#!/bin/bash

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
AUTO_YES=false
SKIP_SHELL_CLEANUP=false
SKIP_GCLOUD_UNINSTALL=false

# Help function
show_help() {
    cat << EOF
Google Cloud Vertex AI Teardown for Claude Code

Usage: $0 [OPTIONS]

OPTIONS:
  -y, --yes                    Skip all confirmation prompts (auto-approve)
  --skip-shell-cleanup         Skip shell profile cleanup
  --skip-gcloud-uninstall      Skip gcloud CLI uninstallation
  -h, --help                   Show this help message

EXAMPLES:
  # Interactive teardown (with confirmations)
  $0

  # Fully automated teardown
  $0 -y

  # Remove only project config files (keep gcloud CLI and shell profile)
  $0 -y --skip-shell-cleanup --skip-gcloud-uninstall

  # Remove config and gcloud CLI, but keep shell profile
  $0 --skip-shell-cleanup

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -y|--yes)
            AUTO_YES=true
            shift
            ;;
        --skip-shell-cleanup)
            SKIP_SHELL_CLEANUP=true
            shift
            ;;
        --skip-gcloud-uninstall)
            SKIP_GCLOUD_UNINSTALL=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        -*)
            echo -e "${RED}Error: Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
        *)
            echo -e "${RED}Error: Unexpected argument: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

echo "========================================="
echo "Google Cloud Vertex AI Teardown for Claude Code"
echo "========================================="
echo ""

if [ "$AUTO_YES" = true ]; then
    echo -e "${YELLOW}Running in non-interactive mode (--yes)${NC}"
    echo ""
fi

# Check if configuration files exist
if [ ! -f .env ] && [ ! -f .claude/settings.json ]; then
    echo -e "${YELLOW}No Vertex AI configuration found.${NC}"
    echo "Nothing to remove."
    exit 0
fi

echo "This will remove the following:"
if [ -f .env ]; then
    echo "  - .env file"
fi
if [ -f .claude/settings.json ]; then
    echo "  - .claude/settings.json file"
fi
if [ -d .claude ]; then
    echo "  - .claude/ directory (if empty after removal)"
fi

# Check for shell profile cleanup
SHELL_PROFILE=""
if [ "$SKIP_SHELL_CLEANUP" = false ]; then
    # Detect shell and set appropriate profile file
    # Use $SHELL environment variable to detect user's login shell
    # (not $ZSH_VERSION/$BASH_VERSION as this script runs in bash)
    case "$SHELL" in
        */zsh)
            SHELL_PROFILE="$HOME/.zshrc"
            SHELL_NAME="Zsh"
            ;;
        */bash)
            SHELL_PROFILE="$HOME/.bashrc"
            SHELL_NAME="Bash"
            ;;
        *)
            # Default to bash if shell is unknown
            SHELL_PROFILE="$HOME/.bashrc"
            SHELL_NAME="Bash (default)"
            ;;
    esac

    if [ -f "$SHELL_PROFILE" ] && grep -q "google-cloud-sdk/path" "$SHELL_PROFILE"; then
        echo "  - gcloud CLI configuration from $SHELL_PROFILE"
    fi

    if [ -f "$SHELL_PROFILE" ] && grep -q "# Added by Vertex AI Setup Script - Claude Code Aliases" "$SHELL_PROFILE"; then
        echo "  - Claude Code aliases from $SHELL_PROFILE"
    fi
fi

# Check for gcloud CLI installation
GCLOUD_SDK_PATH="$HOME/google-cloud-sdk"
if [ "$SKIP_GCLOUD_UNINSTALL" = false ] && [ -d "$GCLOUD_SDK_PATH" ]; then
    echo "  - gcloud CLI installation ($GCLOUD_SDK_PATH)"
fi

echo ""

# Confirm deletion
if [ "$AUTO_YES" = false ]; then
    read -p "Do you want to continue? (y/N): " CONFIRM

    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "Teardown cancelled."
        exit 0
    fi
fi

echo ""

# Create backup directory with timestamp
BACKUP_DIR=".vertex-ai-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Creating backup in $BACKUP_DIR..."

# Backup .env file
if [ -f .env ]; then
    cp .env "$BACKUP_DIR/"
    echo -e "${GREEN}✓ Backed up .env${NC}"
fi

# Backup .claude directory
if [ -d .claude ]; then
    cp -r .claude "$BACKUP_DIR/"
    echo -e "${GREEN}✓ Backed up .claude/${NC}"
fi

# Backup shell profile if we're going to modify it
if [ "$SKIP_SHELL_CLEANUP" = false ] && [ -f "$SHELL_PROFILE" ]; then
    PROFILE_BACKUP="$SHELL_PROFILE.bak.$(date +%Y%m%d-%H%M%S)"
    cp "$SHELL_PROFILE" "$PROFILE_BACKUP"
    echo -e "${GREEN}✓ Backed up $SHELL_PROFILE to $PROFILE_BACKUP${NC}"
fi

echo ""

# Remove configuration files
if [ -f .env ]; then
    rm .env
    echo -e "${GREEN}✓ Removed .env${NC}"
fi

if [ -d .claude ]; then
    rm -rf .claude
    echo -e "${GREEN}✓ Removed .claude/${NC}"
fi

echo ""

# Clean up shell profile
if [ "$SKIP_SHELL_CLEANUP" = false ]; then
    if [ -f "$SHELL_PROFILE" ] && grep -q "google-cloud-sdk/path" "$SHELL_PROFILE"; then
        echo "Cleaning up $SHELL_PROFILE..."

        # Remove the lines added by the setup script
        # This removes:
        # - The comment line: "# Added by Google Cloud Vertex AI Setup Script"
        # - The two source lines for path.*.inc and completion.*.inc
        # - Any blank lines immediately before the comment

        # Create a temporary file
        TEMP_FILE=$(mktemp)

        # Use sed to remove the specific lines
        # -i '' for macOS (BSD sed), -i for Linux (GNU sed)
        if sed --version >/dev/null 2>&1; then
            # GNU sed (Linux)
            sed -i '/# Added by Google Cloud Vertex AI Setup Script/,+2d' "$SHELL_PROFILE"
        else
            # BSD sed (macOS)
            sed -i '' '/# Added by Google Cloud Vertex AI Setup Script/,+2d' "$SHELL_PROFILE"
        fi

        # Also remove any empty lines that might be left
        if sed --version >/dev/null 2>&1; then
            sed -i '/^$/N;/^\n$/d' "$SHELL_PROFILE"
        else
            sed -i '' '/^$/N;/^\n$/d' "$SHELL_PROFILE"
        fi

        echo -e "${GREEN}✓ Removed gcloud CLI configuration from $SHELL_PROFILE${NC}"
        echo -e "${YELLOW}Note: Restart your terminal or run 'source $SHELL_PROFILE' for changes to take effect${NC}"
    else
        echo "No gcloud CLI configuration found in $SHELL_PROFILE"
    fi
    echo ""

    # Clean up Claude Code aliases
    if [ -f "$SHELL_PROFILE" ] && grep -q "# Added by Vertex AI Setup Script - Claude Code Aliases" "$SHELL_PROFILE"; then
        echo "Cleaning up Claude Code aliases from $SHELL_PROFILE..."

        # Remove the lines added by the setup script
        # This removes:
        # - The comment line: "# Added by Vertex AI Setup Script - Claude Code Aliases"
        # - The two alias lines
        # - Any blank lines immediately before the comment

        if sed --version >/dev/null 2>&1; then
            # GNU sed (Linux)
            sed -i '/# Added by Vertex AI Setup Script - Claude Code Aliases/,+2d' "$SHELL_PROFILE"
        else
            # BSD sed (macOS)
            sed -i '' '/# Added by Vertex AI Setup Script - Claude Code Aliases/,+2d' "$SHELL_PROFILE"
        fi

        # Also remove any empty lines that might be left
        if sed --version >/dev/null 2>&1; then
            sed -i '/^$/N;/^\n$/d' "$SHELL_PROFILE"
        else
            sed -i '' '/^$/N;/^\n$/d' "$SHELL_PROFILE"
        fi

        echo -e "${GREEN}✓ Removed Claude Code aliases from $SHELL_PROFILE${NC}"
    else
        echo "No Claude Code aliases found in $SHELL_PROFILE"
    fi
    echo ""
fi

# Uninstall gcloud CLI
if [ "$SKIP_GCLOUD_UNINSTALL" = false ]; then
    if [ -d "$GCLOUD_SDK_PATH" ]; then
        echo "Uninstalling gcloud CLI..."

        # Verify the path is correct before deleting
        if [ "$GCLOUD_SDK_PATH" = "$HOME/google-cloud-sdk" ]; then
            rm -rf "$GCLOUD_SDK_PATH"
            echo -e "${GREEN}✓ Removed gcloud CLI from $GCLOUD_SDK_PATH${NC}"
        else
            echo -e "${RED}Error: Unexpected gcloud SDK path: $GCLOUD_SDK_PATH${NC}"
            echo "Skipping gcloud CLI uninstallation for safety"
        fi
    else
        echo "gcloud CLI not found at $GCLOUD_SDK_PATH"
    fi
    echo ""
fi

echo "========================================="
echo -e "${GREEN}Teardown Complete!${NC}"
echo "========================================="
echo ""
echo "Configuration files have been removed."
echo "Backup saved in: $BACKUP_DIR"
echo ""

if [ "$SKIP_SHELL_CLEANUP" = true ] || [ "$SKIP_GCLOUD_UNINSTALL" = true ]; then
    echo "Note: Some components were not removed (as requested):"
    if [ "$SKIP_SHELL_CLEANUP" = true ]; then
        echo "  - Shell profile still contains gcloud CLI configuration"
    fi
    if [ "$SKIP_GCLOUD_UNINSTALL" = true ]; then
        echo "  - gcloud CLI is still installed at $GCLOUD_SDK_PATH"
    fi
    echo ""
fi

echo "Note: This script does not:"
echo "  - Disable Vertex AI API in your GCP project"
echo "  - Remove Application Default Credentials"
echo ""
echo "To completely reset authentication, run:"
echo "  gcloud auth application-default revoke"
echo ""
