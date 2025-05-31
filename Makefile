.PHONY: help build deploy start stop restart logs clean test lint format check-env

# Default target
help:
	@echo "Orbia Backend - Available commands:"
	@echo ""
	@echo "  🚀 Deployment:"
	@echo "    deploy      - Full deployment (build + start)"
	@echo "    build       - Build Docker image"
	@echo "    start       - Start services"
	@echo "    stop        - Stop services"
	@echo "    restart     - Restart services"
	@echo ""
	@echo "  📊 Monitoring:"
	@echo "    logs        - View logs"
	@echo "    status      - Check service status"
	@echo "    health      - Check application health"
	@echo ""
	@echo "  🔧 Development:"
	@echo "    test        - Run tests"
	@echo "    lint        - Run linting"
	@echo "    format      - Format code"
	@echo "    check-env   - Validate environment variables"
	@echo ""
	@echo "  🧹 Maintenance:"
	@echo "    clean       - Clean up Docker resources"
	@echo "    backup      - Backup data"

# Deployment commands
deploy: check-env build start
	@echo "✅ Deployment complete!"
	@echo "🔗 Application: http://localhost:8000"
	@echo "🔗 Health: http://localhost:8000/_Health"

build:
	@echo "🔨 Building Docker image..."
	docker build -t orbia:latest .

start:
	@echo "🚀 Starting services..."
	docker-compose up -d

stop:
	@echo "🛑 Stopping services..."
	docker-compose down

restart: stop start

# Monitoring commands
logs:
	docker-compose logs -f

status:
	docker-compose ps

health:
	@echo "🔍 Checking application health..."
	@curl -s http://localhost:8000/_Health | jq . || echo "❌ Health check failed"

# Development commands
test:
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v

lint:
	@echo "🔍 Running linter..."
	ruff check .

format:
	@echo "🎨 Formatting code..."
	ruff format .

check-env:
	@echo "🔧 Checking environment variables..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found! Copy from example.env"; \
		exit 1; \
	fi
	@if grep -q "your_" .env || grep -q "CHANGE_THIS" .env; then \
		echo "⚠️  Found placeholder values in .env file"; \
		echo "Please update these before deploying:"; \
		grep -E "(your_|CHANGE_THIS)" .env || true; \
		exit 1; \
	fi
	@echo "✅ Environment variables look good"

# Maintenance commands
clean:
	@echo "🧹 Cleaning up Docker resources..."
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

backup:
	@echo "💾 Creating backup..."
	@mkdir -p backups
	@docker-compose exec -T redis redis-cli BGSAVE
	@tar -czf backups/logs-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz logs/
	@echo "✅ Backup created in backups/ directory"

# Development setup
setup-dev:
	@echo "🔧 Setting up development environment..."
	@if [ ! -f .env ]; then cp example.env .env; fi
	@echo "📝 Please edit .env with your actual values"
	@echo "🐍 Install dependencies with: poetry install"

# Production deployment
deploy-prod: check-env
	@echo "🌐 Deploying to production..."
	@if [ "$(NODE_ENV)" != "production" ]; then \
		echo "❌ NODE_ENV must be set to 'production'"; \
		exit 1; \
	fi
	@$(MAKE) build
	@$(MAKE) start
	@echo "✅ Production deployment complete!" 