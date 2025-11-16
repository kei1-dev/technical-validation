# syntax=docker/dockerfile:1
ARG VARIANT='3.12-bookworm'
FROM mcr.microsoft.com/devcontainers/python:${VARIANT}

ENV PIPENV_VENV_IN_PROJECT=1 \
    PIPENV_NOSPIN=1 \
    PIPENV_SKIP_LOCK=1

# Install pipenv and supporting tooling
RUN python3 -m pip install --no-cache-dir pipenv \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        bash-completion \
        less \
        jq \
        curl \
        wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pre-create workspace directory for consistency with devcontainer.json
RUN mkdir -p /workspaces
WORKDIR /workspaces

# Set up Claude Code and Codex CLI aliases with skip permissions for vscode user
RUN echo '\n# Claude Code and Codex CLI aliases with skip permissions' >> /home/vscode/.bashrc \
    && echo "alias claude='claude --dangerously-skip-permissions'" >> /home/vscode/.bashrc \
    && echo "alias claude-normal='command claude'" >> /home/vscode/.bashrc \
    && echo "alias codex='codex --dangerously-bypass-approvals-and-sandbox'" >> /home/vscode/.bashrc \
    && echo '\n# Claude Code and Codex CLI aliases with skip permissions' >> /home/vscode/.zshrc \
    && echo "alias claude='claude --dangerously-skip-permissions'" >> /home/vscode/.zshrc \
    && echo "alias claude-normal='command claude'" >> /home/vscode/.zshrc \
    && echo "alias codex='codex --dangerously-bypass-approvals-and-sandbox'" >> /home/vscode/.zshrc \
    && chown vscode:vscode /home/vscode/.bashrc /home/vscode/.zshrc
