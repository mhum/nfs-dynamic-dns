# NearlyFreeSpeech.NET Dynamic DNS
This script will update the A DNS record for a domain/subdomain at [NearlyFreeSpeech.NET](https://www.nearlyfreespeech.net)
with the public IP address for the machine the script runs on. Run this script on a server in which the public IP
address is dynamic and changes so your domain is always up to date.

## How It Works
There are two steps to this script. First, it retrieves the configured IP address for the subdomain, the current public
IP address of the server, and then compares the two. If the public IP address is different, it updates the A record of
the subdomain with the new IP address.

## Requirements
[Tcl](http://www.tcl.tk/software/tcltk) and [Tcllib](http://www.tcl.tk/software/tcllib) are the only two requirements. They come pre-installed on most *nix operating systems.

## Configuring
Configurations are set by providing the script with environment variables

### Configs
```
username  USERNAME
api_key   API_KEY
domain    DOMAIN
subdomain SUBDOMAIN
```
```
username    --Your NFSN username
api_key     --API key for using NFSN's APIs. This can be obtained via the Member Interface > "Profile" tab > "Actions" > "Manage API Key".
domain      ---Domain that the subdomain belongs to
subdomain   ---Subdomain to update with the script. Leave blank for the bare domain name.
```

## Running
### Manually
It is as easy as running: `tclsh dns.tcl`

or make it executable with `chmod u+x dns.tcl` and then run `./dns.tcl`

### With Docker
1. set the configuration values in the script the way you want them (or create a file containing the environment variables)
2. build the image with `docker build -t nfs-dynamic-dns .`
3. run the image (production) with `docker run -d --name nfsn-dynamic-dns nfs-dynamic-dns` (add the `--envfile <file>` argument before the last `nfsn-dynamic-dns` if you want to use your environment variable file)

#### Development
To run the container locally (and let it run its cronjobs), use this command:
`docker run -it --rm --init nfs-dynamic-dns`

to run the container locally and be put into a shell where you can run `./dns.tcl` yourself use this:
`docker run -it --rm --init nfs-dynamic-dns sh`

If your setup uses environment variables, you will also need to add the `--envfile` argument (or specify variables individually with [the `-e` docker flag](https://docs.docker.com/engine/reference/run/#env-environment-variables)).

## Scheduling
It can even be setup to run as a cron job to completely automate this process. Something such as:
> @hourly /usr/local/bin/tclsh /scripts/nfs-dynamic-dns/dns.tcl

## Troubleshooting
The script communicates with NearlyFreeSpeech.NET via its RESTful API. Specifics about the API can be found [here](https://members.nearlyfreespeech.net/wiki/API/Introduction).
