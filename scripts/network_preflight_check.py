#!/usr/bin/env python3
"""Check the network boundaries required by the DICOM deployment."""

from __future__ import annotations

import argparse
import shutil
import socket
import subprocess
import sys
import time
from typing import Sequence


def run_ping(host: str, count: int = 4) -> bool:
    count_flag = "-n" if sys.platform == "win32" else "-c"
    try:
        result = subprocess.run(
            ["ping", count_flag, str(count), host],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"ICMP {host}: unavailable ({exc})")
        return False
    print(f"ICMP {host}: {'reachable' if result.returncode == 0 else 'unreachable'}")
    return result.returncode == 0


def run_path_mtu(host: str, payload_size: int = 1332) -> bool:
    if sys.platform == "darwin":
        arguments: Sequence[str] = ("-c", "2", "-D", "-s", str(payload_size), host)
    elif sys.platform == "linux":
        arguments = ("-c", "2", "-M", "do", "-s", str(payload_size), host)
    else:
        arguments = ("-n", "2", "-f", "-l", str(payload_size), host)
    try:
        result = subprocess.run(["ping", *arguments], capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"DF path-MTU check {host}: unavailable ({exc})")
        return False
    print(f"DF path-MTU check {host}: {'passed' if result.returncode == 0 else 'failed'}")
    return result.returncode == 0


def check_tcp(host: str, port: int, timeout: float = 3.0) -> bool:
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed_ms = (time.perf_counter() - started) * 1000
            print(f"TCP {host}:{port}: open ({elapsed_ms:.1f} ms)")
            return True
    except socket.timeout:
        print(f"TCP {host}:{port}: timeout")
    except OSError as exc:
        print(f"TCP {host}:{port}: unavailable ({exc})")
    return False


def check_ipsec() -> bool:
    swanctl = shutil.which("swanctl")
    ipsec = shutil.which("ipsec")
    if swanctl:
        command = [swanctl, "--list-sas"]
    elif ipsec:
        command = [ipsec, "status"]
    else:
        print("IPsec state: strongSwan tools are not installed")
        return True
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"IPsec state: unavailable ({exc})")
        return False
    active = "ESTABLISHED" in result.stdout or "installed" in result.stdout
    print(f"IPsec state: {'active' if active else 'not active'}")
    return active


def main() -> int:
    parser = argparse.ArgumentParser(description="Check DICOM network and IPsec prerequisites")
    parser.add_argument("--target-ip", default="10.200.20.50")
    parser.add_argument("--router-ip", default="10.200.20.10")
    parser.add_argument("--skip-mtu", action="store_true")
    args = parser.parse_args()

    results = [check_ipsec(), run_ping(args.target_ip)]
    if not args.skip_mtu and results[-1]:
        results.append(run_path_mtu(args.target_ip))
    for host, port in (
        (args.target_ip, 4242),
        (args.target_ip, 8042),
        (args.router_ip, 11112),
    ):
        results.append(check_tcp(host, port))
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
