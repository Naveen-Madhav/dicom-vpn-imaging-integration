#!/usr/bin/env bash
set -euo pipefail

: "${VPN_PSK:?VPN_PSK must be provided to the VPN gateway}"
escaped_psk=${VPN_PSK//\\/\\\\}
escaped_psk=${escaped_psk//\"/\\\"}
umask 077
printf ': PSK "%s"\n' "$escaped_psk" > /etc/ipsec.secrets
mkdir -p /etc/swanctl
printf 'secrets { ike-site-alpha { secret = "%s" } }\n' "$escaped_psk" > /etc/swanctl/swanctl.secrets

echo "Starting remote VPN gateway"

sysctl -w net.ipv4.ip_forward=1

if [ -f /root/apply_firewall.sh ]; then
    bash /root/apply_firewall.sh
fi

ipsec start
swanctl --load-all
swanctl --initiate --child telerad-dicom-tunnel || true

ipsec status || true

tail -f /var/log/syslog /var/log/messages 2>/dev/null || tail -f /dev/null
