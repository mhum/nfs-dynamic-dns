package provide nfsUtility 1.0

package require nfsHttp

namespace eval ::nfs::Utility:: {

    namespace export randomRangeString doIPsMatch validateResponse
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

proc ::nfs::Utility::validateResponse {resp} {
  if {[dict exists $resp error]} {
    set now [clock seconds]

    puts "[clock format $now -format {%y-%m-%d %H:%M:%S}]: ERROR: [dict get $resp error]"
    puts "[clock format $now -format {%y-%m-%d %H:%M:%S}]: ERROR: [dict get $resp debug]"

    exit
  }
}
