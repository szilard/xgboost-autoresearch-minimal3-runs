# syntax=docker/dockerfile:1
# Ubuntu 26.04 + codex (as the unprivileged user `ubuntu`, nothing AI as root)
# + a copy of szilard/xgboost-autoresearch-minimal3 with fresh git history,
# without the human-only files (kept root-only in /opt/human-only)
# Build, login and run: see README.md in this folder.
FROM ubuntu:26.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates git ripgrep python3 python3-pip nodejs npm procps \
    && rm -rf /var/lib/apt/lists/*

# ubuntu:26.04 ships a uid-1000 `ubuntu` user; sudo is not installed, and the
# user is also taken out of the admin groups the base image puts it in
RUN for g in sudo admin adm wheel staff; do gpasswd -d ubuntu "$g" 2>/dev/null || true; done
USER ubuntu
WORKDIR /home/ubuntu
ENV PATH=/home/ubuntu/.npm-global/bin:/home/ubuntu/.local/bin:$PATH

# codex starts fresh: `codex --version` leaves ~/.codex/tmp behind, so reset it.
# ~/.codex/auth.json is a symlink into ~/.codex-auth, where the codex-auth
# volume is mounted; codex rewrites auth.json in place, so token refreshes
# land in the volume. A fresh volume takes the owner and mode
# (ubuntu, 700) of ~/.codex-auth from the image.
RUN npm install -g --prefix /home/ubuntu/.npm-global @openai/codex && codex --version \
    && rm -rf /home/ubuntu/.codex && mkdir /home/ubuntu/.codex \
    && mkdir -m 700 /home/ubuntu/.codex-auth \
    && ln -s /home/ubuntu/.codex-auth/auth.json /home/ubuntu/.codex/auth.json

# Python packages from minimal3's quick start (--user: the image is PEP 668)
RUN pip install --break-system-packages --user --no-cache-dir \
        pandas xgboost scikit-learn cloudpickle matplotlib

# identity for the initial commit below and for the agent's experiment commits
RUN git config --global user.name agent && git config --global user.email agent@localhost

# The upstream commit all runs use. A full hash, so that a rebuild cannot
# silently pick up a newer upstream; change it here (or with
# --build-arg MINIMAL3_REF=...) to move to another commit.
ARG MINIMAL3_REF=15ce0aa5a15d7c51968d02f0677808cbef454bce

# Clone at that commit and build data/train.csv, eval.csv and holdout.csv from
# the S3 source (data/ is gitignored)
RUN git clone -q https://github.com/szilard/xgboost-autoresearch-minimal3.git \
    && cd xgboost-autoresearch-minimal3 \
    && git checkout -q "$MINIMAL3_REF" \
    && python3 human/make_data.py && ls -l data/

# The human-only files go where the agent cannot read them (root-only; the
# agent runs as `ubuntu`, without sudo): the human/ scripts and the holdout
# set. The driver copies them back after the agent has exited, for the
# holdout scoring.
USER root
RUN install -d -m 700 /opt/human-only \
    && mv /home/ubuntu/xgboost-autoresearch-minimal3/human /opt/human-only/human \
    && mv /home/ubuntu/xgboost-autoresearch-minimal3/data/holdout.csv /opt/human-only/holdout.csv \
    && chown -R root:root /opt/human-only
USER ubuntu

# Drop upstream history and results/ so the agent cannot see earlier runs,
# then start a new repo (the agent's workflow needs git) without human/. The
# upstream commit is kept in the commit message.
RUN cd xgboost-autoresearch-minimal3 \
    && upstream=$(git rev-parse HEAD) \
    && rm -rf .git results \
    && git init -q -b main \
    && git add -A \
    && git commit -q -m "xgboost-autoresearch-minimal3 @ $upstream" \
    && git status --short && ls -la . data/

CMD ["/bin/bash"]
