#!/usr/bin/env bash
set -euo pipefail

RAW_URL="https://raw.githubusercontent.com/SAP-samples/sap-genai-hub-with-sap-hana-cloud-vector-engine/main/bin/cf_create_bas_sso.py"
SERVICE="default_aicore"
SERVICE_KEY="${1:?Usage: $0 <SERVICE_KEY>}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

curl -fsSL "$RAW_URL" -o "$tmpdir/cf_create_bas_sso.py"
python3 "$tmpdir/cf_create_bas_sso.py" --service "$SERVICE" --service_key "$SERVICE_KEY"
