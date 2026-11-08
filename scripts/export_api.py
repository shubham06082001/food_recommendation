"""Refresh/validate root api.json against FastAPI without lifespan or services.

Run: .venv/bin/python scripts/export_api.py [--refresh]
Requires the application's dependencies and jsonschema (already used by the dev environment).
Only --refresh writes api.json; no runtime files, models or databases are changed.
"""

import argparse
import ast
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def reject_network(*_args, **_kwargs):
    raise RuntimeError("Network disabled during offline API documentation validation")


def pointer(document, ref):
    assert ref.startswith("#/"), ref
    value = document
    for part in ref[2:].split("/"):
        value = value[part.replace("~1", "/").replace("~0", "~")]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Refresh only the declared OpenAPI and source pointers")
    args = parser.parse_args()
    # Import reads configuration, but never invoke lifespan, dependencies or endpoint functions.
    # Block DNS and socket connections even if a future import introduces network side effects.
    with patch.object(socket.socket, "connect", reject_network), \
            patch.object(socket.socket, "connect_ex", reject_network), \
            patch.object(socket, "create_connection", reject_network), \
            patch.object(socket, "getaddrinfo", reject_network):
        from backend.app.main import app
        contract = app.openapi()
        infrastructure = {
            (method, route.path)
            for route in app.routes
            if hasattr(route, "path") and getattr(route, "include_in_schema", True) is False
            for method in route.methods
        }

    path = ROOT / "api.json"
    document = json.loads(path.read_text())
    operations = [operation for module in document["modules"] for operation in module["operations"]]
    expected = {(method.upper(), route) for route, item in contract["paths"].items()
                for method in item if method in METHODS}
    assert document["scope"]["application_operations"] == len(expected)
    assert document["scope"]["infrastructure_method_path_pairs"] == len(infrastructure)
    assert document["scope"]["total_http_operations"] == len(expected | infrastructure)
    documented = [(operation["method"], operation["path"]) for operation in operations]
    assert len(set(documented)) == len(documented), "Duplicate operation documentation"
    assert set(documented) == expected | infrastructure, (
        f"Coverage mismatch; missing={sorted((expected | infrastructure) - set(documented))}; "
        f"extra={sorted(set(documented) - (expected | infrastructure))}"
    )
    for module in document["modules"]:
        for reference in module.get("operation_references", []):
            assert (reference["method"], reference["path"]) in expected, "Unknown module operation reference"

    # Static router inventory cross-checks the offline application contract.
    sources = {}
    for source in sorted((ROOT / "backend/app/routers").glob("*.py")):
        tree = ast.parse(source.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
                        and isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == "router"
                        and decorator.func.attr in METHODS):
                    route = ast.literal_eval(decorator.args[0])
                    sources[(decorator.func.attr.upper(), "/api/v1" + route)] = (
                        f"{source.relative_to(ROOT).as_posix()}#L{node.lineno}"
                    )
    assert set(sources) == expected, "Static router inventory differs from OpenAPI"

    if args.refresh:
        document["openapi_contract"] = contract
        main_tree = ast.parse((ROOT / "backend/app/main.py").read_text())
        app_line = next(node.lineno for node in ast.walk(main_tree)
                        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "FastAPI")
        for operation in operations:
            key = operation["method"], operation["path"]
            if key in expected:
                operation["source"] = sources[key]
                escaped = operation["path"].replace("~", "~0").replace("/", "~1")
                operation["openapi_ref"] = f"#/openapi_contract/paths/{escaped}/{operation['method'].lower()}"
            else:
                operation["source"] = f"backend/app/main.py#L{app_line}"
    assert document["openapi_contract"] == contract, "Declared OpenAPI drift: run with --refresh and review"
    for operation in operations:
        key = operation["method"], operation["path"]
        if key in sources:
            assert operation["source"] == sources[key], f"Stale source link: {key}"

    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012

    registry = Registry().with_resource(
        "urn:ecos:openapi", Resource.from_contents(contract, default_specification=DRAFT202012)
    )

    def validate(schema, example):
        # OpenAPI's local refs resolve relative to the embedded contract, not this documentation envelope.
        wrapped = deepcopy(schema)

        def absolutize(value):
            if isinstance(value, dict):
                return {k: ("urn:ecos:openapi" + v if k == "$ref" and v.startswith("#/") else absolutize(v))
                        for k, v in value.items()}
            if isinstance(value, list):
                return [absolutize(v) for v in value]
            return value

        Draft202012Validator(absolutize(wrapped), registry=registry, format_checker=FormatChecker()).validate(example)

    responses_checked = requests_checked = parameters_checked = 0
    for operation in operations:
        key = operation["method"], operation["path"]
        declared = pointer(document, operation["openapi_ref"]) if key in expected else None
        responses = {code: document["error_catalog"][code] for code in operation["shared_errors"]}
        responses.update(operation["responses"])
        successful = {code for code in declared["responses"] if code.startswith("2")} if declared else {"200"}
        assert successful <= set(responses), f"Missing success status: {key}"
        request = operation.get("request_example", {})
        for parameter in declared.get("parameters", []) if declared else []:
            values = request.get(parameter["in"], {})
            if parameter["required"]:
                assert parameter["name"] in values, f"Missing required parameter example: {key} {parameter['name']}"
            if parameter["name"] in values:
                validate(parameter["schema"], values[parameter["name"]])
                parameters_checked += 1
        if declared and "requestBody" in declared:
            media_type, media = next(iter(declared["requestBody"]["content"].items()))
            body = pointer(document, request["body_ref"]) if "body_ref" in request else request["body"]
            validate(media["schema"], body)
            requests_checked += 1
        for code, response in responses.items():
            examples = response.get("examples", [])
            assert examples, f"No response examples: {key} {code}"
            if declared and code in declared["responses"]:
                content = declared["responses"][code].get("content", {})
                schema = content.get("application/json", {}).get("schema")
            elif code.isdigit() and int(code) >= 400:
                schema = document["inferred_error_schema"]
            else:
                schema = None
            for example in examples:
                assert example["provenance"] in {"synthetic", "offline-declaration-not-http-observed"}
                body = pointer(document, example["body_ref"]) if "body_ref" in example else example.get("body")
                if schema:
                    validate(schema, body)
                    responses_checked += 1
        for code in (declared or {}).get("responses", {}):
            if code == "422":
                assert code in responses, f"Missing validation error: {key}"

    if args.refresh:
        path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    print(f"PASS: JSON parsed; {len(expected)} application operations + {len(infrastructure)} infrastructure "
          f"method/path pairs; static AST and fresh offline OpenAPI agree.")
    print(f"PASS: {requests_checked} request bodies, {parameters_checked} parameters and {responses_checked} "
          "response-example checks pass (including reused shared errors); success response contracts are untyped "
          "objects, not field-level guarantees.")
    print("No lifespan, handlers, databases or external services executed. Live smoke suite intentionally not run.")


if __name__ == "__main__":
    main()
