FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    iputils-ping \
    net-tools \
    netcat-openbsd \
    tcpdump \
    curl \
    dcmtk \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pydicom pynetdicom requests numpy

WORKDIR /app

COPY run_modality.sh /app/run_modality.sh
RUN chmod +x /app/run_modality.sh

ENTRYPOINT ["/app/run_modality.sh"]
