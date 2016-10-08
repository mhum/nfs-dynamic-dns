# NearlyFreeSpeech.NET Dynamic DNS
This script will update the A DNS record for a subdomain at [NearlyFreeSpeech.NET](https://www.nearlyfreespeech.net)
with the public IP address for the machine the script runs on. Run this script on a server in which the public IP
address is dynamic and changes so your subdomain is always up to date.

## How It Works
There are two steps to this script. First, it retrieves the configured IP address for the subdomain, the current public
IP address of the server, and then compares the two. If the public IP address is different, it updates the A record of
the subdomain with the new IP address.

## Requirements
[Tcl](http://www.tcl.tk/software/tcltk) and [Tcllib](http://www.tcl.tk/software/tcllib) are the only two requirements. They come pre-installed on most *nix operating systems.

## Configuring
Configurations are set straight within the `dns.tcl` file in the `CONFIG` section.

### Configs
```
username  USERNAME
api_key   API_KEY
domain    DOMAIN
subdomain SUBDOMAIN
```
```
username    --Your NFSN username
api_key     --API key for using NFSN's APIs. This can be obtained via a service request
domain      ---Domain that the subdomain belongs to
subdomain   ---Subdomain to update with the script
```

## Running
It is as easy as running: `tclsh dns.tcl`

or make it executable with `chmod u+x dns.tcl` and then run `./dns.tcl`

## Scheduling
It can even be setup to run as a cron job to completely automate this process. Something such as:
> @hourly /usr/local/bin/tclsh /scripts/nfs-dynamic-dns/dns.tcl

## Troubleshooting
The script communicates with NearlyFreeSpeech.NET via its RESTful API. Specifics about the API can be found [here](https://members.nearlyfreespeech.net/wiki/API/Introduction).
