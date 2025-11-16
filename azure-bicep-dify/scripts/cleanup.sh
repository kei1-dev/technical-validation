#!/bin/bash

# ============================================================================
# Cleanup Script - Delete Azure resources
# ============================================================================

set -e

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

Delete Dify on Azure infrastructure resources

OPTIONS:
    -g, --resource-group RG     Resource group name [required]
    -f, --force                 Skip confirmation prompt
    -h, --help                  Show this help message

EXAMPLES:
    # Delete resource group (with confirmation)
    $0 --resource-group dify-dev-rg

    # Delete resource group (skip confirmation)
    $0 --resource-group dify-dev-rg --force

EOF
    exit 1
}

# ============================================================================
# Parse Arguments
# ============================================================================

RESOURCE_GROUP=""
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -g|--resource-group)
            RESOURCE_GROUP="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
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
if [ -z "$RESOURCE_GROUP" ]; then
    print_error "Resource group is required"
    usage
fi

# ============================================================================
# Script Execution
# ============================================================================

print_header "Dify on Azure - Cleanup Script"

# Check if resource group exists
if ! az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    print_error "Resource group '$RESOURCE_GROUP' does not exist"
    exit 1
fi

print_info "Resource group: $RESOURCE_GROUP"

# ============================================================================
# List Resources
# ============================================================================

print_header "Resources to be deleted"

print_info "Listing resources in resource group..."

RESOURCES=$(az resource list --resource-group "$RESOURCE_GROUP" --query "[].{Type:type, Name:name}" -o tsv)

if [ -z "$RESOURCES" ]; then
    print_warning "No resources found in resource group '$RESOURCE_GROUP'"
else
    echo "$RESOURCES" | while IFS=$'\t' read -r TYPE NAME; do
        echo "  - $NAME ($TYPE)"
    done
fi

echo ""

# Count resources
RESOURCE_COUNT=$(az resource list --resource-group "$RESOURCE_GROUP" --query "length([])" -o tsv)
print_warning "Total resources: $RESOURCE_COUNT"

# ============================================================================
# Confirmation
# ============================================================================

if [ "$FORCE" = false ]; then
    print_warning "============================================"
    print_warning "THIS WILL DELETE ALL RESOURCES IN:"
    print_warning "  Resource Group: $RESOURCE_GROUP"
    print_warning "  Resource Count: $RESOURCE_COUNT"
    print_warning "============================================"
    echo ""
    print_error "THIS ACTION CANNOT BE UNDONE!"
    echo ""

    read -p "Are you sure you want to delete this resource group? (yes/no): " CONFIRM

    if [[ ! "$CONFIRM" =~ ^(yes|YES)$ ]]; then
        print_info "Cleanup cancelled"
        exit 0
    fi

    echo ""
    read -p "Type the resource group name to confirm: " CONFIRM_RG

    if [ "$CONFIRM_RG" != "$RESOURCE_GROUP" ]; then
        print_error "Resource group name does not match. Cleanup cancelled."
        exit 1
    fi
fi

# ============================================================================
# Handle Key Vault Purge Protection
# ============================================================================

print_header "Step 1: Check Key Vault Purge Protection"

KEY_VAULTS=$(az keyvault list --resource-group "$RESOURCE_GROUP" --query "[].name" -o tsv)

if [ -n "$KEY_VAULTS" ]; then
    for KV in $KEY_VAULTS; do
        PURGE_PROTECTION=$(az keyvault show --name "$KV" --query "properties.enablePurgeProtection" -o tsv)

        if [ "$PURGE_PROTECTION" = "true" ]; then
            print_warning "Key Vault '$KV' has purge protection enabled"
            print_warning "After deletion, you will need to manually purge it within 90 days or wait for automatic purge"
            print_info "To manually purge: az keyvault purge --name $KV"
        fi
    done
fi

# ============================================================================
# Delete Resource Group
# ============================================================================

print_header "Step 2: Delete Resource Group"

print_info "Deleting resource group '$RESOURCE_GROUP'..."
print_warning "This may take 10-20 minutes..."

az group delete \
    --name "$RESOURCE_GROUP" \
    --yes \
    --no-wait=false

if [ $? -eq 0 ]; then
    print_success "Resource group '$RESOURCE_GROUP' deleted successfully"
else
    print_error "Failed to delete resource group '$RESOURCE_GROUP'"
    exit 1
fi

# ============================================================================
# Cleanup Soft-Deleted Resources
# ============================================================================

print_header "Step 3: Check Soft-Deleted Resources"

# Check for soft-deleted Key Vaults
print_info "Checking for soft-deleted Key Vaults..."

SOFT_DELETED_KVS=$(az keyvault list-deleted --query "[?properties.tags.Project=='Dify'].name" -o tsv 2>/dev/null || echo "")

if [ -n "$SOFT_DELETED_KVS" ]; then
    print_warning "Found soft-deleted Key Vaults:"
    for KV in $SOFT_DELETED_KVS; do
        echo "  - $KV"
        print_info "To purge immediately: az keyvault purge --name $KV"
    done
else
    print_info "No soft-deleted Key Vaults found"
fi

# ============================================================================
# Summary
# ============================================================================

print_header "Cleanup Complete"

print_success "Resource group '$RESOURCE_GROUP' has been deleted"

if [ -n "$SOFT_DELETED_KVS" ]; then
    echo ""
    print_warning "Note: Some resources may be in soft-delete state:"
    echo "  - Key Vaults (recoverable for 90 days unless purged)"
    echo ""
    print_info "To purge all soft-deleted Key Vaults:"
    for KV in $SOFT_DELETED_KVS; do
        echo "  az keyvault purge --name $KV"
    done
fi

echo ""
print_success "Cleanup process complete!"
