#!/usr/bin/env bash
set -euo pipefail

# Ensure pipenv is available even if base image changes
if ! command -v pipenv >/dev/null 2>&1; then
  echo "[devcontainer] Installing pipenv..."
  python3 -m pip install --no-cache-dir pipenv
fi

if [[ -x scripts/install-tools.sh ]]; then
  echo "[devcontainer] Installing AI agent tooling (Codex CLI / Claude Code)..."
  bash scripts/install-tools.sh || echo "[devcontainer][warn] AI agent tooling install exited with a non-zero status."
else
  echo "[devcontainer][warn] scripts/install-tools.sh not found or not executable; skipping AI agent tooling install."
fi

# Install Azure deployment tools
echo "[devcontainer] Setting up Azure deployment tools..."

# Verify Azure CLI installation (installed via devcontainer feature)
if command -v az >/dev/null 2>&1; then
  echo "[devcontainer] Azure CLI installed: $(az version --output tsv | grep azure-cli | awk '{print $2}')"
else
  echo "[devcontainer][error] Azure CLI not found. Check devcontainer features configuration."
fi

# Install Bicep CLI (should be included with Azure CLI, but verify)
if ! az bicep version >/dev/null 2>&1; then
  echo "[devcontainer] Installing Bicep CLI..."
  az bicep install
  echo "[devcontainer] Bicep CLI installed: $(az bicep version)"
else
  echo "[devcontainer] Bicep CLI already installed: $(az bicep version)"
fi

# Upgrade Bicep to latest version
echo "[devcontainer] Upgrading Bicep CLI to latest version..."
az bicep upgrade || echo "[devcontainer][warn] Bicep upgrade failed or not needed"

echo "[devcontainer] Azure deployment tools setup complete!"
echo "[devcontainer] All deployment tools installed successfully!"
