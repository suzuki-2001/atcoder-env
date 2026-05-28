FROM ubuntu:24.04

ARG UID=1000
ARG GID=1000
ARG DEBIAN_FRONTEND=noninteractive
# Languages to install. cpp/python are always available; c is covered by
# build-essential. Add go/rust by passing e.g. LANGUAGES=cpp,python,go,rust.
ARG LANGUAGES=cpp,python

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        g++ \
        gdb \
        valgrind \
        python3 \
        python3-pip \
        python3-venv \
        curl \
        ca-certificates \
        git \
        patch \
        locales \
        sudo \
    && rm -rf /var/lib/apt/lists/*

RUN locale-gen en_US.UTF-8 ja_JP.UTF-8
ENV LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/atcoder/ac-library.git /opt/ac-library
ENV CPLUS_INCLUDE_PATH=/opt/ac-library

RUN if echo ",$LANGUAGES," | grep -q ',go,'; then \
        apt-get update && apt-get install -y --no-install-recommends golang-go \
        && rm -rf /var/lib/apt/lists/*; \
    fi

ENV RUSTUP_HOME=/opt/rust \
    CARGO_HOME=/opt/rust \
    PATH=/opt/rust/bin:$PATH
RUN if echo ",$LANGUAGES," | grep -q ',rust,'; then \
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
          | sh -s -- -y --default-toolchain stable --profile minimal --no-modify-path \
        && chmod -R a+rX /opt/rust; \
    fi

RUN npm install -g atcoder-cli

RUN pip install --break-system-packages --no-cache-dir \
        online-judge-tools \
        aclogin

COPY scripts/apply-mib-patch.py /tmp/apply-mib-patch.py
RUN python3 /tmp/apply-mib-patch.py && rm /tmp/apply-mib-patch.py

RUN userdel -r ubuntu 2>/dev/null || true \
    && groupdel ubuntu 2>/dev/null || true \
    && if getent group ${GID} >/dev/null; then \
           groupmod -n atcoder $(getent group ${GID} | cut -d: -f1); \
       else \
           groupadd -g ${GID} atcoder; \
       fi \
    && useradd -m -s /bin/bash -u ${UID} -g ${GID} atcoder \
    && echo "atcoder ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers \
    && mkdir -p /home/atcoder/.config/atcoder-cli-nodejs \
                /home/atcoder/.local/share/online-judge-tools \
    && chown -R atcoder:atcoder /home/atcoder

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /work
USER atcoder

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]
