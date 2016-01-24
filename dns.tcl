#!/usr/bin/env tclsh

set auto_path [linsert $auto_path 0 .]

package require nfsHttp

namespace eval ::nfs:: {

	variable CFG
#------------------------------CONFIG----------------------------------------------#
	foreach {config value} {
		username  USERNAME
		api_key   API_KEY
		domain    DOMAIN
		subdomain SUBDOMAIN
	} {set CFG($config) $value}
#------------------------------END CONFIG------------------------------------------#
}

proc updateIPs {current_ip domain_ip} {
	puts "Current IP: $current_ip doesn't match Domain IP: $domain_ip"

	::nfs::Http::removeDomain $domain_ip
	::nfs::Http::addDomain $current_ip

	if {[::nfs::Utility::doIPsMatch]} {
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