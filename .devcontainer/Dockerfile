# Declarative platform and base image
FROM ubuntu:25.10

# Build arguments for user configuration
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Enforce Mise strictness
ENV MISE_STRICT=1

# Use shell with pipefail for better error handling
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Bare minimum system dependencies
# Everything else comes from Mise/Pixi/UV
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    sudo \
    zsh \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libatomic1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create the user using variables, handling potential UID/GID conflicts
RUN export USER_UID=${USER_UID:-1000} \
    && export USER_GID=${USER_GID:-$USER_UID} \
    && if id -u $USERNAME >/dev/null 2>&1; then userdel -r $USERNAME || true; fi \
    && if getent group $USERNAME >/dev/null 2>&1; then groupdel $USERNAME || true; fi \
    && if id -u 1000 >/dev/null 2>&1; then userdel -r $(id -nu 1000) || true; fi \
    && if getent group 1000 >/dev/null 2>&1; then groupdel $(getent group 1000 | cut -d: -f1) || true; fi \
    && if id -u $USER_UID >/dev/null 2>&1; then userdel -r $(id -nu $USER_UID) || true; fi \
    && if getent group $USER_GID >/dev/null 2>&1; then groupdel $(getent group $USER_GID | cut -d: -f1) || true; fi \
    && groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m -s /bin/bash $USERNAME \
    && mkdir -p /home/$USERNAME/.ssh && chmod 700 /home/$USERNAME/.ssh \
    && chown $USERNAME:$USERNAME /home/$USERNAME/.ssh \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER $USERNAME
ENV USER=$USERNAME
WORKDIR /home/$USERNAME

# Copy the dotfiles repository
COPY --chown=$USERNAME:$USERNAME . /home/$USERNAME/.local/share/chezmoi

# Declarative PATH enforcement
ENV PATH="/home/$USERNAME/.local/bin:/home/$USERNAME/.local/share/mise/shims:/home/$USERNAME/.cargo/bin:${PATH}"

WORKDIR /home/$USERNAME
