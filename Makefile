.PHONY: up down build logs ps migrate seed shell-backend shell-db dev-backend dev-frontend

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

ps:
	docker compose ps

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python /app/scripts/seed_demo.py

shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec postgres psql -U exalink -d exalink_campo

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

setup: build up
	@echo "Esperando servicios..."
	@sleep 5
	$(MAKE) migrate
	$(MAKE) seed
	@echo "✅  Exalink Campo listo en http://localhost:3000"
	@echo "    API Docs: http://localhost:8000/docs"
	@echo "    Admin: admin@exalink.com / exalink2024"

reset-db:
	docker compose exec backend alembic downgrade base
	$(MAKE) migrate
	$(MAKE) seed
