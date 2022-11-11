#!/usr/bin/env tclsh

set auto_path [linsert $auto_path 0 .]

package require nfsHttp

namespace eval ::nfs:: {

	variable CFG
#------------------------------CONFIG----------------------------------------------#
	foreach {config value} {
		username  ::env(USERNAME)
		api_key   ::env(API_KEY)
		domain    ::env(DOMAIN)
		subdomain ::env(SUBDOMAIN)
	} {set CFG($config) $value}
#------------------------------END CONFIG------------------------------------------#
}

proc updateIPs {current_ip domain_ip} {
	# When there's no existing record for a domain name, the
	# listRRs API query returns the domain name of the name server.
	if {[string first "nearlyfreespeech.net" $domain_ip] ne -1} {
		puts "The domain IP doesn't appear to be set yet."
	} else {
		puts "Current IP: $current_ip doesn't match Domain IP: $domain_ip"

		# The case where the server returns 0.0.0.0 is probably
		# vestigial, but I'm leaving it in just in case.
		if {$domain_ip ne {0.0.0.0}} {
			::nfs::Http::removeDomain $domain_ip
		}
	}

	::nfs::Http::addDomain $current_ip

	if {[::nfs::Utility::doIPsMatch]} {
		set domain_ip [::nfs::Http::fetchDomainIP]

		puts "IPs match now! Current IP: $current_ip Domain IP: $domain_ip"
		exit
	} else {
		puts "They still don't match. Current IP: $current_ip Domain IP: $domain_ip"
		exit
	}
}

proc compareIPs {} {
	set domain_ip [::nfs::Http::fetchDomainIP]
	set current_ip [::nfs::Http::fetchCurrentIP]

	if {[::nfs::Utility::doIPsMatch]} {
		puts "IPs still match! Current IP: $current_ip Domain IP: $domain_ip"
		exit
	} else {
		updateIPs $current_ip $domain_ip
	}
}

compareIPs
