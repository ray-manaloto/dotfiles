# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE=ubuntu:24.04
ARG MISE_VERSION=v2025.2.27

FROM ${BASE_IMAGE} AS devcontainer

ARG DEBIAN_FRONTEND=noninteractive
ARG MISE_VERSION

# Global mise environment
ENV DEBIAN_FRONTEND=${DEBIAN_FRONTEND} \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    MISE_DATA_DIR=/opt/mise \
    MISE_CONFIG_DIR=/etc/mise \
    MISE_INSTALL_PATH=/usr/local/bin/mise \
    MISE_TRUSTED_CONFIG_PATHS=/etc/mise:/workspaces/dotfiles \
    MISE_ARCH=x64 \
    MISE_OS=linux \
    CONDA_SUBDIR=linux-64 \
    MISE_HTTP_TIMEOUT=120 \
    npm_config_update_notifier=false \
    RUSTUP_INIT_SKIP_PATH_CHECK=yes \
    CARGO_HOME=/opt/cargo \
    RUSTUP_HOME=/opt/rustup \
    PATH="/usr/local/bin:/opt/mise/shims:/opt/cargo/bin:${PATH}"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    sed -i '/^path-exclude=\/usr\/share\/man\/\*$/d' /etc/dpkg/dpkg.cfg.d/excludes && \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    gnupg \
    graphviz \
    pkg-config \
    unzip \
    zsh \
    libatomic1 \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl-dev \
    zlib1g-dev \
    sudo \
    openssh-server \
    && rm -rf /var/lib/apt/lists/* /tmp/*

# Install mise globally
RUN curl -fsSL https://mise.jdx.dev/mise-latest-linux-x64 > /usr/local/bin/mise && \
    chmod +x /usr/local/bin/mise

# System-wide mise config and data structure
RUN groupadd --gid 2000 mise && \
    mkdir -p /etc/mise /opt/mise /opt/cargo /opt/rustup && \
    chown -R :mise /opt/mise /opt/cargo /opt/rustup && \
    chmod -R 775 /opt/mise /opt/cargo /opt/rustup

COPY . /tmp/dotfiles/

# Pre-install tools globally via mise tasks
# We strip chezmoi tags from the template to allow mise to parse it during build
RUN --mount=type=cache,id=mise-cache,target=/opt/mise/cache,sharing=locked \
    --mount=type=cache,id=uv-cache,target=/root/.cache/uv,sharing=locked \
    --mount=type=secret,id=github_token \
    export MISE_VERSION="${MISE_VERSION}" && \
    export MISE_INSTALL_MODE=system && \
    export UV_LINK_MODE=copy && \
    if [ -f /run/secrets/github_token ]; then \
      export GITHUB_TOKEN="$(cat /run/secrets/github_token)"; \
      export MISE_GITHUB_TOKEN="$GITHUB_TOKEN"; \
    fi && \
    mkdir -p /etc/mise && \
    sed '/{{/d' /tmp/dotfiles/home/dot_config/mise/config.toml.tmpl > /etc/mise/config.toml && \
    mise install -y && \
    chmod -R 777 /opt/mise /etc/mise /opt/cargo /opt/rustup

# Final global permissions check
RUN chmod -R 777 /opt/mise /etc/mise /opt/cargo /opt/rustup

# Ensure mise is activated for all users
RUN echo 'eval "$(/usr/local/bin/mise activate bash)"' > /etc/profile.d/mise.sh && \
    echo 'eval "$(/usr/local/bin/mise activate zsh)"' > /etc/profile.d/mise.zsh

WORKDIR /workspaces
