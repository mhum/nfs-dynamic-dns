package provide nfsUtility 1.0

package require nfsHttp

namespace eval ::nfs::Utility:: {

    namespace export randomRangeString doIPsMatch
}

proc ::nfs::Utility::randomRangeString {length} {
	set chars "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789"
    set range [expr {[string length $chars]-1}]

    set txt ""
    for {set i 0} {$i < $length} {incr i} {
       set pos [expr {int(rand()*$range)}]
       append txt [string range $chars $pos $pos]
    }
    return $txt
}

proc ::nfs::Utility::doIPsMatch {} {
	set domain_ip [::nfs::Http::fetchDomainIP]
	set current_ip [::nfs::Http::fetchCurrentIP]

	return [expr {$domain_ip == $current_ip} ? 1 : 0]
}