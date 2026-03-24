# Declarative platform and base image
ARG OS=ubuntu
ARG OS_VERSION=25.10
FROM --platform=linux/amd64 ${OS}:${OS_VERSION}

# Build arguments for user configuration
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

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
RUN if id -u $USERNAME >/dev/null 2>&1; then userdel -r $USERNAME || true; fi \
    && if id -u $USER_UID >/dev/null 2>&1; then \
        CONFLICTING_USER=$(id -nu $USER_UID); \
        if [ "$CONFLICTING_USER" != "$USERNAME" ]; then userdel -r $CONFLICTING_USER || true; fi; \
    fi \
    && if getent group $USERNAME >/dev/null 2>&1; then groupdel $USERNAME || true; fi \
    && if getent group $USER_GID >/dev/null 2>&1; then \
        CONFLICTING_GROUP=$(getent group $USER_GID | cut -d: -f1); \
        if [ "$CONFLICTING_GROUP" != "$USERNAME" ]; then groupdel $CONFLICTING_GROUP || true; fi; \
    fi \
    && groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m -s /bin/bash $USERNAME \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER $USERNAME
ENV USER=$USERNAME
WORKDIR /home/$USERNAME

# Copy the dotfiles repository
COPY --chown=$USERNAME:$USERNAME . /home/$USERNAME/.local/share/chezmoi

# Bootstrap Mise and hand off to Chezmoi
# The install.sh script is kept to the absolute minimum
RUN cd /home/$USERNAME/.local/share/chezmoi && bash install.sh --local

# Explicitly ensure all Mise tools are installed and shims are active
RUN /home/$USERNAME/.local/bin/mise install --yes

# Declarative PATH enforcement
ENV PATH="/home/$USERNAME/.local/bin:/home/$USERNAME/.local/share/mise/shims:/home/$USERNAME/.cargo/bin:${PATH}"

WORKDIR /home/$USERNAME
