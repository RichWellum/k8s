#!/bin/bash
runOnMac=false
int2ip() { printf ${2+-v} $2 "%d.%d.%d.%d" \
        $(($1>>24)) $(($1>>16&255)) $(($1>>8&255)) $(($1&255)) ;}
ip2int() { local _a=(${1//./ }) ; printf ${2+-v} $2 "%u" $(( _a<<24 |
                  ${_a[1]} << 16 | ${_a[2]} << 8 | ${_a[3]} )) ;}
while IFS=$' :\t\r\n' read a b c d; do
    [ "$a" = "usage" ] && [ "$b" = "route" ] && runOnMac=true
    if $runOnMac ;then
        case $a in
            gateway )    gWay=$b  ;;
            interface )  iFace=$b ;;
        esac
    else
        [ "$a" = "0.0.0.0" ] && [ "$c" = "$a" ] && iFace=${d##* } gWay=$b
    fi
done < <(/sbin/route -n 2>&1 || /sbin/route -n get 0.0.0.0/0)
ip2int $gWay gw
while read lhs rhs; do
    [ "$lhs" ] && {
        [ -z "${lhs#*:}" ] && iface=${lhs%:}
        [ "$lhs" = "inet" ] && [ "$iface" = "$iFace" ] && {
            mask=${rhs#*netmask }
            mask=${mask%% *}
            [ "$mask" ] && [ -z "${mask%0x*}" ] &&
                printf -v mask %u $mask ||
                ip2int $mask mask
            ip2int ${rhs%% *} ip
            (( ( ip & mask ) == ( gw & mask ) )) &&
                int2ip $ip myIp && int2ip $mask netMask
        }
    }
done < <(/sbin/ifconfig)
printf "%-12s: %s\n" Interface $iFace Local\ Ip $myIp \
       Gateway $gWay Net\ mask $netMask Run\ on\ mac $runOnMac
sleep 10000
