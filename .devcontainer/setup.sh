#!/bin/bash
set -e
# Host proxy may be unreachable and the corporate network re-signs TLS certs, so bypass both for package installs.
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ftp_proxy FTP_PROXY
export PIP_TRUSTED_HOST="pypi.org files.pythonhosted.org"
pip install --user --no-cache-dir uv
export UV_NATIVE_TLS=1 UV_INSECURE_HOST="pypi.org files.pythonhosted.org download.pytorch.org"
~/.local/bin/uv sync --frozen
