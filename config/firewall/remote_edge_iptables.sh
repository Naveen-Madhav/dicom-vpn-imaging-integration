#!/usr/bin/env bash
set -euo pipefail

echo "Applying remote edge firewall policy"

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

iptables -A INPUT -i eth1 -p udp --dport 500 -s 198.51.100.1 -j ACCEPT
iptables -A INPUT -i eth1 -p udp --dport 4500 -s 198.51.100.1 -j ACCEPT
iptables -A INPUT -i eth1 -p esp -s 198.51.100.1 -j ACCEPT

iptables -A INPUT -i eth0 -s 10.100.10.0/24 -p icmp --icmp-type echo-request -j ACCEPT
iptables -A INPUT -i eth0 -s 10.100.10.0/24 -p udp --dport 53 -j ACCEPT

iptables -A FORWARD -i eth0 -s 10.100.10.0/24 -d 10.200.20.0/24 -p tcp --dport 104 -m policy --dir out --pol ipsec -j ACCEPT
iptables -A FORWARD -i eth0 -s 10.100.10.0/24 -d 10.200.20.0/24 -p tcp --dport 11112 -m policy --dir out --pol ipsec -j ACCEPT
iptables -A FORWARD -i eth0 -s 10.100.10.0/24 -d 10.200.20.0/24 -p tcp --dport 4242 -m policy --dir out --pol ipsec -j ACCEPT
iptables -A FORWARD -i eth0 -s 10.100.10.0/24 -d 10.200.20.0/24 -p tcp --dport 8042 -m policy --dir out --pol ipsec -j ACCEPT
iptables -A FORWARD -i eth0 -s 10.100.10.0/24 -d 10.200.20.0/24 -p icmp -m policy --dir out --pol ipsec -j ACCEPT

iptables -A FORWARD -i eth1 -s 10.200.20.0/24 -d 10.100.10.0/24 -m policy --dir in --pol ipsec -j ACCEPT

iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -d 10.200.20.0/24 -j TCPMSS --set-mss 1360
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -s 10.200.20.0/24 -j TCPMSS --set-mss 1360

iptables -A INPUT -m limit --limit 5/min -j LOG --log-prefix "[FW_REMOTE_DROP_IN]: " --log-level 4
iptables -A FORWARD -m limit --limit 5/min -j LOG --log-prefix "[FW_REMOTE_DROP_FWD]: " --log-level 4

echo "Remote edge firewall policy applied"
