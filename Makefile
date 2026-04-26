.PHONY: up down build migrate shell test superuser collectstatic deploy-check

up:
	docker compose up

build:
	docker compose build

down:
	docker compose down

migrate:
	docker compose exec web python manage.py migrate

shell:
	docker compose exec web python manage.py shell

test:
	docker compose exec web pytest

superuser:
	docker compose exec web python manage.py createsuperuser

collectstatic:
	docker compose exec web python manage.py collectstatic --noinput

deploy-check:
	docker compose exec web python manage.py check --deploy

# v33 completion/stabilization helpers
validate-structure:
	./scripts/validation/validate_structure.sh

module-inventory:
	./scripts/validation/module_inventory.sh

.PHONY: auth-readiness-smoke
auth-readiness-smoke:
	python manage.py test accounts.tests.test_v35_auth_completion --settings=config.settings.test

.PHONY: production-preflight production-bootstrap smoke-http docker-smoke
production-preflight:
	python manage.py ops_production_preflight --json

production-bootstrap:
	./scripts/validation/production_bootstrap.sh

smoke-http:
	./scripts/validation/smoke_http.sh $${BASE_URL:-http://localhost:8000}

docker-smoke:
	docker compose up -d db redis web
	docker compose exec web python manage.py ops_production_preflight

production-verify:
	python manage.py production_verify

v42-verify:
	python manage.py production_verify --persist

admin-contract-smoke:
	python scripts/admin_contract_smoke.py

# v43 business-focused commands
seed-business-products:
	python manage.py seed_business_products

business-core-check:
	python manage.py check
	python manage.py showmigrations accounts billing admin_integration admin_console customer_portal notifications ops production_verification

seed-business:
	python manage.py seed_business_products
