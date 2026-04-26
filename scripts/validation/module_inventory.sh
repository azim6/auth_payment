#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "# Module Inventory"
echo
echo "Generated from repository structure."
echo
echo "| Module | Has models | Has serializers | Has views | Has urls | Has migration | Test files |"
echo "|---|---:|---:|---:|---:|---:|---:|"

for app in accounts billing security_ops compliance ops developer_platform notifications observability data_governance fraud_abuse admin_console customer_portal identity_hardening enterprise_sso scim_provisioning oidc_provider sdk_registry usage_billing tax_pricing; do
  models=$(test -s "$app/models.py" && echo yes || echo no)
  serializers=$(test -s "$app/serializers.py" && echo yes || echo no)
  views=$(test -s "$app/views.py" && echo yes || echo no)
  urls=$(test -s "$app/urls.py" && echo yes || echo no)
  migration=$(test -f "$app/migrations/0001_initial.py" && echo yes || echo no)
  tests=0
  if [ -d "$app/tests" ]; then
    tests=$(ls "$app/tests"/*.py 2>/dev/null | wc -l | tr -d ' ')
  elif [ -f "$app/tests.py" ]; then
    tests=1
  fi
  echo "| $app | $models | $serializers | $views | $urls | $migration | $tests |"
done
