#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${ECOS_INSTALL_USE_PROXY:-false}" != "true" ]]; then
	unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy ftp_proxy FTP_PROXY
fi
if [[ -s .devcontainer/host-ca.pem ]]; then
	python - <<'PY'
from pathlib import Path

destination = Path("/usr/local/share/ca-certificates/ecos-host")
destination.mkdir(parents=True, exist_ok=True)
for index, part in enumerate(Path(".devcontainer/host-ca.pem").read_text().split("-----END CERTIFICATE-----")):
	if "-----BEGIN CERTIFICATE-----" in part:
		(destination / f"host-{index}.crt").write_text(part.strip() + "\n-----END CERTIFICATE-----\n")
PY
	update-ca-certificates
fi
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
export PIP_CERT="$SSL_CERT_FILE"
python -m venv /opt/ecos-venv
/opt/ecos-venv/bin/python -m pip install --upgrade pip
/opt/ecos-venv/bin/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
/opt/ecos-venv/bin/python -m pip install -r requirements.txt
/opt/ecos-venv/bin/python - <<'PY'
from sentence_transformers import SentenceTransformer

SentenceTransformer("all-MiniLM-L6-v2", local_files_only=False)
print("Recommendation model cached for offline startup.")
PY
