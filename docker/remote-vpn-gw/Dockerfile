FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    strongswan \
    strongswan-swanctl \
    libcharon-extra-plugins \
    iptables \
    nftables \
    iproute2 \
    iputils-ping \
    net-tools \
    tcpdump \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY entrypoint.sh /root/entrypoint.sh
RUN chmod +x /root/entrypoint.sh

ENTRYPOINT ["/root/entrypoint.sh"]
