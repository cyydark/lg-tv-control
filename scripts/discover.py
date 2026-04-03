#!/usr/bin/env python3
"""
LG TV Network Discovery
Scans the local network for LG webOS TVs.
Usage: python3 discover.py [--subnet 192.168.2]
"""
import subprocess
import sys
import argparse
import concurrent.futures

DEFAULT_SUBNET = "192.168.2"
CHECK_PORTS = [3001, 3000]


def check_port(ip, port):
    """Check if a port is open on the given IP."""
    try:
        result = subprocess.run(
            ["nc", "-z", "-w1", ip, str(port)],
            capture_output=True,
            timeout=1
        )
        return result.returncode == 0, ip, port
    except Exception:
        return False, ip, port


def scan_subnet(subnet, ports=None):
    """Scan a subnet for LG TV WebSocket ports."""
    if ports is None:
        ports = CHECK_PORTS

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = []
        for port in ports:
            for i in range(1, 255):
                ip = f"{subnet}.{i}"
                futures.append(executor.submit(check_port, ip, port))

        for future in concurrent.futures.as_completed(futures):
            found, ip, port = future.result()
            if found:
                results.append((ip, port))
                print(f"Found LG TV at {ip}:{port}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Discover LG webOS TVs on the network")
    parser.add_argument("--subnet", default=DEFAULT_SUBNET,
                        help=f"Subnet to scan (default: {DEFAULT_SUBNET})")
    args = parser.parse_args()

    subnet = args.subnet.rstrip(".")
    print(f"Scanning {subnet}.1-254 for LG TV ports {CHECK_PORTS}...")

    results = scan_subnet(subnet)

    if results:
        print(f"\nFound {len(results)} LG TV(s):")
        for ip, port in results:
            print(f"  {ip}:{port}")
    else:
        print("\nNo LG TVs found. Tips:")
        print("  - Make sure TV and computer are on the same network")
        print("  - Check TV is powered on")
        print("  - Try a different subnet (--subnet 192.168.1)")


if __name__ == "__main__":
    main()
