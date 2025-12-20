#!/bin/bash

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="449272628852"
ECR_REPO_NAME="sol-analyst-backend"
# LAMBDA_FUNCTION_NAME="sol-analyst-api"

# Exit on any error
set -e

echo "🔨 Building Docker image..."
docker build --platform linux/arm64 --provenance=false -t ${ECR_REPO_NAME}:latest .

echo "📦 Creating ECR repository (if doesn't exist)..."
aws ecr create-repository --repository-name ${ECR_REPO_NAME} --region ${AWS_REGION} 2>/dev/null || true

echo "🔐 Logging into ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

echo "🏷️  Tagging image..."
docker tag ${ECR_REPO_NAME}:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:latest

echo "⬆️  Pushing to ECR..."
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:latest

echo "✅ Image pushed successfully!"
echo ""
echo "📦 Image URI: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:latest"
echo ""
