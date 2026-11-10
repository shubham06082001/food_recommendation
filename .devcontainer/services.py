"""Host-side database bootstrap; never removes containers, volumes, or collections."""

import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
from urllib.parse import quote_plus, urlsplit, urlunsplit
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
SERVICES = (
    ("mongodb", 20000, 27017, "mongo:7", "/data/db"),
    ("qdrant", 6333, 6333, "qdrant/qdrant:v1.18.2", "/qdrant/storage"),
)


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()


def listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            return True
    except OSError:
        return False


def uses_port(container, port):
    bindings = container["HostConfig"].get("PortBindings") or {}
    return any(binding.get("HostPort") == str(port)
               for values in bindings.values() for binding in (values or []))


def ensure_service(service, port, internal_port, image, storage, check_only=False):
    if listening(port):
        print(f"Reusing {service} on port {port}.")
        return
    if check_only:
        raise RuntimeError(f"{service} is unavailable on port {port}.")
    container_ids = docker("ps", "-aq").split()
    containers = json.loads(docker("inspect", *container_ids)) if container_ids else []
    for container in containers:
        if uses_port(container, port):
            print(f"Starting existing container {container['Name']}.")
            docker("start", container["Id"])
            break
    else:
        name = f"ecos-{service}"
        if any(container["Name"] == f"/{name}" for container in containers):
            raise RuntimeError(f"Container {name} exists with different ports; inspect it manually.")
        print(f"Creating persistent {service} on port {port}.")
        docker("run", "-d", "--name", name, "--restart", "unless-stopped",
               "-p", f"{port}:{internal_port}", "-v", f"{name}-data:{storage}", image)
    for remaining in reversed(range(90)):
        if listening(port):
            return
        if remaining == 0:
            raise RuntimeError(f"{service} did not open port {port} within 90 seconds.")
        time.sleep(1)


def env_values():
    values = {}
    if (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text().splitlines():
            key, separator, value = line.partition("=")
            if separator and not key.lstrip().startswith("#"):
                values[key.strip()] = value.strip().strip("'\"")
    return {**values, **os.environ}


def configure_env():
    path = ROOT / ".env"
    text = path.read_text() if path.exists() else (ROOT / "env.template").read_text()
    values = env_values()
    mongo = urlsplit(values.get("ECOS_MONGODB_URI") or "mongodb://localhost:20000")
    authentication = mongo.netloc.rpartition("@")[0] if "@" in mongo.netloc else ""
    if not authentication and values.get("DB_USERNAME") and values.get("DB_PASSWORD"):
        authentication = f"{quote_plus(values['DB_USERNAME'])}:{quote_plus(values['DB_PASSWORD'])}"
    host = f"{authentication}@host.docker.internal:20000" if authentication else "host.docker.internal:20000"
    updates = {"ECOS_MONGODB_URI": urlunsplit(("mongodb", host, mongo.path, mongo.query, "")),
               "QDRANT_VECTOR_DB_URL": "http://host.docker.internal:6333"}
    if not values.get("ECOS_MANAGER_PASSWORD") or values["ECOS_MANAGER_PASSWORD"].startswith("CHANGE_ME"):
        updates["ECOS_MANAGER_PASSWORD"] = secrets.token_urlsafe(24)
    lines = text.splitlines()
    for key, value in updates.items():
        matches = [index for index, line in enumerate(lines) if line.partition("=")[0].strip() == key]
        if matches:
            for index in matches:
                lines[index] = f"{key}={value}"
        else:
            lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n")
    path.chmod(0o600)
    print("Configured .env database URLs; manager password is in .env (not logged).")


def export_host_ca():
    path = ROOT / ".devcontainer" / "host-ca.pem"
    if sys.platform == "darwin":
        bundle = subprocess.check_output(
            ["security", "find-certificate", "-a", "-p", "/Library/Keychains/System.keychain"], text=True)
        certificates = []
        for part in bundle.split("-----END CERTIFICATE-----"):
            if "-----BEGIN CERTIFICATE-----" not in part:
                continue
            certificate = part.strip() + "\n-----END CERTIFICATE-----\n"
            constraints = subprocess.check_output(
                ["openssl", "x509", "-noout", "-ext", "basicConstraints"], input=certificate, text=True)
            if "CA:TRUE" in constraints:
                certificates.append(certificate)
        path.write_text("".join(certificates))
    else:
        source = ssl.get_default_verify_paths().cafile
        path.write_text(Path(source).read_text() if source else "")
    print("Exported public host CA certificates for verified dependency downloads.")


def qdrant_request(path, data=None, headers=None):
    key = env_values().get("QDRANT_API_KEY", "")
    request_headers = {**({"api-key": key} if key else {}), **(headers or {})}
    request = urllib.request.Request(f"http://127.0.0.1:6333{path}", data=data, headers=request_headers)
    with OPENER.open(request, timeout=600) as response:
        result = json.load(response)
    if result.get("status") != "ok":
        raise RuntimeError(f"Qdrant request failed: {result.get('status')}")
    return result["result"]


def collection_names(check_only):
    for attempt in range(90):
        try:
            return {item["name"] for item in qdrant_request("/collections")["collections"]}
        except urllib.error.HTTPError:
            raise
        except OSError:
            if check_only or attempt == 89:
                raise
            time.sleep(1)


def upload_snapshot(collection):
    snapshots = sorted((ROOT / "qdrant-snapshot").glob(f"{collection}-*.snapshot"))
    if not snapshots:
        raise RuntimeError(f"No snapshot supplied for {collection} in qdrant-snapshot/.")
    snapshot = snapshots[-1]
    boundary = secrets.token_hex(16)
    prefix = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"snapshot\"; "
              f"filename=\"{snapshot.name}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode()
    suffix = f"\r\n--{boundary}--\r\n".encode()

    def chunks():
        yield prefix
        with snapshot.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                yield chunk
        yield suffix

    print(f"Restoring {collection} from {snapshot.name}...")
    qdrant_request(f"/collections/{collection}/snapshots/upload?wait=true&priority=snapshot",
                   chunks(), {"Content-Type": f"multipart/form-data; boundary={boundary}",
                              "Content-Length": str(len(prefix) + snapshot.stat().st_size + len(suffix))})


def restore_snapshots(check_only=False):
    collections = collection_names(check_only)
    for collection in ("food_nutrients", "ecos_ingredients"):
        if collection not in collections:
            if check_only:
                raise RuntimeError(f"Missing Qdrant collection: {collection}")
            upload_snapshot(collection)
        details = qdrant_request(f"/collections/{collection}")
        if details["status"] != "green" or not details["points_count"]:
            raise RuntimeError(f"Collection {collection} is not ready or is empty.")
        print(f"{collection}: {details['points_count']} points, healthy (existing data preserved).")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only check; no starts, imports, or .env changes")
    args = parser.parse_args()
    for service in SERVICES:
        ensure_service(*service, check_only=args.check)
    restore_snapshots(check_only=args.check)
    if not args.check:
        configure_env()
        export_host_ca()


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Database bootstrap failed: {error}") from error