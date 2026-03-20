# Slack MCP Server (Python + FastMCP)

FROM python:3.12-slim

WORKDIR /app

# Install Blizzard corporate CA certificates
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl -o /usr/local/share/ca-certificates/ABKRoot.crt \
        https://abkpki.battle.net/pki/ABKRoot.cer \
    && curl -o /usr/local/share/ca-certificates/ActivisionIssuing.crt \
        https://abkpki.battle.net/pki/ActivisionIssuing.cer \
    && curl -o /usr/local/share/ca-certificates/BlizzardIssuing.crt \
        https://abkpki.battle.net/pki/BlizzardIssuing.cer \
    && curl -o /usr/local/share/ca-certificates/KingIssuing.crt \
        https://abkpki.battle.net/pki/KingIssuing.cer \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

EXPOSE 5000

CMD ["python3", "server.py"]
