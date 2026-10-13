FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    iputils-ping \
    net-tools \
    tcpdump \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pydicom pynetdicom

WORKDIR /app

COPY router.py /app/router.py

RUN useradd --create-home --uid 10001 dicom-router && chown -R dicom-router:dicom-router /app
USER dicom-router

CMD ["python3", "/app/router.py"]
