#!/bin/bash

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
AUTO_YES=false
SKIP_GCLOUD_INSTALL=false
SKIP_PROFILE_UPDATE=false
SKIP_AUTH=false
PROJECT_ID=""

# Help function
show_help() {
    cat << EOF
Google Cloud Vertex AI Setup for Claude Code

Usage: $0 [OPTIONS] [PROJECT_ID]

OPTIONS:
  -y, --yes                  Skip all confirmation prompts (auto-approve)
  -p, --project PROJECT      Specify Google Cloud Project ID
  --skip-gcloud-install      Skip gcloud CLI installation
  --skip-profile-update      Skip shell profile update
  --skip-auth                Skip ADC authentication
  -h, --help                 Show this help message

ARGUMENTS:
  PROJECT_ID                 Google Cloud Project ID (alternative to -p)

EXAMPLES:
  # Fully automated setup
  $0 -y my-project-id

  # Setup with specific options
  $0 --yes --skip-auth --project my-project-id

  # Skip gcloud installation (already installed)
  $0 -y --skip-gcloud-install my-project-id

ENVIRONMENT VARIABLES:
  GOOGLE_CLOUD_PROJECT       If set, used as default project ID

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
        -p|--project)
            PROJECT_ID="$2"
            shift 2
            ;;
        --skip-gcloud-install)
            SKIP_GCLOUD_INSTALL=true
            shift
            ;;
        --skip-profile-update)
            SKIP_PROFILE_UPDATE=true
            shift
            ;;
        --skip-auth)
            SKIP_AUTH=true
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
            # Positional argument (PROJECT_ID)
            if [ -z "$PROJECT_ID" ]; then
                PROJECT_ID="$1"
            else
                echo -e "${RED}Error: Multiple project IDs specified${NC}"
                exit 1
            fi
            shift
            ;;
    esac
done

# Use environment variable if PROJECT_ID not specified
if [ -z "$PROJECT_ID" ] && [ -n "$GOOGLE_CLOUD_PROJECT" ]; then
    PROJECT_ID="$GOOGLE_CLOUD_PROJECT"
fi

echo "========================================="
echo "Google Cloud Vertex AI Setup for Claude Code"
echo "========================================="
echo ""

if [ "$AUTO_YES" = true ]; then
    echo -e "${YELLOW}Running in non-interactive mode (--yes)${NC}"
    echo ""
fi

# Function to install gcloud CLI
install_gcloud_cli() {
    # Save current directory to return to it later
    ORIGINAL_DIR=$(pwd)

    echo ""
    echo "gcloud CLI is not installed on your system."
    echo ""

    if [ "$AUTO_YES" = false ]; then
        read -p "Would you like to install it now? (y/N): " INSTALL_CONFIRM
        if [[ ! "$INSTALL_CONFIRM" =~ ^[Yy]$ ]]; then
            echo ""
            echo "Please install Google Cloud CLI manually from:"
            echo "https://cloud.google.com/sdk/docs/install"
            cd "$ORIGINAL_DIR"
            exit 1
        fi
    else
        echo "Auto-installing gcloud CLI..."
    fi

    echo ""
    echo "Installing gcloud CLI using official installer..."
    echo ""

    # Determine the appropriate installer for macOS
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        # Apple Silicon (M1/M2/M3)
        INSTALLER_URL="https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-darwin-arm.tar.gz"
        INSTALLER_FILE="google-cloud-cli-darwin-arm.tar.gz"
    else
        # Intel Mac
        INSTALLER_URL="https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-darwin-x86_64.tar.gz"
        INSTALLER_FILE="google-cloud-cli-darwin-x86_64.tar.gz"
    fi

    INSTALL_DIR="$HOME/google-cloud-sdk"

    echo "Detected architecture: $ARCH"
    echo "Download URL: $INSTALLER_URL"
    echo "Install location: $INSTALL_DIR"
    echo ""

    # Download the installer
    echo "Downloading gcloud CLI..."
    cd /tmp
    if curl -o "$INSTALLER_FILE" "$INSTALLER_URL"; then
        echo -e "${GREEN}✓ Download completed${NC}"
    else
        echo -e "${RED}Failed to download gcloud CLI${NC}"
        echo "Please install it manually from: https://cloud.google.com/sdk/docs/install"
        cd "$ORIGINAL_DIR"
        exit 1
    fi

    # Extract the archive
    echo ""
    echo "Extracting installer..."
    if tar -xzf "$INSTALLER_FILE"; then
        echo -e "${GREEN}✓ Extraction completed${NC}"
    else
        echo -e "${RED}Failed to extract installer${NC}"
        cd "$ORIGINAL_DIR"
        exit 1
    fi

    # Move to home directory
    echo ""
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}Warning: $INSTALL_DIR already exists${NC}"
        if [ "$AUTO_YES" = false ]; then
            read -p "Do you want to overwrite it? (y/N): " OVERWRITE_CONFIRM
            if [[ "$OVERWRITE_CONFIRM" =~ ^[Yy]$ ]]; then
                rm -rf "$INSTALL_DIR"
            else
                echo "Installation cancelled."
                cd "$ORIGINAL_DIR"
                exit 1
            fi
        else
            echo "Auto-overwriting existing installation..."
            rm -rf "$INSTALL_DIR"
        fi
    fi

    mv google-cloud-sdk "$HOME/"
    rm "$INSTALLER_FILE"

    echo -e "${GREEN}✓ gcloud CLI installed to $INSTALL_DIR${NC}"
    echo ""

    # Run the install script
    echo "Running gcloud installation script..."
    "$INSTALL_DIR/install.sh" --quiet --usage-reporting false --path-update false --command-completion false

    echo ""
    echo -e "${GREEN}✓ gcloud CLI installation completed${NC}"
    echo ""

    # Detect shell and set appropriate profile file
    SHELL_PROFILE=""
    PATH_INC=""
    COMPLETION_INC=""

    if [ -n "$ZSH_VERSION" ]; then
        SHELL_PROFILE="$HOME/.zshrc"
        PATH_INC="$INSTALL_DIR/path.zsh.inc"
        COMPLETION_INC="$INSTALL_DIR/completion.zsh.inc"
        SHELL_NAME="Zsh"
    elif [ -n "$BASH_VERSION" ]; then
        SHELL_PROFILE="$HOME/.bashrc"
        PATH_INC="$INSTALL_DIR/path.bash.inc"
        COMPLETION_INC="$INSTALL_DIR/completion.bash.inc"
        SHELL_NAME="Bash"
    else
        # Fallback: check $SHELL environment variable
        case "$SHELL" in
            */zsh)
                SHELL_PROFILE="$HOME/.zshrc"
                PATH_INC="$INSTALL_DIR/path.zsh.inc"
                COMPLETION_INC="$INSTALL_DIR/completion.zsh.inc"
                SHELL_NAME="Zsh"
                ;;
            */bash)
                SHELL_PROFILE="$HOME/.bashrc"
                PATH_INC="$INSTALL_DIR/path.bash.inc"
                COMPLETION_INC="$INSTALL_DIR/completion.bash.inc"
                SHELL_NAME="Bash"
                ;;
            *)
                SHELL_PROFILE="$HOME/.bashrc"
                PATH_INC="$INSTALL_DIR/path.bash.inc"
                COMPLETION_INC="$INSTALL_DIR/completion.bash.inc"
                SHELL_NAME="Bash (default)"
                ;;
        esac
    fi

    echo "Detected shell: $SHELL_NAME"
    echo "Profile file: $SHELL_PROFILE"
    echo ""

    # Check if profile update should be skipped
    if [ "$SKIP_PROFILE_UPDATE" = true ]; then
        echo "Skipping shell profile update (--skip-profile-update)"
        # Source for current session anyway
        if [ -f "$PATH_INC" ]; then
            source "$PATH_INC"
        fi
        if [ -f "$COMPLETION_INC" ]; then
            source "$COMPLETION_INC"
        fi
        echo -e "${GREEN}✓ gcloud CLI is available in your current session${NC}"
        echo ""
        return
    fi

    # Ask user if they want to update shell profile automatically
    PROFILE_UPDATE="n"
    if [ "$AUTO_YES" = false ]; then
        read -p "Would you like to automatically add gcloud CLI to your $SHELL_PROFILE? (Y/n): " PROFILE_UPDATE
    else
        PROFILE_UPDATE="y"
        echo "Auto-updating shell profile..."
    fi

    if [[ ! "$PROFILE_UPDATE" =~ ^[Nn]$ ]]; then
        # Create backup of profile file
        if [ -f "$SHELL_PROFILE" ]; then
            cp "$SHELL_PROFILE" "$SHELL_PROFILE.bak.$(date +%Y%m%d-%H%M%S)"
            echo -e "${GREEN}✓ Created backup of $SHELL_PROFILE${NC}"
        else
            touch "$SHELL_PROFILE"
            echo -e "${GREEN}✓ Created $SHELL_PROFILE${NC}"
        fi

        # Check if already added (to prevent duplicates)
        if grep -q "google-cloud-sdk/path" "$SHELL_PROFILE"; then
            echo -e "${YELLOW}Note: gcloud CLI PATH already exists in $SHELL_PROFILE${NC}"
        else
            # Add to shell profile
            echo "" >> "$SHELL_PROFILE"
            echo "# Added by Google Cloud Vertex AI Setup Script" >> "$SHELL_PROFILE"
            echo "if [ -f '$PATH_INC' ]; then source '$PATH_INC'; fi" >> "$SHELL_PROFILE"
            echo "if [ -f '$COMPLETION_INC' ]; then source '$COMPLETION_INC'; fi" >> "$SHELL_PROFILE"
            echo -e "${GREEN}✓ Added gcloud CLI to $SHELL_PROFILE${NC}"
        fi

        # Source the path for current session
        if [ -f "$PATH_INC" ]; then
            source "$PATH_INC"
        fi
        if [ -f "$COMPLETION_INC" ]; then
            source "$COMPLETION_INC"
        fi

        echo ""
        echo -e "${GREEN}✓ gcloud CLI is now available in your current session and future sessions${NC}"
        echo ""
    else
        # User declined automatic update
        echo ""
        echo -e "${YELLOW}To use gcloud in future terminal sessions, manually add this to your $SHELL_PROFILE:${NC}"
        echo ""
        echo "  if [ -f '$PATH_INC' ]; then source '$PATH_INC'; fi"
        echo "  if [ -f '$COMPLETION_INC' ]; then source '$COMPLETION_INC'; fi"
        echo ""

        # Source for current session anyway
        if [ -f "$PATH_INC" ]; then
            source "$PATH_INC"
            echo -e "${GREEN}✓ gcloud CLI is available in your current session${NC}"
        fi
        echo ""
    fi

    # Return to original directory
    cd "$ORIGINAL_DIR"
}

# Add gcloud to PATH if it exists but not in current PATH
GCLOUD_SDK_PATH="$HOME/google-cloud-sdk"
if [ -d "$GCLOUD_SDK_PATH/bin" ] && ! command -v gcloud &> /dev/null; then
    export PATH="$GCLOUD_SDK_PATH/bin:$PATH"
    echo -e "${GREEN}Added gcloud to PATH for this session${NC}"
    echo ""
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    if [ "$SKIP_GCLOUD_INSTALL" = true ]; then
        echo -e "${RED}Error: gcloud CLI is not installed and --skip-gcloud-install was specified${NC}"
        echo "Please install Google Cloud CLI from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    echo -e "${YELLOW}gcloud CLI is not installed.${NC}"
    install_gcloud_cli
fi

echo -e "${GREEN}✓ Google Cloud CLI is installed${NC}"
echo ""

# Get project ID
if [ -z "$PROJECT_ID" ]; then
    if [ "$AUTO_YES" = true ]; then
        echo -e "${RED}Error: Project ID is required in non-interactive mode${NC}"
        echo "Use: $0 -y PROJECT_ID or $0 -y --project PROJECT_ID"
        exit 1
    fi
    read -p "Enter your Google Cloud Project ID: " PROJECT_ID
fi

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: Project ID cannot be empty${NC}"
    exit 1
fi

echo ""
echo "Using Project ID: $PROJECT_ID"
echo ""

# Set the project
gcloud config set project "$PROJECT_ID"

echo ""

# Check gcloud user authentication (required for gcloud commands)
echo "Checking gcloud user authentication..."
ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null)

if [ -z "$ACTIVE_ACCOUNT" ]; then
    echo -e "${YELLOW}No active gcloud account found.${NC}"

    if [ "$SKIP_AUTH" = true ]; then
        echo -e "${RED}Error: gcloud authentication is required to enable APIs${NC}"
        echo "Please run: gcloud auth login"
        exit 1
    fi

    if [ "$AUTO_YES" = true ]; then
        echo -e "${RED}Error: gcloud authentication is required in non-interactive mode${NC}"
        echo ""
        echo "Please authenticate before running this script:"
        echo "  gcloud auth login"
        echo ""
        echo "Then run this script again:"
        echo "  $0 -y $PROJECT_ID"
        exit 1
    fi

    echo "Running: gcloud auth login"
    echo ""
    gcloud auth login

    # Verify authentication succeeded
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null)
    if [ -z "$ACTIVE_ACCOUNT" ]; then
        echo -e "${RED}Authentication failed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Authenticated as: $ACTIVE_ACCOUNT${NC}"
else
    echo -e "${GREEN}✓ Already authenticated as: $ACTIVE_ACCOUNT${NC}"
fi
echo ""

# Check if Vertex AI API is enabled
echo "Checking Vertex AI API status..."
if gcloud services list --enabled --filter="name:aiplatform.googleapis.com" --format="value(name)" | grep -q "aiplatform.googleapis.com"; then
    echo -e "${GREEN}✓ Vertex AI API is already enabled${NC}"
else
    echo -e "${YELLOW}Vertex AI API is not enabled. Enabling now...${NC}"
    gcloud services enable aiplatform.googleapis.com
    echo -e "${GREEN}✓ Vertex AI API has been enabled${NC}"
fi
echo ""

# Check Application Default Credentials (ADC) for Claude Code
if [ "$SKIP_AUTH" = true ]; then
    echo "Skipping Application Default Credentials setup (--skip-auth)"
    echo -e "${YELLOW}Warning: You may need to run 'gcloud auth application-default login' later${NC}"
    echo ""
else
    echo "Checking Application Default Credentials (for Claude Code)..."
    if gcloud auth application-default print-access-token &> /dev/null; then
        echo -e "${GREEN}✓ Application Default Credentials are already configured${NC}"
    else
        if [ "$AUTO_YES" = true ]; then
            echo -e "${YELLOW}Application Default Credentials not found.${NC}"
            echo -e "${YELLOW}Cannot run interactive authentication in non-interactive mode${NC}"
            echo ""
            echo "Please run manually:"
            echo "  gcloud auth application-default login"
            echo ""
        else
            echo -e "${YELLOW}Application Default Credentials not found.${NC}"
            echo "Running: gcloud auth application-default login"
            echo ""
            gcloud auth application-default login
            echo -e "${GREEN}✓ Application Default Credentials configured${NC}"
        fi
    fi
    echo ""
fi

# Set region (prefer asia-northeast1 for Tokyo)
REGION="asia-northeast1"
echo "Using region: $REGION (Tokyo)"
echo ""

# Create .env file
echo "Creating .env file..."
cat > .env << EOF
# Claude Code Vertex AI Configuration
# Required environment variables for Claude Code with Vertex AI

# Enable Vertex AI integration
CLAUDE_CODE_USE_VERTEX=1

# Google Cloud Project ID
ANTHROPIC_VERTEX_PROJECT_ID=$PROJECT_ID

# Cloud ML Region (use 'global' for automatic routing, or specific region)
CLOUD_ML_REGION=global

# Regional model override for asia-northeast1 (Tokyo)
VERTEX_REGION_CLAUDE_4_5_SONNET=$REGION

# Default model to use
ANTHROPIC_MODEL=claude-sonnet-4-5@20250929

# Optional: Disable prompt caching if needed
# DISABLE_PROMPT_CACHING=1
EOF
echo -e "${GREEN}✓ .env file created${NC}"
echo ""

# Create .claude directory if it doesn't exist
mkdir -p .claude

# Create .claude/settings.json with environment variables
echo "Creating .claude/settings.json..."
cat > .claude/settings.json << EOF
{
  "env": {
    "CLAUDE_CODE_USE_VERTEX": "1",
    "ANTHROPIC_VERTEX_PROJECT_ID": "$PROJECT_ID",
    "CLOUD_ML_REGION": "global",
    "VERTEX_REGION_CLAUDE_4_5_SONNET": "$REGION",
    "ANTHROPIC_MODEL": "claude-sonnet-4-5@20250929"
  }
}
EOF
echo -e "${GREEN}✓ .claude/settings.json created${NC}"
echo ""
echo "========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================="
echo ""
echo "Configuration:"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Model: Claude Sonnet 4.5"
echo ""
echo "Files created:"
echo "  - .env (environment variables reference)"
echo "  - .claude/settings.json (Claude Code configuration)"
echo ""
echo "You can now use Claude Code with Google Cloud Vertex AI!"
echo ""
echo "To start using Claude Code:"
echo "  claude"
echo ""
echo "Notes:"
echo "  - Settings are automatically loaded from .claude/settings.json"
echo "  - These files can be committed to Git (no sensitive credentials)"
echo "  - Authentication is handled separately via Google Cloud ADC"
echo ""
