
COMPOSE = docker compose --env-file .env -f compose.yaml

.PHONY: build pull up down restart ps logs config

# Build custom service images
build:
	$(COMPOSE) build --pull

# Download service images
pull:
	$(COMPOSE) pull

# Start all services
up:
	$(COMPOSE) up -d --build

# Stop and remove containers and networks
down:
	$(COMPOSE) down

# Restart services
restart:
	$(COMPOSE) restart

# Show service status
ps:
	$(COMPOSE) ps

# Follow service logs
logs:
	$(COMPOSE) logs -f

# Validate Compose configuration
config:
	$(COMPOSE) config
