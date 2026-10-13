#!/usr/bin/env bash
set -e

echo "[*] Initializing Remote Modality Node (${LOCAL_AET:-CT_SCANNER_01})..."

if [ -n "$DEFAULT_GATEWAY" ]; then
    echo "[*] Setting default gateway to $DEFAULT_GATEWAY..."
    ip route del default || true
    ip route add default via "$DEFAULT_GATEWAY" || true
fi

echo "[+] Default route configured:"
ip route show

echo "[*] Modality node is ready. Keeping container alive for operator access..."
tail -f /dev/null
