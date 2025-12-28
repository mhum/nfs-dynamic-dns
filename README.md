# NearlyFreeSpeech.NET Dynamic DNS
This script will update the `A` DNS record (and optionally, the `AAAA` records) for a domain/subdomain at [NearlyFreeSpeech.NET](https://www.nearlyfreespeech.net)
with the public IP address for the machine the script runs on. Run this script on a server in which the public IP
address is dynamic and changes so your domain is always up to date.

## How It Works
There are two steps to this script. First, it retrieves the configured IP address for the domain/subdomain, the current public
IP address of the server, and then compares the two. If the public IP address is different, it updates the `A` (and, if configured, the `AAAA`) record(s) of
the domain/subdomain with the new IP address.

## Requirements
- `python-dotenv`
- `requests`

Both can be downloaded from pip using `pip install -r requirements.txt`

## Configuring
Configurations are set by providing the script with environment variables or command line arguments.

### Configs
| Env Variable | Command Line Argument | Required | Description |
| --- | --- | --- | --- |
| USERNAME | | Y | Your NFSN username |
| API_KEY | | Y | API key for using NFSN's APIs. This can be obtained via the Member Interface > "Profile" tab > "Actions" > "Manage API Key" |
| DOMAIN | | Y | Domain that the subdomain belongs to |
| SUBDOMAIN | | N | Subdomain to update with the script. Leave blank for the bare domain name |
| ENABLE_DDNS | | N | Enable dynamic DNS updates. Defaults to `true` for backwards compatibility. Set to `false` to disable DDNS and run only certificate management. |
| ENABLE_CERTS | | N | Enable Let's Encrypt certificate issuing and renewal via ACME DNS-01 challenge. Defaults to `false`. Set to `true` to enable certificate management. |
| DDNS_CRON | | N | Cron schedule for DDNS updates. Defaults to `*/30 * * * *` (every 30 minutes). Only used if `ENABLE_DDNS=true`. Can also be set at build time via `--build-arg`. |
| CERT_CRON | | N | Cron schedule for certificate renewal checks. Defaults to `0 3 * * *` (daily at 3 AM). Only used if `ENABLE_CERTS=true`. Can also be set at build time via `--build-arg`. |
| IP_PROVIDER | | N | Use a different IP providing service than the default: [http://ipinfo.io/ip](http://ipinfo.io/ip) This might be useful if the default provider is unavailable or is blocked. The alternate provider MUST be served over `http` (please open an issue if this is ever a problem) and MUST return ONLY the IP in the response body |
| IPV6_PROVIDER | | N | Use a different IP providing service than the default: [http://v6.ipinfo.io/ip](http://v6.ipinfo.io/ip) This might be useful if the default provider is unavailable or is blocked. The alternate provider MUST be served over `http` (please open an issue if this is ever a problem) and MUST return ONLY the IP in the response body |
| ENABLE_IPV6 | `--ipv6` or `-6` | N | Set this to any value to also cause the script to check for and update AAAA records on the specified domain. |
| IP_USE_DIG | `--useDig` or `-d` | N | Use the system's *dig* command and Google's DNS server to determine the IP address instead of an IP providing service over HTTP |

## Running
### Manually
It is as easy as running: `python3 ./nfsn-ddns.py` (after installing the dependencies listed above)

To include all of the environmental variables inline when running, you can do something like this:
```bash
$ export USERNAME=username API_KEY=api_key DOMAIN=domain.com SUBDOMAIN=subdomain && python3 ./nfsn-ddns.py
```

or with optional command line arguments like this:
```bash
$ export USERNAME=username API_KEY=api_key DOMAIN=domain.com SUBDOMAIN=subdomain && python3 ./nfsn-ddns.py --useDig
```

or you can put your variables in a `.env` file:

```
# NFSN credentials
USERNAME=your_username
API_KEY=your_api_key
DOMAIN=example.com
SUBDOMAIN=subdomain

# Feature flags
ENABLE_DDNS=true        # Enable dynamic DNS (default: true)
ENABLE_CERTS=false      # Enable Let's Encrypt certs (default: false)

# Optional: Customize schedules
#DDNS_CRON=*/30 * * * *  # Every 30 minutes (default)
#CERT_CRON=0 3 * * *     # Daily at 3 AM (default)

# Optional: IPv6 support
#ENABLE_IPV6=true

# Optional: Customize IP providers
#IP_PROVIDER=http://ipinfo.io/ip
#IPV6_PROVIDER=http://v6.ipinfo.io/ip
```

### With Docker
1. Set the configuration values in the script the way you want them (or create a file containing the environment variables)
2. Build the image with `docker build -t nfs-dynamic-dns .`
3. Run the image (production) with `docker run -d --name nfsn-dynamic-dns nfs-dynamic-dns` (add the `--env-file <file>` argument before the last `nfsn-dynamic-dns` if you want to use your environment variable file)

	Ex: `docker run -d --name nfsn-dynamic-dns --env-file .env nfs-dynamic-dns`

### With Docker Compose
You can use the following config to run this with [docker compose](https://docs.docker.com/compose/).
```yaml
services:
  nfs-dynamic-dns:
    image: ghcr.io/mhum/nfs-dynamic-dns:latest
    container_name: nfs-dynamic-dns
    network_mode: host
    environment:
     - USERNAME=username
     - API_KEY=api_key
     - DOMAIN=domain.com
     - SUBDOMAIN=subdomain
    restart: unless-stopped
 ```

#### Development
To run the container locally (and let it run its cronjobs), use this command:
`docker run -it --rm --init nfs-dynamic-dns`

to run the container locally and be put into a shell where you can run `python3 ./nfsn-ddns.py` yourself use this:
`docker run -it --rm --init nfs-dynamic-dns sh`

If your setup uses environment variables, you will also need to add the `--env-file` argument (or specify variables individually with [the `-e` docker flag](https://docs.docker.com/engine/reference/run/#env-environment-variables)). The `--env-file` option is for [docker run](https://docs.docker.com/engine/reference/commandline/run/) and the env file format can be found [here](https://docs.docker.com/compose/env-file/).

### Docker
When using the Docker file, DDNS updates are scheduled to run every 30 minutes by default. This is configurable when building the
container using [build args](https://docs.docker.com/engine/reference/builder/#arg).

#### Customizing Cron Schedules

You can customize the schedules using build args:

**With docker:**
```bash
# For DDNS updates (backwards compatible)
$ docker build --build-arg CRON_SCHEDULE="*/5 * * * *" -t nfs-dynamic-dns .

# Or use the new arg names
$ docker build --build-arg DDNS_CRON="*/5 * * * *" --build-arg CERT_CRON="0 2 * * *" -t nfs-dynamic-dns .
```

**With docker compose:**
```yaml
services:
  nfs-dynamic-dns:
    image: nfs-dynamic-dns
    build:
      context: ./nfs-dynamic-dns
      args:
        - DDNS_CRON=*/5 * * * *
        - CERT_CRON=0 2 * * *
    container_name: nfs-dynamic-dns
...
 ```

**Note:** The `CRON_SCHEDULE` build arg is still supported for backwards compatibility and maps to `DDNS_CRON`.

## ACME Certificate Management

This application can automatically issue and renew Let's Encrypt certificates using DNS-01 challenges via the NFSN DNS API.

### Requirements for Certificate Management
- Set `ENABLE_CERTS=true` environment variable
- Ensure `DOMAIN` environment variable is set (certificates will be issued for `$DOMAIN` and `*.$DOMAIN`)
- Mount a volume to `/certs` to persist certificates outside the container

### Certificate Paths
Certificates are stored in `/certs`:
- Certificate: `/certs/$DOMAIN.crt`
- Private key: `/certs/$DOMAIN.key`

### Docker Example with Certificates
```bash
docker run -d \
  --name nfsn-dynamic-dns \
  --env-file .env \
  -v /path/to/certs:/certs \
  nfs-dynamic-dns
```

Make sure your `.env` file includes:
```
ENABLE_CERTS=true
```

### Docker Compose Example with Certificates
```yaml
version: "3"

services:
  nfs-dynamic-dns:
    image: nfs-dynamic-dns
    build: ./nfs-dynamic-dns
    container_name: nfs-dynamic-dns
    network_mode: host
    environment:
      - USERNAME=username
      - API_KEY=api_key
      - DOMAIN=domain.com
      - SUBDOMAIN=subdomain
      - ENABLE_DDNS=true
      - ENABLE_CERTS=true
    volumes:
      - ./certs:/certs
      - ./logs:/logs
    restart: unless-stopped
```

### Running Only Certificate Management (No DDNS)
To run only certificate issuing/renewal without DDNS:
```bash
docker run -d \
  --name nfsn-certs \
  -e USERNAME=username \
  -e API_KEY=api_key \
  -e DOMAIN=domain.com \
  -e ENABLE_DDNS=false \
  -e ENABLE_CERTS=true \
  -v /path/to/certs:/certs \
  nfs-dynamic-dns
```

### Manual Certificate Operations
To manually issue a certificate inside the container:
```bash
docker exec nfsn-dynamic-dns /root/.acme.sh/acme.sh --issue \
  -d domain.com -d "*.domain.com" \
  --dns dns_nfsn \
  --cert-file /certs/domain.com.crt \
  --key-file /certs/domain.com.key \
  --home /root/.acme.sh
```

To force renewal:
```bash
docker exec nfsn-dynamic-dns /root/.acme.sh/acme.sh --renew \
  -d domain.com \
  --force \
  --home /root/.acme.sh
```

### Customizing Certificate Renewal Schedule
Both DDNS and certificate renewal schedules can be customized via environment variables:

```yaml
environment:
  - DDNS_CRON=*/15 * * * *      # Check DDNS every 15 minutes
  - CERT_CRON=0 2 * * *         # Check renewal daily at 2 AM
```

## Troubleshooting
The script communicates with NearlyFreeSpeech.NET via its RESTful API. Specifics about the API can be found [here](https://members.nearlyfreespeech.net/wiki/API/Introduction).
