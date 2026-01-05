FROM debian:trixie

RUN apt-get update -y && \
    apt-get install -y \
      build-essential \
      cmake \
      pkg-config \
      squashfs-tools \
      git-core \
      bc \
      flex \
      bison \
      libssl-dev \
      dos2unix \
      sudo \
      unzip \
      wget \
      g++-aarch64-linux-gnu \
      gcc-aarch64-linux-gnu \
      file \
      golang-go \
    && git config --global --add safe.directory '*' \
    && rm -rf /var/lib/apt/lists/*

RUN dpkg --add-architecture arm64 && \
    apt-get update -y && \
    apt-get install -y \
      libssl-dev:arm64 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
