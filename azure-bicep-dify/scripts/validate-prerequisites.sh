#!/bin/bash

# ============================================================================
# Prerequisites Validation Script
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
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# ============================================================================
# Validation
# ============================================================================

echo ""
echo "============================================================"
echo "Prerequisites Validation"
echo "============================================================"
echo ""

ERRORS=0

# Check Azure CLI
print_info "Checking Azure CLI..."
if command -v az &> /dev/null; then
    AZ_VERSION=$(az version --query '"azure-cli"' -o tsv)
    print_success "Azure CLI installed (version: $AZ_VERSION)"

    # Check if version is recent enough (>= 2.40.0)
    REQUIRED_VERSION="2.40.0"
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$AZ_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
        print_warning "Azure CLI version is older than recommended ($REQUIRED_VERSION). Please consider updating."
    fi
else
    print_error "Azure CLI is not installed"
    echo "  Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    ERRORS=$((ERRORS + 1))
fi

# Check Bicep CLI
print_info "Checking Bicep CLI..."
if az bicep version &> /dev/null; then
    BICEP_VERSION=$(az bicep version)
    print_success "Bicep CLI installed ($BICEP_VERSION)"

    # Check if upgrade is available
    if az bicep upgrade --dry-run &> /dev/null; then
        print_info "Bicep upgrade available. Run: az bicep upgrade"
    fi
else
    print_error "Bicep CLI is not installed"
    echo "  Install with: az bicep install"
    ERRORS=$((ERRORS + 1))
fi

# Check jq (for JSON parsing)
print_info "Checking jq..."
if command -v jq &> /dev/null; then
    JQ_VERSION=$(jq --version)
    print_success "jq installed ($JQ_VERSION)"
else
    print_warning "jq is not installed (recommended for deployment script)"
    echo "  Install from: https://stedolan.github.io/jq/download/"
fi

# Check Azure login status
print_info "Checking Azure login status..."
if az account show &> /dev/null; then
    ACCOUNT_NAME=$(az account show --query name -o tsv)
    SUBSCRIPTION_ID=$(az account show --query id -o tsv)
    print_success "Logged in to Azure"
    echo "  Subscription: $ACCOUNT_NAME"
    echo "  ID: $SUBSCRIPTION_ID"
else
    print_error "Not logged in to Azure"
    echo "  Run: az login"
    ERRORS=$((ERRORS + 1))
fi

# Check Azure subscription permissions
if az account show &> /dev/null; then
    print_info "Checking Azure permissions..."

    # Check if user can create resources
    SUBSCRIPTION_ID=$(az account show --query id -o tsv)

    # Try to list resource groups (basic permission check)
    if az group list --query "[0].name" -o tsv &> /dev/null; then
        print_success "Basic Azure permissions verified"
    else
        print_error "Insufficient permissions to list resource groups"
        ERRORS=$((ERRORS + 1))
    fi

    # Check if user can create role assignments (needed for Automation Account)
    print_info "Checking role assignment permissions..."
    CURRENT_USER=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || echo "")
    if [ -n "$CURRENT_USER" ]; then
        print_success "Can query current user ($CURRENT_USER)"
    else
        print_warning "Cannot query current user. Role assignments may fail."
        print_warning "You may need 'Owner' or 'User Access Administrator' role."
    fi
fi

# Check required Azure resource providers
print_info "Checking Azure resource providers..."

REQUIRED_PROVIDERS=(
    "Microsoft.Network"
    "Microsoft.Storage"
    "Microsoft.KeyVault"
    "Microsoft.DBforPostgreSQL"
    "Microsoft.Cache"
    "Microsoft.App"
    "Microsoft.OperationalInsights"
    "Microsoft.Insights"
    "Microsoft.Automation"
    "Microsoft.ManagedIdentity"
)

for PROVIDER in "${REQUIRED_PROVIDERS[@]}"; do
    STATUS=$(az provider show --namespace "$PROVIDER" --query "registrationState" -o tsv 2>/dev/null || echo "Unknown")
    if [ "$STATUS" = "Registered" ]; then
        print_success "$PROVIDER: Registered"
    elif [ "$STATUS" = "Registering" ]; then
        print_warning "$PROVIDER: Currently registering..."
    else
        print_error "$PROVIDER: Not registered"
        echo "  Register with: az provider register --namespace $PROVIDER"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check available quota (approximate)
print_info "Checking approximate resource quotas..."

# This is a basic check - actual quota verification requires more complex logic
print_info "Note: Quota checks are approximate. Actual limits may vary by region."

# Check Container Apps quota
print_info "Checking Container Apps availability..."
LOCATION="japaneast"
if az provider show --namespace Microsoft.App --query "resourceTypes[?resourceType=='managedEnvironments'].locations[]" -o tsv | grep -qi "$LOCATION"; then
    print_success "Container Apps available in $LOCATION"
else
    print_warning "Container Apps may not be available in $LOCATION"
fi

echo ""
echo "============================================================"
echo "Prerequisites Summary"
echo "============================================================"
echo ""

if [ $ERRORS -eq 0 ]; then
    print_success "All prerequisites validated successfully!"
    echo ""
    echo "You can proceed with deployment."
    exit 0
else
    print_error "Found $ERRORS error(s) in prerequisites"
    echo ""
    echo "Please resolve the errors above before deploying."
    exit 1
fi
