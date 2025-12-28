#!/bin/bash
set -e

# Load environment variables from .env
if [ -f /root/.env ]; then
  export $(grep -v '^#' /root/.env | xargs)
fi

# Set defaults (backwards compatibility)
ENABLE_DDNS="${ENABLE_DDNS:-true}"
ENABLE_CERTS="${ENABLE_CERTS:-false}"
DDNS_CRON="${DDNS_CRON:-*/30 * * * *}"
CERT_CRON="${CERT_CRON:-0 3 * * *}"

CERT_HOME="/root/.acme.sh"
CERT_PATH="/certs"

# Clear existing crontab
crontab -r 2>/dev/null || true

# Conditional DDNS cron setup
if [ "$ENABLE_DDNS" = "true" ]; then
  echo "[INIT] Setting up DDNS cron: $DDNS_CRON"
  (crontab -l 2>/dev/null; echo "$DDNS_CRON python3 /root/nfsn-ddns.py >> /logs/ddns.log 2>&1") | crontab -
else
  echo "[INIT] DDNS disabled"
fi

# Conditional ACME setup
if [ "$ENABLE_CERTS" = "true" ]; then
  echo "[INIT] Certificate management enabled"
  mkdir -p "$CERT_PATH"

  # Issue initial certificate if needed
  DOMAIN_CERT_FILE="$CERT_PATH/$DOMAIN.crt"
  DOMAIN_KEY_FILE="$CERT_PATH/$DOMAIN.key"

  if [ ! -f "$DOMAIN_CERT_FILE" ] || [ ! -f "$DOMAIN_KEY_FILE" ]; then
    echo "[INIT] Issuing certificate for $DOMAIN"
    $CERT_HOME/acme.sh --issue \
      -d "$DOMAIN" -d "*.$DOMAIN" \
      --dns dns_nfsn \
      --cert-file "$DOMAIN_CERT_FILE" \
      --key-file "$DOMAIN_KEY_FILE" \
      --home "$CERT_HOME" || echo "[ERROR] Cert issuing failed, will retry via cron"
  else
    echo "[INIT] Certificate exists for $DOMAIN"
  fi

  # Add renewal cron
  echo "[INIT] Setting up ACME renewal cron: $CERT_CRON"
  (crontab -l 2>/dev/null; echo "$CERT_CRON $CERT_HOME/acme.sh --renew --home $CERT_HOME --cron >> /logs/acme.log 2>&1") | crontab -
else
  echo "[INIT] Certificate management disabled"
fi

# Show final crontab for debugging
echo "[INIT] Final crontab:"
crontab -l || echo "  (empty)"

# Start cron in foreground
exec crond -f -d 8
