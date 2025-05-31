#!/bin/bash

# =============================================================================
# Orbia Backend Deployment Script
# =============================================================================

set -e  # Exit on any error

echo "🚀 Starting Orbia Backend Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    print_status "Creating .env from example.env..."
    cp example.env .env
    print_warning "Please update .env with your actual values before proceeding!"
    exit 1
fi

# Check if required environment variables are set
print_status "Checking required environment variables..."

required_vars=("OPENAI_API_KEY" "JWT_SECRET_KEY")
missing_vars=()

for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env || grep -q "^${var}=your_" .env || grep -q "^${var}=CHANGE_THIS" .env; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_error "Missing or placeholder values for required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    print_warning "Please update these values in your .env file before deploying!"
    exit 1
fi

# Create logs directory with proper permissions
print_status "Setting up logs directory..."
mkdir -p logs
chmod 755 logs

# Build Docker image
print_status "Building Docker image..."
docker build -t orbia:latest .

# Stop existing containers
print_status "Stopping existing containers..."
docker-compose down || true

# Start services
print_status "Starting services..."
docker-compose up -d

# Wait for services to be healthy
print_status "Waiting for services to be healthy..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    print_status "✅ Deployment successful!"
    print_status "Services are running:"
    docker-compose ps
    
    print_status "🔗 Application URLs:"
    echo "  - API: http://localhost:8000"
    echo "  - Health Check: http://localhost:8000/_Health"
    echo "  - Metrics: http://localhost:8000/metrics"
    
    print_status "📋 Useful commands:"
    echo "  - View logs: docker-compose logs -f"
    echo "  - Stop services: docker-compose down"
    echo "  - Restart: docker-compose restart"
    
else
    print_error "❌ Deployment failed!"
    print_status "Checking logs..."
    docker-compose logs
    exit 1
fi 