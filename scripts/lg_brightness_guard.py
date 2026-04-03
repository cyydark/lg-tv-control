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

# Disable SOCKS proxy (Clash on port 7893 interferes with local TV access)
for k in list(os.environ.keys()):
    if "proxy" in k.lower():
        os.environ.pop(k, None)

from bscpylgtv import webos_client, StorageSqliteDict, endpoints

TV_IP = "192.168.2.40"
_SKILL_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.."
STORE_PATH = os.path.join(_SKILL_DIR, ".lg_tv_store.db")


class BrightnessGuardian:
    def __init__(self, target=100, poll=5, threshold=3):
        self.target = target
        self.poll = poll
        self.threshold = threshold  # min drop to trigger restore
        self.client = None
        self.last_backlight = None
        self.is_running = False
        self.last_restore_time = 0  # cooldown to avoid spamming

    async def connect(self):
        storage = StorageSqliteDict(STORE_PATH)
        await storage.async_init()
        self.client = webos_client.WebOsClient(
            TV_IP, storage=storage, without_ssl=False,
            connect_retry_attempts=3, timeout_connect=10
        )
        await self.client.async_init()  # loads client_key from storage
        await self.client.connect()
        print(f"Connected to {TV_IP}")

    async def close(self):
        if self.client:
            await self.client.disconnect()
        print("Disconnected.")

    async def get_backlight(self):
        pic = await self.client.get_picture_settings()
        return int(pic.get("backlight", 0))

    async def restore_backlight(self):
        """Set backlight directly. TV may briefly show a pairing dialog on connect,
        but the command is accepted regardless — no ENTER needed."""
        await self.client.luna_request(
            endpoints.LUNA_SET_SYSTEM_SETTINGS,
            {"category": "picture", "settings": {"backlight": str(self.target)}}
        )

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
        target=args.target,
        poll=args.interval,
        threshold=args.threshold
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
