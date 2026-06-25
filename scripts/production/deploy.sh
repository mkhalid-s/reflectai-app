#!/bin/bash

# ReflectAI Production Deployment Script
# This script handles the deployment of ReflectAI to production environments

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
ENVIRONMENT=${1:-production}
REGION=${AWS_REGION:-us-west-2}
CLUSTER_NAME="reflectai-cluster"
NAMESPACE="reflectai"
APP_VERSION="v2.0.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check for required tools
    command -v docker >/dev/null 2>&1 || log_error "Docker is required but not installed."
    command -v kubectl >/dev/null 2>&1 || log_error "kubectl is required but not installed."
    command -v helm >/dev/null 2>&1 || log_error "Helm is required but not installed."
    
    # Check for AWS CLI if deploying to AWS
    if [[ "$ENVIRONMENT" == "production" ]] || [[ "$ENVIRONMENT" == "staging" ]]; then
        command -v aws >/dev/null 2>&1 || log_error "AWS CLI is required but not installed."
        
        # Check AWS credentials
        aws sts get-caller-identity >/dev/null 2>&1 || log_error "AWS credentials not configured."
    fi
    
    log_info "Prerequisites check passed."
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    
    docker build \
        -t reflectai/app:${APP_VERSION} \
        -t reflectai/app:latest \
        --build-arg BUILD_ENV=${ENVIRONMENT} \
        --platform linux/amd64 \
        .
    
    log_info "Docker image built successfully."
}

# Push image to registry
push_image() {
    log_info "Pushing image to registry..."
    
    if [[ "$ENVIRONMENT" == "production" ]] || [[ "$ENVIRONMENT" == "staging" ]]; then
        # AWS ECR
        ECR_REGISTRY="$(aws sts get-caller-identity --query Account --output text).dkr.ecr.${REGION}.amazonaws.com"
        
        # Login to ECR
        aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
        
        # Tag and push
        docker tag reflectai/app:${APP_VERSION} ${ECR_REGISTRY}/reflectai:${APP_VERSION}
        docker tag reflectai/app:latest ${ECR_REGISTRY}/reflectai:latest
        
        docker push ${ECR_REGISTRY}/reflectai:${APP_VERSION}
        docker push ${ECR_REGISTRY}/reflectai:latest
    else
        # Local registry or Docker Hub
        docker push reflectai/app:${APP_VERSION}
        docker push reflectai/app:latest
    fi
    
    log_info "Image pushed to registry."
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    kubectl run migrations \
        --image=reflectai/app:${APP_VERSION} \
        --namespace=${NAMESPACE} \
        --rm \
        --attach \
        --restart=Never \
        -- python manage.py migrate
    
    log_info "Migrations completed."
}

# Deploy to Kubernetes
deploy_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply configurations
    kubectl apply -f k8s/configmap.yaml -n ${NAMESPACE}
    kubectl apply -f k8s/secrets.yaml -n ${NAMESPACE}
    kubectl apply -f k8s/deployment.yaml -n ${NAMESPACE}
    kubectl apply -f k8s/service.yaml -n ${NAMESPACE}
    kubectl apply -f k8s/ingress.yaml -n ${NAMESPACE}
    
    # Wait for deployment to be ready
    kubectl rollout status deployment/reflectai-app -n ${NAMESPACE} --timeout=5m
    
    log_info "Kubernetes deployment completed."
}

# Deploy with Helm
deploy_helm() {
    log_info "Deploying with Helm..."
    
    helm upgrade --install reflectai ./helm/reflectai \
        --namespace ${NAMESPACE} \
        --create-namespace \
        --set image.tag=${APP_VERSION} \
        --set environment=${ENVIRONMENT} \
        --values helm/reflectai/values.${ENVIRONMENT}.yaml \
        --wait
    
    log_info "Helm deployment completed."
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    # Get service endpoint
    if [[ "$ENVIRONMENT" == "production" ]]; then
        ENDPOINT="https://api.reflectai.com/health/ready"
    elif [[ "$ENVIRONMENT" == "staging" ]]; then
        ENDPOINT="https://staging.reflectai.com/health/ready"
    else
        # Get service IP for local deployment
        SERVICE_IP=$(kubectl get svc reflectai-service -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
        ENDPOINT="http://${SERVICE_IP}/health/ready"
    fi
    
    # Wait for service to be healthy
    MAX_RETRIES=30
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -f -s "${ENDPOINT}" > /dev/null; then
            log_info "Health check passed."
            return 0
        fi
        
        RETRY_COUNT=$((RETRY_COUNT + 1))
        log_warn "Health check failed. Retry ${RETRY_COUNT}/${MAX_RETRIES}..."
        sleep 10
    done
    
    log_error "Health check failed after ${MAX_RETRIES} retries."
}

# Rollback deployment
rollback() {
    log_warn "Rolling back deployment..."
    
    if command -v helm >/dev/null 2>&1; then
        helm rollback reflectai -n ${NAMESPACE}
    else
        kubectl rollout undo deployment/reflectai-app -n ${NAMESPACE}
    fi
    
    log_info "Rollback completed."
}

# Send deployment notification
notify_deployment() {
    local STATUS=$1
    local MESSAGE=$2
    
    # Send Slack notification if webhook is configured
    if [ ! -z "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"Deployment ${STATUS}: ${MESSAGE}\"}" \
            ${SLACK_WEBHOOK_URL}
    fi
    
    # Log to CloudWatch if in AWS
    if [[ "$ENVIRONMENT" == "production" ]] || [[ "$ENVIRONMENT" == "staging" ]]; then
        aws logs put-log-events \
            --log-group-name "/aws/reflectai/deployments" \
            --log-stream-name "${ENVIRONMENT}" \
            --log-events "timestamp=$(date +%s000),message=Deployment ${STATUS}: ${MESSAGE}"
    fi
}

# Main deployment flow
main() {
    log_info "Starting deployment for environment: ${ENVIRONMENT}"
    log_info "Application version: ${APP_VERSION}"
    
    # Pre-deployment checks
    check_prerequisites
    
    # Build and push image
    build_image
    push_image
    
    # Deploy
    if [ -d "helm/reflectai" ]; then
        deploy_helm
    else
        deploy_kubernetes
    fi
    
    # Run migrations
    run_migrations
    
    # Verify deployment
    if health_check; then
        log_info "Deployment successful!"
        notify_deployment "SUCCESS" "Version ${APP_VERSION} deployed to ${ENVIRONMENT}"
    else
        log_error "Deployment failed. Initiating rollback..."
        rollback
        notify_deployment "FAILED" "Version ${APP_VERSION} deployment failed. Rolled back."
        exit 1
    fi
    
    log_info "Deployment completed successfully!"
}

# Handle script interruption
trap 'log_error "Deployment interrupted"' INT TERM

# Run main function
main