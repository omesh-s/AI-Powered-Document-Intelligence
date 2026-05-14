.PHONY: dev api web test lint format migrate docker-up docker-down smoke demo-setup build-web verify

dev:
	@echo "Run API and Web in separate terminals: make api && make web"

api:
	cd apps/api && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web:
	cd apps/web && npm run dev

test:
	cd apps/api && python -m pytest -q
	cd apps/web && npm run test --if-present

lint:
	cd apps/api && python -m ruff check . && python -m ruff format --check .
	cd apps/web && npm run lint --if-present

format:
	cd apps/api && python -m ruff format .
	cd apps/web && npm run format --if-present

migrate:
	cd apps/api && python -m alembic upgrade head

docker-up:
	docker compose up -d

docker-down:
	docker compose down

demo-setup:
	python scripts/demo_setup.py

smoke:
	cd apps/api && python scripts/smoke_test.py

build-web:
	cd apps/web && npm run build

verify: test lint build-web
