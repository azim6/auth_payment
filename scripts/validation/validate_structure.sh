#!/usr/bin/env bash
set -eu

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

apps="accounts billing security_ops compliance ops developer_platform notifications observability data_governance fraud_abuse admin_console customer_portal identity_hardening enterprise_sso scim_provisioning oidc_provider sdk_registry usage_billing tax_pricing"
missing=0

for app in $apps; do
  for file in __init__.py apps.py models.py urls.py views.py admin.py; do
    if [ ! -f "$app/$file" ]; then
      echo "missing $app/$file"
      missing=1
    fi
  done
  if [ ! -f "$app/migrations/0001_initial.py" ]; then
    echo "missing $app/migrations/0001_initial.py"
    missing=1
  fi
  if [ ! -f "$app/migrations/__init__.py" ]; then
    echo "missing $app/migrations/__init__.py"
    missing=1
  fi
done

for doc in docs/FEATURE_READINESS_MATRIX.md docs/PRODUCTION_MVP_SCOPE.md docs/API_INTEGRATION_MAP.md docs/UPGRADE_POLICY.md; do
  if [ ! -f "$doc" ]; then
    echo "missing $doc"
    missing=1
  fi
done

if [ "$missing" -ne 0 ]; then
  echo "structure validation failed"
  exit 1
fi

echo "structure validation passed"
