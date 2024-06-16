# NearlyFreeSpeech.NET Dynamic DNS
This script will update the `A` DNS record for a domain/subdomain at [NearlyFreeSpeech.NET](https://www.nearlyfreespeech.net)
with the public IP address for the machine the script runs on. Run this script on a server in which the public IP
address is dynamic and changes so your domain is always up to date.

## How It Works
There are two steps to this script. First, it retrieves the configured IP address for the domain/subdomain, the current public
IP address of the server, and then compares the two. If the public IP address is different, it updates the `A` record of
the domain/subdomain with the new IP address.

## Requirements
- `python-dotenv`
- `requests`

Both can be downloaded from pip using `pip install -r requirements.txt`

## Configuring
Configurations are set by providing the script with environment variables

### Configs
| Env Variable | Required | Description |
| --- | --- | --- |
| USERNAME | Y | Your NFSN username |
| API_KEY | Y | API key for using NFSN's APIs. This can be obtained via the Member Interface > "Profile" tab > "Actions" > "Manage API Key" |
| DOMAIN | Y | Domain that the subdomain belongs to |
| SUBDOMAIN | N | Subdomain to update with the script. Leave blank for the bare domain name |
| IP_PROVIDER | N | Use a different IP providing service than the default: [http://ipinfo.io/ip](http://ipinfo.io/ip) This might be useful if the default provider is unavailable or is blocked. The alternate provider MUST be served over `http` (please open an issue if this is ever a problem) and MUST return ONLY the IP in the response body |

## Running
### Manually
It is as easy as running: `python3 ./nfsn-ddns.py` (after installing the dependencies listed above)

To include all of the environmental variables inline when running, you can do something like this:
```bash
$ export USERNAME=username API_KEY=api_key DOMAIN=domain.com SUBDOMAIN=subdomain && python3 ./nfsn-ddns.py 
```

or you can put your variables in a `.env` file:

```
API_KEY=
USERNAME=
DOMAIN=
SUBDOMAIN=
```

### With Docker
1. Set the configuration values in the script the way you want them (or create a file containing the environment variables)
2. Build the image with `docker build -t nfs-dynamic-dns .`
3. Run the image (production) with `docker run -d --name nfsn-dynamic-dns nfs-dynamic-dns` (add the `--env-file <file>` argument before the last `nfsn-dynamic-dns` if you want to use your environment variable file)

	Ex: `docker run -d --name nfsn-dynamic-dns --env-file .env nfs-dynamic-dns`

### With Docker Compose
You can use the following config to run this with [docker compose](https://docs.docker.com/compose/).
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
    restart: unless-stopped
 ```

#### Development
To run the container locally (and let it run its cronjobs), use this command:
`docker run -it --rm --init nfs-dynamic-dns`

to run the container locally and be put into a shell where you can run `python3 ./nfsn-ddns.py` yourself use this:
`docker run -it --rm --init nfs-dynamic-dns sh`

If your setup uses environment variables, you will also need to add the `--env-file` argument (or specify variables individually with [the `-e` docker flag](https://docs.docker.com/engine/reference/run/#env-environment-variables)). The `--env-file` option is for [docker run](https://docs.docker.com/engine/reference/commandline/run/) and the env file format can be found [here](https://docs.docker.com/compose/env-file/).

### Docker
When using the Docker file, it's by default scheduled to run every 30 minutes. However, this is configurable when building the
container. The `CRON_SCHEDULE` [build arg](https://docs.docker.com/engine/reference/builder/#arg) can be overriden.

With docker, the build step (step 2) can be done like this:

`$ docker build --build-arg CRON_SCHEDULE="*/5 * * * *" -t nfs-dynamic-dns .`

With docker compose, it can be done like this:
```yaml
version: "3"

services:
  nfs-dynamic-dns:
    image: nfs-dynamic-dns
    build:
      context: ./nfs-dynamic-dns
      args:
        - CRON_SCHEDULE=*/5 * * * *
    container_name: nfs-dynamic-dns
...
 ```

## Troubleshooting
The script communicates with NearlyFreeSpeech.NET via its RESTful API. Specifics about the API can be found [here](https://members.nearlyfreespeech.net/wiki/API/Introduction).
