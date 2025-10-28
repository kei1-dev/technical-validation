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
BICEP_DIR="$PROJECT_ROOT/bicep"
PARAM_FILE="$BICEP_DIR/parameters/${ENVIRONMENT}.bicepparam"

print_info "Project root: $PROJECT_ROOT"
print_info "Environment: $ENVIRONMENT"
print_info "Resource group: $RESOURCE_GROUP"
print_info "Location: $LOCATION"
print_info "Parameter file: $PARAM_FILE"

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

if [ ! -f "$PARAM_FILE" ]; then
    print_error "Parameter file not found: $PARAM_FILE"
    exit 1
fi

print_success "Parameter file found: $PARAM_FILE"

# Remind user to update passwords
print_warning "================================================"
print_warning "IMPORTANT: Ensure you have updated the following"
print_warning "values in the parameter file:"
print_warning "  - postgresqlAdminPassword"
print_warning "  - keyVaultAdminObjectId"
print_warning "================================================"
echo ""
read -p "Have you updated these values? (yes/no): " CONFIRM
if [[ ! "$CONFIRM" =~ ^(yes|y|Y|YES)$ ]]; then
    print_error "Deployment cancelled. Please update the parameter file first."
    exit 1
fi

# ============================================================================
# Bicep Build & Validation
# ============================================================================

print_header "Step 5: Bicep Build & Validation"

print_info "Building Bicep template..."
az bicep build --file "$BICEP_DIR/main.bicep"
print_success "Bicep template built successfully"

print_info "Validating deployment..."
az deployment group validate \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$BICEP_DIR/main.bicep" \
    --parameters "$PARAM_FILE"
print_success "Deployment validation passed"

# ============================================================================
# What-If Analysis
# ============================================================================

if [ "$WHAT_IF" = true ]; then
    print_header "What-If Analysis"

    print_info "Running what-if analysis..."
    az deployment group what-if \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$BICEP_DIR/main.bicep" \
        --parameters "$PARAM_FILE"

    print_success "What-if analysis complete"
    print_info "Deployment not executed (--what-if mode)"
    exit 0
fi

# ============================================================================
# Deployment
# ============================================================================

print_header "Step 6: Deployment"

print_info "Starting deployment..."
print_warning "This may take 20-30 minutes..."

DEPLOYMENT_NAME="dify-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"

az deployment group create \
    --name "$DEPLOYMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$BICEP_DIR/main.bicep" \
    --parameters "$PARAM_FILE" \
    --verbose

if [ $? -eq 0 ]; then
    print_success "Deployment completed successfully!"
else
    print_error "Deployment failed!"
    exit 1
fi

# ============================================================================
# Deployment Outputs
# ============================================================================

print_header "Step 7: Deployment Outputs"

print_info "Fetching deployment outputs..."

OUTPUTS=$(az deployment group show \
    --name "$DEPLOYMENT_NAME" \
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
