SHELL=/bin/bash

# dev
deps:
	echo "Installing backend dependencies"
	cd backend && python3 -m venv .venv && source .venv/bin/activate && pip3 install --upgrade -r requirements.txt
	echo "Installing frontend dependencies"
	cd frontend && python3 -m venv .venv && source .venv/bin/activate && pip3 install --upgrade -r requirements.txt

autogen-migration:
	cd backend && source .venv/bin/activate && ENV_FILE=.dev.env alembic revision --autogenerate -m '$(message)'

migrate-dev:
	echo "Migrating to last version"
	cd backend && source .venv/bin/activate && ENV_FILE=.dev.env alembic upgrade head 

downgrade-dev:
	echo "Downgrading to last version"
	cd backend && source .venv/bin/activate && ENV_FILE=.dev.env alembic downgrade -1

build-dev:
	docker compose -f docker-compose.dev.yml build

build-dev-nginx:
	SERVER_IP=$(shell ./nginx_server/get-ip.sh) docker compose -f docker-compose.dev.yml build yt_nginx_dev 

run-dev-db:
	docker compose -f docker-compose.dev.yml up -d yt_mysql_dev
	sleep 10
	$(MAKE) migrate-dev

run-dev-nginx:
	$(MAKE) build-dev-nginx
	docker compose -f docker-compose.dev.yml up yt_nginx_dev 

run-dev-backend:
	cd backend && source .venv/bin/activate && ENV_FILE=.dev.env uvicorn backend.server:app --host 0.0.0.0 --port 11014 --reload

run-dev-frontend:
	cd frontend && source .venv/bin/activate && ENV_FILE=.dev.env uvicorn frontend.main:app --host 0.0.0.0 --port 11013 --reload

run-migrate-backend:
	cd backend && source .venv/bin/activate && ENV_FILE=.migrate.env uvicorn backend.server:app --host 0.0.0.0 --port 11014 --reload

run-migrate-frontend:
	cd frontend && source .venv/bin/activate && ENV_FILE=.migrate.env uvicorn frontend.main:app --host 0.0.0.0 --port 11013 --reload

stop-dev:
	docker compose -f docker-compose.dev.yml down 

create-data:
	mkdir -p data/mysql
	mkdir -p data/data/videos
	mkdir -p data/data/thumbnails
	cp subscription_manager data/data/subscription_manager

remove-data:
	rm -rf data

format: 
	echo "Formatting Backend"
	cd backend && source .venv/bin/activate && black . && isort . && djlint . --reformat --format-css --format-js --profile=jinja
	echo "Formatting Frontend"
	cd frontend && source .venv/bin/activate && black . && isort . && djlint . --reformat --format-css --format-js --profile=jinja

check-formatting:
	echo "Checking Backend"
	cd backend && source .venv/bin/activate && black . --check && isort . --check-only && djlint . --check --format-css --format-js --profile=jinja
	echo "Checking Frontend"
	cd frontend && source .venv/bin/activate && black . --check && isort . --check-only && djlint . --check --format-css --format-js --profile=jinja

lint:
	echo "Linting Backend"
	cd backend && source .venv/bin/activate && flake8 . --exclude=.venv --ignore=E501 --per-file-ignores="__init__.py:F401"
	echo "Linting Frontend"
	cd frontend && source .venv/bin/activate && flake8 . --exclude=.venv --ignore=E501 --per-file-ignores="__init__.py:F401"

shell:
	cd backend && source .venv/bin/activate && ENV_FILE=.dev.env python3

first:
	yt-dlp --format mp4 https://youtu.be/dQw4w9WgXcQ
	mv *.mp4 frontend/static/dQw4w9WgXcQ.mp4

# prod
build-prod:
	docker compose -f docker-compose.prod.yml build yt_frontend yt_backend
	$(MAKE) build-prod-nginx

build-prod-nginx:
	SERVER_IP=yt_frontend docker compose -f docker-compose.prod.yml build yt_nginx 

run-prod-nginx:
	docker compose -f docker-compose.prod.yml up -d yt_nginx

run-prod:
	docker compose -f docker-compose.prod.yml up -d yt_backend yt_frontend yt_nginx

migrate-prod:
	echo "Migrating to last version"
	cd backend && source .venv/bin/activate && ENV_FILE=.migrate.env alembic upgrade head 

run-prod-db:
	docker compose -f docker-compose.prod.yml up -d yt_mysql
	sleep 10
	$(MAKE) migrate-prod

stop-prod:
	docker compose -f docker-compose.prod.yml down

shell-prod:
	cd backend && source .venv/bin/activate && ENV_FILE=.migrate.env python3

deploy:
	$(MAKE) stop-prod
	$(MAKE) run-prod-db
	$(MAKE) build-prod
	$(MAKE) run-prod

# prod_less
build-prod-less:
	docker compose -f docker-compose.prod_less.yml build yt_frontend_less_good yt_backend_less_good
	$(MAKE) build-prod-nginx-less

build-prod-nginx-less:
	SERVER_IP=yt_frontend_less_good docker compose -f docker-compose.prod_less.yml build yt_nginx_less_good

run-prod-nginx-less:
	docker compose -f docker-compose.prod_less.yml up -d yt_nginx_less_good

run-prod-less:
	docker compose -f docker-compose.prod_less.yml up -d yt_backend_less_good yt_frontend_less_good yt_nginx_less_good

migrate-prod-less:
	echo "Migrating to last version"
	cd backend && source .venv/bin/activate && ENV_FILE=.migrate.env alembic upgrade head 

run-prod-db-less:
	docker compose -f docker-compose.prod_less.yml up -d yt_mysql_less_good
	sleep 10
	$(MAKE) migrate-prod-less

stop-prod-less:
	docker compose -f docker-compose.prod_less.yml down

shell-prod-less:
	cd backend && source .venv/bin/activate && ENV_FILE=.migrate.env python3

deploy-less:
	$(MAKE) stop-prod-less
	$(MAKE) run-prod-db-less
	$(MAKE) build-prod-less
	$(MAKE) run-prod-less

# prod_vpn
build-prod-vpn:
	docker compose -f docker-compose.prod_vpn.yml build yt_frontend yt_backend
	$(MAKE) build-prod-nginx-vpn

build-prod-nginx-vpn:
	SERVER_IP=yt_frontend_vpn_good docker compose -f docker-compose.prod_vpn.yml build yt_nginx

run-prod-nginx-vpn:
	docker compose -f docker-compose.prod_vpn.yml up -d yt_nginx

run-prod-vpn:
	docker compose -f docker-compose.prod_vpn.yml up -d yt_backend yt_frontend yt_nginx

migrate-prod-vpn:
	echo "Migrating to last version"
	cd backend && source .venv/bin/activate && ENV_FILE=.migrate.env alembic upgrade head 

run-prod-db-vpn:
	docker compose -f docker-compose.prod_vpn.yml up -d yt_mysql
	sleep 10
	$(MAKE) migrate-prod-vpn

stop-prod-vpn:
	docker compose -f docker-compose.prod_vpn.yml down

shell-prod-vpn:
	cd backend && source .venv/bin/activate && ENV_FILE=.migrate.env python3

rebuild-frontend:
	docker compose -f docker-compose.prod_vpn.yml down yt_frontend
	docker compose -f docker-compose.prod_vpn.yml build yt_frontend
	docker compose -f docker-compose.prod_vpn.yml up -d yt_frontend

deploy-vpn:
	$(MAKE) stop-prod-vpn
	$(MAKE) run-prod-db-vpn
	$(MAKE) build-prod-vpn
	$(MAKE) run-prod-vpn