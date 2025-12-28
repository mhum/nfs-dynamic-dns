FROM python:3.8-alpine

# Install dependencies
RUN pip install --upgrade pip
RUN pip3 install requests python-dotenv
RUN apk add --no-cache curl socat bash

# Copy scripts and docs
COPY *.py /root/
COPY entrypoint.sh /root/entrypoint.sh
COPY LICENSE /root/LICENSE
COPY README.md /root/README.md

RUN chmod +x /root/entrypoint.sh

# Install acme.sh
RUN curl https://get.acme.sh | sh

# Install NFSN DNS plugin for acme.sh
COPY dns_nfsn.sh /root/.acme.sh/dnsapi/dns_nfsn.sh
RUN chmod +x /root/.acme.sh/dnsapi/dns_nfsn.sh

# Directories for logs and certs
RUN mkdir -p /logs /certs

WORKDIR /root

# Set cron schedules (with backwards compatibility)
ARG CRON_SCHEDULE="*/30 * * * *"
ARG DDNS_CRON="${CRON_SCHEDULE}"
ARG CERT_CRON="0 3 * * *"

# Convert to ENV for runtime use in entrypoint.sh
ENV DDNS_CRON="${DDNS_CRON}"
ENV CERT_CRON="${CERT_CRON}"

ENTRYPOINT ["/root/entrypoint.sh"]
