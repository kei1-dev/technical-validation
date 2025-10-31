#!/bin/bash

# ============================================================================
# Dify on Azure - Deployment Script
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Functions
# ============================================================================

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo "============================================================"
    echo "$1"
    echo "============================================================"
    echo ""
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy Dify on Azure infrastructure using Bicep

OPTIONS:
    -e, --environment ENV       Environment to deploy (dev/prod) [required]
    -g, --resource-group RG     Resource group name [required]
    -l, --location LOCATION     Azure region (default: japaneast)
    -s, --subscription SUB      Azure subscription ID (default: current)
    -w, --what-if               Run what-if analysis without deploying
    -h, --help                  Show this help message

EXAMPLES:
    # Deploy to development environment
    $0 --environment dev --resource-group dify-dev-rg

    # Deploy to production environment with what-if analysis
    $0 --environment prod --resource-group dify-prod-rg --what-if

    # Deploy to specific subscription
    $0 --environment dev --resource-group dify-dev-rg --subscription xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

EOF
    exit 1
}

# ============================================================================
# Parse Arguments
# ============================================================================

ENVIRONMENT=""
RESOURCE_GROUP=""
LOCATION="japaneast"
SUBSCRIPTION=""
WHAT_IF=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -g|--resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        -l|--location)
            LOCATION="$2"
            shift 2
            ;;
        -s|--subscription)
            SUBSCRIPTION="$2"
            shift 2
            ;;
        -w|--what-if)
            WHAT_IF=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required parameters
if [ -z "$ENVIRONMENT" ]; then
    print_error "Environment is required"
    usage
fi

if [ -z "$RESOURCE_GROUP" ]; then
    print_error "Resource group is required"
    usage
fi

if [[ ! "$ENVIRONMENT" =~ ^(dev|prod)$ ]]; then
    print_error "Environment must be 'dev' or 'prod'"
    usage
fi

# ============================================================================
# Script Execution
# ============================================================================

print_header "Dify on Azure - Deployment Script"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ACR_BICEP_DIR="$PROJECT_ROOT/bicep/acr-only"
MAIN_BICEP_DIR="$PROJECT_ROOT/bicep/main"
ACR_PARAM_FILE="$ACR_BICEP_DIR/parameters/${ENVIRONMENT}.bicepparam"
MAIN_PARAM_FILE="$MAIN_BICEP_DIR/parameters/${ENVIRONMENT}.bicepparam"

print_info "Project root: $PROJECT_ROOT"
print_info "Environment: $ENVIRONMENT"
print_info "Resource group: $RESOURCE_GROUP"
print_info "Location: $LOCATION"
print_info "ACR parameter file: $ACR_PARAM_FILE"
print_info "Main parameter file: $MAIN_PARAM_FILE"

# ============================================================================
# Prerequisites Check
# ============================================================================

print_header "Step 1: Prerequisites Check"

# Run prerequisites validation script
if [ -f "$SCRIPT_DIR/validate-prerequisites.sh" ]; then
    print_info "Running prerequisites validation..."
    bash "$SCRIPT_DIR/validate-prerequisites.sh"
else
    print_warning "Prerequisites validation script not found, skipping..."
fi

# ============================================================================
# Azure Login & Subscription
# ============================================================================

print_header "Step 2: Azure Authentication"

# Check if already logged in
if ! az account show &> /dev/null; then
    print_info "Not logged in to Azure. Starting login process..."
    az login
else
    print_success "Already logged in to Azure"
fi

# Set subscription if provided
if [ -n "$SUBSCRIPTION" ]; then
    print_info "Setting subscription: $SUBSCRIPTION"
    az account set --subscription "$SUBSCRIPTION"
fi

# Show current subscription
CURRENT_SUB=$(az account show --query name -o tsv)
CURRENT_SUB_ID=$(az account show --query id -o tsv)
print_success "Using subscription: $CURRENT_SUB ($CURRENT_SUB_ID)"

# ============================================================================
# Resource Group
# ============================================================================

print_header "Step 3: Resource Group Setup"

# Check if resource group exists
if az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    print_success "Resource group '$RESOURCE_GROUP' already exists"
else
    print_info "Creating resource group '$RESOURCE_GROUP' in '$LOCATION'..."
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
    print_success "Resource group created"
fi

# ============================================================================
# Parameter File Validation
# ============================================================================

print_header "Step 4: Parameter File Validation"

if [ ! -f "$ACR_PARAM_FILE" ]; then
    print_error "ACR parameter file not found: $ACR_PARAM_FILE"
    exit 1
fi

if [ ! -f "$MAIN_PARAM_FILE" ]; then
    print_error "Main parameter file not found: $MAIN_PARAM_FILE"
    exit 1
fi

print_success "ACR parameter file found: $ACR_PARAM_FILE"
print_success "Main parameter file found: $MAIN_PARAM_FILE"

# Remind user to update passwords
print_warning "================================================"
print_warning "IMPORTANT: Ensure you have updated the following"
print_warning "values in the main parameter file:"
print_warning "  - postgresqlAdminPassword"
print_warning "  - keyVaultAdminObjectId"
print_warning "  - difySecretKey"
print_warning "================================================"
echo ""
read -p "Have you updated these values? (yes/no): " CONFIRM
if [[ ! "$CONFIRM" =~ ^(yes|y|Y|YES)$ ]]; then
    print_error "Deployment cancelled. Please update the parameter file first."
    exit 1
fi

# ============================================================================
# Phase 1: Deploy ACR
# ============================================================================

print_header "Phase 1: Deploy ACR"

print_info "Building ACR Bicep template..."
az bicep build --file "$ACR_BICEP_DIR/main.bicep"
print_success "ACR Bicep template built successfully"

print_info "Deploying ACR..."
ACR_DEPLOYMENT_NAME="acr-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"

az deployment group create \
    --name "$ACR_DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$ACR_BICEP_DIR/main.bicep" \
    --parameters "$ACR_PARAM_FILE" \
    --verbose

if [ $? -ne 0 ]; then
    print_error "ACR deployment failed"
    exit 1
fi

print_success "ACR deployed successfully"

# Get ACR information from deployment outputs
print_info "Retrieving ACR information..."
ACR_NAME=$(az deployment group show \
    --name "$ACR_DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query 'properties.outputs.acrName.value' \
    -o tsv)

ACR_LOGIN_SERVER=$(az deployment group show \
    --name "$ACR_DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query 'properties.outputs.acrLoginServer.value' \
    -o tsv)

if [ -z "$ACR_NAME" ] || [ -z "$ACR_LOGIN_SERVER" ]; then
    print_error "Failed to retrieve ACR information from deployment outputs"
    exit 1
fi

print_success "ACR Name: $ACR_NAME"
print_success "ACR Login Server: $ACR_LOGIN_SERVER"

# ============================================================================
# Phase 2: Build and Push nginx Container
# ============================================================================

print_header "Phase 2: Build and Push nginx Container"

print_info "Building and pushing nginx container to ACR..."
bash "$SCRIPT_DIR/build-and-push-nginx.sh" \
    --resource-group "$RESOURCE_GROUP" \
    --acr-name "$ACR_NAME"

if [ $? -ne 0 ]; then
    print_error "nginx container build/push failed"
    print_info "ACR has been deployed but nginx image is not available"
    print_info "You can retry by running: bash scripts/build-and-push-nginx.sh --resource-group $RESOURCE_GROUP --acr-name $ACR_NAME"
    exit 1
fi

print_success "nginx container pushed to ACR successfully"

# Construct nginx image URL
NGINX_IMAGE_URL="${ACR_LOGIN_SERVER}/dify-nginx:latest"
print_success "nginx Image URL: $NGINX_IMAGE_URL"

# Get ACR credentials for Container Apps authentication
print_info "Retrieving ACR credentials..."
ACR_USERNAME=$(az acr credential show \
    --name "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query 'username' \
    -o tsv)

ACR_PASSWORD=$(az acr credential show \
    --name "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query 'passwords[0].value' \
    -o tsv)

if [ -z "$ACR_USERNAME" ] || [ -z "$ACR_PASSWORD" ]; then
    print_error "Failed to retrieve ACR credentials"
    exit 1
fi

print_success "ACR credentials retrieved"

# ============================================================================
# Phase 3: Deploy Main Infrastructure
# ============================================================================

print_header "Phase 3: Deploy Main Infrastructure"

print_info "Building Main Bicep template..."
az bicep build --file "$MAIN_BICEP_DIR/main.bicep"
print_success "Main Bicep template built successfully"

if [ "$WHAT_IF" = true ]; then
    print_info "Running what-if analysis..."
    az deployment group what-if \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$MAIN_BICEP_DIR/main.bicep" \
        --parameters "$MAIN_PARAM_FILE" \
        --parameters acrName="$ACR_NAME" \
        --parameters acrLoginServer="$ACR_LOGIN_SERVER" \
        --parameters acrAdminUsername="$ACR_USERNAME" \
        --parameters acrAdminPassword="$ACR_PASSWORD" \
        --parameters nginxImage="$NGINX_IMAGE_URL"

    print_success "What-if analysis complete"
    print_info "Deployment not executed (--what-if mode)"
    exit 0
fi

print_info "Deploying main infrastructure..."
print_warning "This may take 20-30 minutes..."

MAIN_DEPLOYMENT_NAME="main-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"

az deployment group create \
    --name "$MAIN_DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$MAIN_BICEP_DIR/main.bicep" \
    --parameters "$MAIN_PARAM_FILE" \
    --parameters acrName="$ACR_NAME" \
    --parameters acrLoginServer="$ACR_LOGIN_SERVER" \
    --parameters acrAdminUsername="$ACR_USERNAME" \
    --parameters acrAdminPassword="$ACR_PASSWORD" \
    --parameters nginxImage="$NGINX_IMAGE_URL" \
    --verbose

if [ $? -ne 0 ]; then
    print_error "Main infrastructure deployment failed"
    print_info "ACR and nginx image are available"
    print_info "You can retry the main deployment with the same parameters"
    exit 1
fi

print_success "Main infrastructure deployed successfully!"

# ============================================================================
# Deployment Outputs
# ============================================================================

print_header "Deployment Outputs"

print_info "Fetching deployment outputs..."

OUTPUTS=$(az deployment group show \
    --name "$MAIN_DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.outputs \
    -o json)

echo "$OUTPUTS" | jq .

# Extract key outputs
APP_GATEWAY_IP=$(echo "$OUTPUTS" | jq -r '.applicationGatewayPublicIp.value // empty')
APP_GATEWAY_FQDN=$(echo "$OUTPUTS" | jq -r '.applicationGatewayFqdn.value // empty')
KEY_VAULT_NAME=$(echo "$OUTPUTS" | jq -r '.keyVaultName.value // empty')

if [ -n "$APP_GATEWAY_FQDN" ]; then
    print_success "Application Gateway FQDN: $APP_GATEWAY_FQDN"
    print_info "You can access Dify at: http://$APP_GATEWAY_FQDN"
fi

if [ -n "$APP_GATEWAY_IP" ]; then
    print_success "Application Gateway IP: $APP_GATEWAY_IP"
fi

# ============================================================================
# Post-Deployment Steps
# ============================================================================

print_header "Post-Deployment Steps"

print_info "Next steps:"
echo ""
echo "1. Store secrets in Key Vault:"
echo "   Run: bash scripts/setup-secrets.sh -g $RESOURCE_GROUP -k $KEY_VAULT_NAME"
echo ""
echo "2. Configure DNS (if using custom domain):"
echo "   Point your domain to: $APP_GATEWAY_IP"
echo ""
echo "3. Upload SSL certificate to Key Vault (for HTTPS):"
echo "   az keyvault certificate import --vault-name $KEY_VAULT_NAME --name dify-ssl-cert --file cert.pfx"
echo ""
echo "4. Update Application Gateway with SSL certificate"
echo ""
echo "5. Access the application:"
echo "   URL: http://$APP_GATEWAY_FQDN"
echo ""

print_success "Deployment process complete!"
