FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    orthanc \
    orthanc-dicomweb \
    iproute2 \
    iputils-ping \
    net-tools \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/lib/orthanc/db /etc/orthanc

EXPOSE 4242 8042

COPY orthanc.json /etc/orthanc/orthanc.json

CMD ["Orthanc", "/etc/orthanc/orthanc.json"]
