COMPOSE = docker compose --env-file .env -f compose.yaml

.PHONY: build build-frontend pull up down restart ps logs logs-frontend config

# Build all custom service images
build:
	$(COMPOSE) build

# Rebuild only the frontend image
build-frontend:
	$(COMPOSE) build --no-cache frontend

# Download service images
pull:
	$(COMPOSE) pull

# Start all services
up:
	$(COMPOSE) up -d --build

# Rebuild frontend and restart its container
rebuild-frontend:
	$(COMPOSE) up -d --build --no-deps frontend

# Stop and remove containers and networks
down:
	$(COMPOSE) down

# Restart services
restart:
	$(COMPOSE) restart

# Show service status
ps:
	$(COMPOSE) ps

# Follow logs from all services
logs:
	$(COMPOSE) logs -f

# Follow frontend logs
logs-frontend:
	$(COMPOSE) logs -f frontend

# Validate Compose configuration
config:
	$(COMPOSE) config
