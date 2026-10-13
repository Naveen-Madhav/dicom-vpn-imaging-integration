#!/usr/bin/env bash
set -euo pipefail

echo "Applying central data-center firewall policy"

sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv4.conf.all.accept_redirects=0
sysctl -w net.ipv4.conf.all.send_redirects=0

iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X

iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

iptables -A INPUT -i eth1 -p udp --dport 500 -s 198.51.100.2 -j ACCEPT
iptables -A INPUT -i eth1 -p udp --dport 4500 -s 198.51.100.2 -j ACCEPT
iptables -A INPUT -i eth1 -p esp -s 198.51.100.2 -j ACCEPT

iptables -A INPUT -i eth0 -s 10.200.20.0/24 -p icmp --icmp-type echo-request -j ACCEPT

iptables -A FORWARD -i eth1 -s 10.100.10.0/24 -d 10.200.20.10 -p tcp --dport 11112 -m policy --dir in --pol ipsec -j ACCEPT

iptables -A FORWARD -i eth1 -s 10.100.10.0/24 -d 10.200.20.50 -p tcp --dport 4242 -m policy --dir in --pol ipsec -j ACCEPT
iptables -A FORWARD -i eth1 -s 10.100.10.0/24 -d 10.200.20.50 -p tcp --dport 104 -m policy --dir in --pol ipsec -j ACCEPT

iptables -A FORWARD -i eth1 -s 10.100.10.0/24 -d 10.200.20.50 -p tcp --dport 8042 -m policy --dir in --pol ipsec -j ACCEPT

iptables -A FORWARD -i eth1 -s 10.100.10.0/24 -d 10.200.20.0/24 -p icmp -m policy --dir in --pol ipsec -j ACCEPT

iptables -A FORWARD -i eth0 -s 10.200.20.0/24 -d 10.100.10.0/24 -m policy --dir out --pol ipsec -j ACCEPT

iptables -A FORWARD -i eth1 -s 10.100.10.0/24 -p tcp -m multiport --dports 22,80,445,3389 -j LOG --log-prefix "[DC_UNAUTHORIZED_PORT_BLOCKED]: "
iptables -A FORWARD -i eth1 -s 10.100.10.0/24 -p tcp -m multiport --dports 22,80,445,3389 -j DROP

iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -d 10.100.10.0/24 -j TCPMSS --set-mss 1360
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -s 10.100.10.0/24 -j TCPMSS --set-mss 1360

iptables -A FORWARD -m limit --limit 5/min -j LOG --log-prefix "[FW_CENTRAL_DROP_FWD]: " --log-level 4

echo "Central data-center firewall policy applied"
