#!/usr/bin/env python3
"""
LG TV Brightness Guardian
Monitors backlight and auto-restores if TV dims itself.
Presses ENTER to dismiss the confirmation dialog automatically.
"""
import os
import sys
import asyncio
import json
import time
import argparse

# Use Python 3.9 packages (where bscpylgtv is installed)
sys.path.insert(0, "/Users/chenyanyu/Library/Python/3.9/lib/python/site-packages")

# Disable macOS system SOCKS proxy (Clash on :7893) for local TV WebSocket access.
# urllib.request.getproxies() reads macOS system proxy settings, which websockets
# follows unconditionally. Must patch before bscpylgtv imports websockets.
import urllib.request
_orig_getproxies = urllib.request.getproxies


def _no_socks_getproxies():
    proxies = _orig_getproxies()
    proxies.pop("socks", None)
    return proxies


urllib.request.getproxies = _no_socks_getproxies

from bscpylgtv import webos_client, StorageSqliteDict

_SKILL_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.."
STORE_PATH = os.path.join(_SKILL_DIR, ".lg_tv_store.db")


class BrightnessGuardian:
    def __init__(self, ip: str, target: int = 100, poll: int = 5, threshold: int = 3):
        self.ip = ip
        self.target = target
        self.poll = poll
        self.threshold = threshold  # min drop to trigger restore
        self.client: webos_client.WebOsClient | None = None
        self.last_backlight: int | None = None
        self.is_running = False
        self.last_restore_time = 0.0  # cooldown to avoid spamming

    async def connect(self):
        storage = StorageSqliteDict(STORE_PATH)
        await storage.async_init()
        self.client = webos_client.WebOsClient(
            self.ip, storage=storage, without_ssl=False,
            connect_retry_attempts=3, timeout_connect=10
        )
        await self.client.async_init()  # loads client_key from storage
        await self.client.connect()
        print(f"Connected to {self.ip}")

    async def close(self):
        if self.client:
            await self.client.disconnect()
        print("Disconnected.")

    async def get_backlight(self) -> int:
        pic = await self.client.get_picture_settings()
        return int(pic.get("backlight", 0))

    async def restore_backlight(self):
        """Set backlight via set_settings (Luna endpoint, works reliably)."""
        await self.client.set_settings("picture", {"backlight": str(self.target)})

    async def run(self):
        await self.connect()
        self.is_running = True
        print(f"Monitoring every {self.poll}s, target: {self.target}, threshold: {self.threshold}")
        print("Ctrl+C to stop\n")

        while self.is_running:
            try:
                current = await self.get_backlight()
                now = time.time()

                if self.last_backlight is not None:
                    diff = current - self.last_backlight

                    if diff < 0:
                        symbol = "↓"
                        consecutive_drops = True
                    elif diff > 0:
                        symbol = "↑"
                        consecutive_drops = False
                    else:
                        symbol = "="
                        consecutive_drops = False

                    print(f"[{time.strftime('%H:%M:%S')}] Backlight: {current}  {symbol} {abs(diff)}")

                    # Auto-restore if TV dimmed beyond threshold (and not in cooldown)
                    if (current < self.target - self.threshold and
                            consecutive_drops and
                            now - self.last_restore_time > 15):
                        print(f"  → TV auto-dimmed by {abs(diff)}! Restoring to {self.target}...")
                        await self.restore_backlight()
                        print(f"  → Restored & dialog dismissed.")
                        self.last_restore_time = now

                else:
                    print(f"[{time.strftime('%H:%M:%S')}] Backlight: {current}  (initial)")

                self.last_backlight = current

            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")
                await asyncio.sleep(10)
                try:
                    await self.connect()
                except:
                    pass

            await asyncio.sleep(self.poll)

    def stop(self):
        self.is_running = False


async def main():
    parser = argparse.ArgumentParser(description="LG TV Brightness Guardian")
    parser.add_argument("-t", "--ip", default=TV_IP, help=f"TV IP")
    parser.add_argument("--target", type=int, default=100, choices=range(0, 256),
                        metavar="0-255", help="Target backlight")
    parser.add_argument("-i", "--interval", type=int, default=5,
                        help="Poll interval (seconds)")
    parser.add_argument("--threshold", type=int, default=3,
                        help="Min drop to trigger restore")
    args = parser.parse_args()

    guardian = BrightnessGuardian(
        ip=args.ip,
        target=args.target,
        poll=args.interval,
        threshold=args.threshold,
    )

    try:
        await guardian.run()
    except KeyboardInterrupt:
        print("\nStopping...")
        guardian.stop()
    finally:
        await guardian.close()


if __name__ == "__main__":
    asyncio.run(main())
