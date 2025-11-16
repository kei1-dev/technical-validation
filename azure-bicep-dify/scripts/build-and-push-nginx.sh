#!/bin/bash

# ==============================================================================
# Build and Push Custom nginx Docker Image to ACR
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo "Build and Push Custom nginx Image"
echo "============================================================"
echo ""

# Parse arguments
RESOURCE_GROUP=""
ACR_NAME=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --resource-group)
      RESOURCE_GROUP="$2"
      shift 2
      ;;
    --acr-name)
      ACR_NAME="$2"
      shift 2
      ;;
    *)
      echo -e "${RED}[ERROR]${NC} Unknown argument: $1"
      exit 1
      ;;
  esac
done

# Validate arguments
if [ -z "$RESOURCE_GROUP" ]; then
  echo -e "${RED}[ERROR]${NC} Resource group is required (--resource-group)"
  exit 1
fi

# Get ACR name if not provided
if [ -z "$ACR_NAME" ]; then
  echo -e "${BLUE}[INFO]${NC} Getting ACR name from deployment outputs..."
  ACR_NAME=$(az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name main \
    --query 'properties.outputs.acrName.value' \
    -o tsv 2>/dev/null)

  if [ -z "$ACR_NAME" ]; then
    echo -e "${RED}[ERROR]${NC} Failed to get ACR name from deployment"
    exit 1
  fi
  echo -e "${GREEN}[✓]${NC} ACR name: $ACR_NAME"
fi

# Get ACR login server
echo -e "${BLUE}[INFO]${NC} Getting ACR login server..."
ACR_LOGIN_SERVER=$(az acr show \
  --name "$ACR_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query 'loginServer' \
  -o tsv)

if [ -z "$ACR_LOGIN_SERVER" ]; then
  echo -e "${RED}[ERROR]${NC} Failed to get ACR login server"
  exit 1
fi
echo -e "${GREEN}[✓]${NC} ACR login server: $ACR_LOGIN_SERVER"

# Login to ACR
echo ""
echo -e "${BLUE}[INFO]${NC} Logging in to ACR..."
az acr login --name "$ACR_NAME"

# Build Docker image
echo ""
echo "============================================================"
echo "Building Docker Image"
echo "============================================================"
echo -e "${BLUE}[INFO]${NC} Building nginx image..."
echo -e "${BLUE}[INFO]${NC} Context: $PROJECT_ROOT/docker/nginx"
echo -e "${BLUE}[INFO]${NC} Image tag: ${ACR_LOGIN_SERVER}/dify-nginx:latest"

docker build \
  -t "${ACR_LOGIN_SERVER}/dify-nginx:latest" \
  -f "$PROJECT_ROOT/docker/nginx/Dockerfile" \
  "$PROJECT_ROOT/docker/nginx"

if [ $? -eq 0 ]; then
  echo -e "${GREEN}[✓]${NC} Docker image built successfully"
else
  echo -e "${RED}[ERROR]${NC} Failed to build Docker image"
  exit 1
fi

# Push Docker image
echo ""
echo "============================================================"
echo "Pushing Docker Image to ACR"
echo "============================================================"
echo -e "${BLUE}[INFO]${NC} Pushing image to ACR..."

docker push "${ACR_LOGIN_SERVER}/dify-nginx:latest"

if [ $? -eq 0 ]; then
  echo -e "${GREEN}[✓]${NC} Docker image pushed successfully"
else
  echo -e "${RED}[ERROR]${NC} Failed to push Docker image"
  exit 1
fi

# Summary
echo ""
echo "============================================================"
echo "Summary"
echo "============================================================"
echo -e "${GREEN}[✓]${NC} Image: ${ACR_LOGIN_SERVER}/dify-nginx:latest"
echo -e "${GREEN}[✓]${NC} Successfully built and pushed to ACR"
echo ""
echo "Next steps:"
echo "1. Update bicep/parameters/dev.bicepparam:"
echo "   param nginxImage = '${ACR_LOGIN_SERVER}/dify-nginx:latest'"
echo "2. Re-deploy infrastructure"
echo ""
