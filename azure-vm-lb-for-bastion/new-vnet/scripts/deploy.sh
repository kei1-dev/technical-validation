#!/bin/bash

###############################################################################
# Azure Bastion VM Infrastructure Deployment Script
#
# This script deploys:
# - Load Balancer VNet and VM VNet with VNet Peering
# - Internal Load Balancer with NAT Rules
# - Private Link Service
# - Private Endpoint in Hub VNet
# - Multiple bastion VMs
###############################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BICEP_DIR="$PROJECT_ROOT/bicep"
PARAMS_FILE="$BICEP_DIR/parameters/main.parameters.json"
MAIN_BICEP="$BICEP_DIR/main.bicep"

###############################################################################
# Functions
###############################################################################

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed. Please install it first."
        exit 1
    fi

    # Check Bicep CLI
    if ! command -v bicep &> /dev/null; then
        log_warn "Bicep CLI not found. Installing via Azure CLI..."
        az bicep install
    fi

    # Check if logged in
    if ! az account show &> /dev/null; then
        log_error "Not logged in to Azure. Please run 'az login' first."
        exit 1
    fi

    log_info "Prerequisites check passed."
}

validate_parameters() {
    log_info "Validating parameters file..."

    if [ ! -f "$PARAMS_FILE" ]; then
        log_error "Parameters file not found: $PARAMS_FILE"
        exit 1
    fi

    # Check for placeholder values
    if grep -q "<SUBSCRIPTION_ID>" "$PARAMS_FILE"; then
        log_error "Please replace <SUBSCRIPTION_ID> in $PARAMS_FILE with your actual subscription ID."
        exit 1
    fi

    log_info "Parameters validation passed."
}

build_bicep() {
    log_info "Building Bicep template..."
    az bicep build --file "$MAIN_BICEP"
    log_info "Bicep build completed."
}

validate_deployment() {
    log_info "Validating deployment (what-if mode)..."

    az deployment sub what-if \
        --location japaneast \
        --template-file "$MAIN_BICEP" \
        --parameters "$PARAMS_FILE"

    log_info "Validation completed. Review the changes above."
}

deploy_infrastructure() {
    log_info "Starting deployment..."

    DEPLOYMENT_NAME="bastion-lb-$(date +%Y%m%d-%H%M%S)"

    az deployment sub create \
        --name "$DEPLOYMENT_NAME" \
        --location japaneast \
        --template-file "$MAIN_BICEP" \
        --parameters "$PARAMS_FILE" \
        --verbose

    if [ $? -eq 0 ]; then
        log_info "Deployment completed successfully."
        return 0
    else
        log_error "Deployment failed. Check the error messages above."
        return 1
    fi
}

show_outputs() {
    log_info "Fetching deployment outputs..."

    LATEST_DEPLOYMENT=$(az deployment sub list --query "[?contains(name, 'bastion-lb')].name" -o tsv | head -n 1)

    if [ -z "$LATEST_DEPLOYMENT" ]; then
        log_warn "No deployment found."
        return
    fi

    OUTPUTS=$(az deployment sub show --name "$LATEST_DEPLOYMENT" --query properties.outputs -o json)

    echo ""
    echo "=========================================="
    echo "Deployment Outputs"
    echo "=========================================="
    echo "$OUTPUTS" | jq '.'
    echo ""

    # Extract SSH connection info
    SSH_INFO=$(echo "$OUTPUTS" | jq -r '.sshConnectionInfo.value[]')

    if [ -n "$SSH_INFO" ]; then
        echo "=========================================="
        echo "SSH Connection Commands"
        echo "=========================================="
        echo "$OUTPUTS" | jq -r '.sshConnectionInfo.value[] | .sshCommand'
        echo ""
    fi
}

approve_private_link() {
    log_info "Checking Private Link Service connections..."

    RG_LB="rg-lb-bastion"
    PLS_NAME="pls-bastion"

    # List connections
    CONNECTIONS=$(az network private-endpoint-connection list \
        --name "$PLS_NAME" \
        --resource-group "$RG_LB" \
        --type Microsoft.Network/privateLinkServices \
        --query "[?properties.privateLinkServiceConnectionState.status=='Pending'].name" -o tsv)

    if [ -z "$CONNECTIONS" ]; then
        log_info "No pending Private Link connections to approve."
        return
    fi

    log_warn "Pending Private Link connections found:"
    echo "$CONNECTIONS"

    read -p "Do you want to approve all pending connections? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        for CONN in $CONNECTIONS; do
            log_info "Approving connection: $CONN"
            az network private-endpoint-connection approve \
                --name "$CONN" \
                --resource-name "$PLS_NAME" \
                --resource-group "$RG_LB" \
                --type Microsoft.Network/privateLinkServices \
                --description "Auto-approved by deployment script"
        done
        log_info "All connections approved."
    fi
}

download_ssh_private_key() {
    log_info "Checking for SSH Key to download..."

    LATEST_DEPLOYMENT=$(az deployment sub list --query "[?contains(name, 'bastion-lb')].name" -o tsv | head -n 1)

    if [ -z "$LATEST_DEPLOYMENT" ]; then
        log_warn "No deployment found. Cannot retrieve SSH Key info."
        return
    fi

    SSH_KEY_NAME=$(az deployment sub show --name "$LATEST_DEPLOYMENT" --query "properties.outputs.sshKeyName.value" -o tsv 2>/dev/null)
    SSH_KEY_RG=$(az deployment sub show --name "$LATEST_DEPLOYMENT" --query "properties.outputs.sshKeyResourceGroup.value" -o tsv 2>/dev/null)

    if [ -z "$SSH_KEY_NAME" ] || [ -z "$SSH_KEY_RG" ]; then
        log_warn "SSH Key info not found in deployment outputs."
        return
    fi

    echo ""
    echo "=========================================="
    echo "SSH Private Key Download"
    echo "=========================================="
    log_info "Azure has generated an SSH key pair for you."
    log_warn "IMPORTANT: The private key can only be retrieved ONCE, immediately after deployment."
    echo ""

    SSH_DIR="$PROJECT_ROOT/.ssh"
    PRIVATE_KEY_FILE="$SSH_DIR/${SSH_KEY_NAME}.pem"

    read -p "Do you want to download the private key now? (Y/n): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Nn]$ ]]; then
        log_warn "Skipping private key download."
        echo ""
        log_info "You can manually retrieve it later using:"
        echo "  az sshkey show --resource-group $SSH_KEY_RG --name $SSH_KEY_NAME --query 'publicKey' -o tsv"
        echo ""
        echo "Note: The private key can only be accessed through Azure Portal or via the SSH extension."
        return
    fi

    # Create .ssh directory if it doesn't exist
    mkdir -p "$SSH_DIR"

    # Note: Azure-generated SSH keys don't expose the private key via CLI for security
    # Users must use Azure Portal or az ssh commands
    log_warn "Azure-managed SSH keys do not expose the private key via CLI for security reasons."
    echo ""
    echo "To connect to your VMs, use one of the following methods:"
    echo ""
    echo "1. Use Azure CLI SSH (recommended):"
    echo "   az ssh vm --resource-group $SSH_KEY_RG --name vm-bastion-1"
    echo ""
    echo "2. Configure SSH config using Azure extension:"
    echo "   az ssh config --file ~/.ssh/config --resource-group $SSH_KEY_RG --name $SSH_KEY_NAME"
    echo ""
    echo "3. Download from Azure Portal:"
    echo "   Portal → $SSH_KEY_RG → $SSH_KEY_NAME → 'Download private key'"
    echo ""

    log_info "SSH public key location: Azure Portal → $SSH_KEY_RG → $SSH_KEY_NAME"
}

###############################################################################
# Main execution
###############################################################################

main() {
    echo ""
    echo "=========================================="
    echo "Azure Bastion VM Infrastructure Deployment"
    echo "=========================================="
    echo ""

    # Check prerequisites
    check_prerequisites

    # Validate parameters
    validate_parameters

    # Build Bicep
    build_bicep

    # Ask for what-if
    read -p "Do you want to run what-if validation? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        validate_deployment
    fi

    # Confirm deployment
    echo ""
    read -p "Proceed with deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warn "Deployment cancelled by user."
        exit 0
    fi

    # Deploy
    if deploy_infrastructure; then
        # Show outputs
        show_outputs

        # Download SSH private key
        download_ssh_private_key

        # Approve Private Link
        approve_private_link

        echo ""
        echo "=========================================="
        log_info "All done! Your bastion VM infrastructure is ready."
        echo "=========================================="
    else
        log_error "Deployment failed. Please check the errors and try again."
        exit 1
    fi
}

# Run main function
main "$@"
