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

# Install AWS CDK tools
echo "[devcontainer] Setting up AWS CDK tools..."

# Verify AWS CLI installation (installed via devcontainer feature)
if command -v aws >/dev/null 2>&1; then
  echo "[devcontainer] AWS CLI installed: $(aws --version)"
else
  echo "[devcontainer][error] AWS CLI not found. Check devcontainer features configuration."
fi

# Install AWS CDK CLI globally
if ! command -v cdk >/dev/null 2>&1; then
  echo "[devcontainer] Installing AWS CDK CLI..."
  npm install -g aws-cdk@latest
  echo "[devcontainer] AWS CDK CLI installed: $(cdk --version)"
else
  echo "[devcontainer] AWS CDK CLI already installed: $(cdk --version)"
fi

echo "[devcontainer] AWS CDK tools setup complete!"
echo "[devcontainer] All deployment tools installed successfully!"
