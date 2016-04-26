package provide nfsHttp 1.0

package require http
package require json
package require sha1
package require tls

package require nfsUtility

namespace eval ::nfs::Http:: {

    namespace export getRequest fetchCurrentIP fetchDomainIP removeDomain addDomain
}

proc ::nfs::Http::getRequest {uri {body { }}} {

	set url "https://api.nearlyfreespeech.net$uri"
	set header [createHeader $uri $body]

	http::register https 443 [list ::tls::socket -tls1 1]

	set token [http::geturl $url -headers $header -query $body]
	set resp_data [http::data $token]

	::nfs::Utility::validateResponse $resp_data

	http::cleanup $token
	http::unregister https

	return $resp_data
}

proc ::nfs::Http::fetchCurrentIP {} {

	set url "http://ipinfo.io/ip"

	set token [http::geturl $url]
	set data [http::data $token]

	http::cleanup $token

	return [string trim $data]
}

proc ::nfs::Http::fetchDomainIP {} {
	variable ::nfs::CFG

	set uri "/dns/$::nfs::CFG(domain)/listRRs"
	set body "name=$::nfs::CFG(subdomain)"

	set data [getRequest $uri $body]

	# Response will be empty if domain is not set
	if {$data eq {[]} } {
		return "0.0.0.0"
	}

	set resp_data [json::json2dict $data]

	::nfs::Utility::validateResponse $resp_data

	set ip [dict get [lindex $resp_data 0] data]

	return $ip
}

proc ::nfs::Http::removeDomain {domain_ip} {
	variable ::nfs::CFG

	puts "Removing $::nfs::CFG(subdomain).$::nfs::CFG(domain)..."

	set uri "/dns/$::nfs::CFG(domain)/removeRR"
	set body "name=$::nfs::CFG(subdomain)&type=A&data=$domain_ip"

	set data [getRequest $uri $body]
	set resp_data [json::json2dict $data]

	::nfs::Utility::validateResponse $resp_data
}

proc ::nfs::Http::addDomain {current_ip} {
	variable ::nfs::CFG

	puts "Setting $::nfs::CFG(subdomain).$::nfs::CFG(domain) to $current_ip..."

	set uri "/dns/$::nfs::CFG(domain)/addRR"
	set body "name=$::nfs::CFG(subdomain)&type=A&data=$current_ip"

	set data [getRequest $uri $body]
}

proc createHeader {uri body} {
	variable ::nfs::CFG

	set timestamp [clock scan now]
	set salt [::nfs::Utility::randomRangeString  "16"]

	set uts "$::nfs::CFG(username);$timestamp;$salt"
	set body_hash [sha1::sha1 $body]

	set msg "$uts;$::nfs::CFG(api_key);$uri;$body_hash"

	set hash [sha1::sha1 $msg]

	set header "$uts;$hash"

	return "X-NFSN-Authentication $header"

}