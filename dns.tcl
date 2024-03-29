#!/usr/bin/env tclsh

set auto_path [linsert $auto_path 0 .]

package require nfsHttp

namespace eval ::nfs:: {

	variable CFG
#------------------------------CONFIG----------------------------------------------#
	set subdomain ""
	if {[info exists ::env(SUBDOMAIN)]} {
	    set subdomain $::env(SUBDOMAIN)
	}

	set ip_provider "http://ipinfo.io/ip"
	if {[info exists ::env(IP_PROVIDER)]} {
	    set ip_provider $::env(IP_PROVIDER)
	}

	foreach {config value} [list\
			username  $::env(USERNAME)\
			api_key   $::env(API_KEY)\
			domain    $::env(DOMAIN)\
			subdomain $subdomain\
			ip_provider $ip_provider\
	] {set CFG($config) $value}
#------------------------------END CONFIG------------------------------------------#
}

proc updateIPs {current_ip domain_ip} {
	set now [clock seconds]
	# When there's no existing record for a domain name, the
	# listRRs API query returns the domain name of the name server.
	if {[string first "nearlyfreespeech.net" $domain_ip] ne -1} {
		puts "[clock format $now -format {%y-%m-%d %H:%M:%S}]: The domain IP doesn't appear to be set yet."
	} else {
		puts "[clock format $now -format {%y-%m-%d %H:%M:%S}]: Current IP: $current_ip doesn't match Domain IP: $domain_ip"
	}

	# Set or update the domain IP
	::nfs::Http::replaceDomain $current_ip

	# Check to see if the update was successful
	set now [clock seconds]
	if {[::nfs::Utility::doIPsMatch]} {
		set domain_ip [::nfs::Http::fetchDomainIP]

		puts "[clock format $now -format {%y-%m-%d %H:%M:%S}]: IPs match now! Current IP: $current_ip Domain IP: $domain_ip"
	} else {
		puts "[clock format $now -format {%y-%m-%d %H:%M:%S}]: They still don't match. Current IP: $current_ip Domain IP: $domain_ip"
	}
}

proc compareIPs {} {
	set domain_ip [::nfs::Http::fetchDomainIP]
	set current_ip [::nfs::Http::fetchCurrentIP]
	set now [clock seconds]

	if {[::nfs::Utility::doIPsMatch]} {
		puts "[clock format $now -format {%y-%m-%d %H:%M:%S}]: IPs still match! Current IP: $current_ip Domain IP: $domain_ip"
		exit
	} else {
		updateIPs $current_ip $domain_ip
	}
}

compareIPs
