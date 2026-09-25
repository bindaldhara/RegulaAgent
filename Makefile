.PHONY: start up down rebuild test install migrate

install:
	pip install -r backend/requirements.txt
	pip install pytest httpx

# Start full stack (Postgres + API + frontend). Run from repo root.
start: up

up:
	docker compose up --build

# Use if frontend shows "Failed to resolve import motion/react" (stale node_modules volume).
fix-ui:
	docker compose stop frontend
	docker volume rm -f regulaagent_frontend_node_modules 2>/dev/null || true
	docker compose up -d --build frontend

rebuild:
	docker compose down
	docker compose build --no-cache frontend
	docker compose up --build

down:
	docker compose down

migrate:
	cd backend && python -c "from db.connection import init_db; init_db()"

test:
	pytest -q
