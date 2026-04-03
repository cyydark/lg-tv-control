#!/usr/bin/env python3
"""
LG TV Control CLI
Control LG webOS TV via WebSocket API using bscpylgtv.

Usage:
    python3 lg_tv_control.py --ip 192.168.2.40 --get
    python3 lg_tv_control.py --ip 192.168.2.40 --backlight 80
    python3 lg_tv_control.py --ip 192.168.2.40 --brightness 50
    python3 lg_tv_control.py --ip 192.168.2.40 --mode cinema
    python3 lg_tv_control.py --ip 192.168.2.40 --power
    python3 lg_tv_control.py --ip 192.168.2.40 --inputs
    python3 lg_tv_control.py --ip 192.168.2.40 --apps
    python3 lg_tv_control.py --ip 192.168.2.40 --launch com.webos.app.hdmi2
"""
import os
import sys
import argparse
import json
import asyncio

# Use bscpylgtv from Python 3.9
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

from bscpylgtv import webos_client, StorageSqliteDict, endpoints

# Default store in skill directory (symlinked from ~/.lg_tv_store.db)
_SKILL_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.."
DEFAULT_STORE = os.path.join(_SKILL_DIR, ".lg_tv_store.db")

# Picture modes available on OLED C1
PICTURE_MODES = [
    "cinema", "dolbyHdrCinema", "dolbyHdrCinemaBright", "dolbyHdrDarkAmazon",
    "dolbyHdrGame", "dolbyHdrStandard", "dolbyHdrVivid", "dolbyStandard",
    "eco", "expert1", "expert2", "filmMaker", "game", "hdrCinema",
    "hdrCinemaBright", "hdrExternal", "hdrFilmMaker", "hdrGame",
    "hdrStandard", "hdrVivid", "normal", "photo", "sports", "vivid"
]


class LgTvController:
    def __init__(self, ip, store_path=None):
        self.ip = ip
        self.store_path = store_path or DEFAULT_STORE
        self.client = None

    async def connect(self):
        storage = StorageSqliteDict(self.store_path)
        await storage.async_init()
        self.client = webos_client.WebOsClient(
            self.ip,
            storage=storage,
            without_ssl=False,
            connect_retry_attempts=3,
            timeout_connect=10,
        )
        await self.client.async_init()  # ← loads client_key from storage
        await self.client.connect()

    async def close(self):
        if self.client:
            await self.client.disconnect()

    # ── Picture settings ────────────────────────────────────────────────

    async def get_picture(self):
        return await self.client.get_picture_settings()

    async def set_backlight(self, value):
        """Set backlight 0-255. Must be string."""
        v = max(0, min(255, int(value)))
        return await self.client.luna_request(
            endpoints.LUNA_SET_SYSTEM_SETTINGS,
            {"category": "picture", "settings": {"backlight": str(v)}}
        )

    async def set_brightness(self, value):
        """Set brightness 0-100."""
        v = max(0, min(100, int(value)))
        return await self.client.luna_request(
            endpoints.LUNA_SET_SYSTEM_SETTINGS,
            {"category": "picture", "settings": {"brightness": str(v)}}
        )

    async def set_contrast(self, value):
        v = max(0, min(100, int(value)))
        return await self.client.luna_request(
            endpoints.LUNA_SET_SYSTEM_SETTINGS,
            {"category": "picture", "settings": {"contrast": str(v)}}
        )

    async def set_picture_mode(self, mode):
        """Set picture mode. e.g. cinema, game, hdrGame, dolbyHdrCinema."""
        return await self.client.luna_request(
            endpoints.LUNA_SET_SYSTEM_SETTINGS,
            {"category": "picture", "settings": {"pictureMode": mode}}
        )

    async def set_energy_saving(self, value="off"):
        """Set energy saving: off, min, medium, max, screen_off."""
        return await self.client.luna_request(
            endpoints.LUNA_SET_SYSTEM_SETTINGS,
            {"category": "picture", "settings": {"energySaving": value}}
        )

    async def set_hdr_tone_mapping(self, value="off"):
        """Set HDR Dynamic Tone Mapping: on, off."""
        return await self.client.luna_request(
            endpoints.LUNA_SET_SYSTEM_SETTINGS,
            {"category": "picture", "settings": {"hdrDynamicToneMapping": value}}
        )

    # ── System ────────────────────────────────────────────────────────

    async def get_power(self):
        return await self.client.get_power_state()

    async def get_inputs(self):
        return await self.client.get_inputs()

    async def get_apps(self):
        return await self.client.get_apps_all()

    async def get_current_app(self):
        return await self.client.get_current_app()

    async def launch_app(self, app_id):
        return await self.client.launch_app(app_id)

    async def set_input(self, input_id):
        """Set input: HDMI_1, HDMI_2, HDMI_3, HDMI_4, etc."""
        return await self.client.set_input(input_id)

    async def power_off(self):
        return await self.client.power_off()


async def main():
    parser = argparse.ArgumentParser(description="LG TV Control")
    parser.add_argument("--ip", required=True, help="TV IP address")
    parser.add_argument("--store", default=DEFAULT_STORE, help="Key store path")
    parser.add_argument("--get", action="store_true", help="Get picture settings")
    parser.add_argument("--power", action="store_true", help="Get power state")
    parser.add_argument("--inputs", action="store_true", help="List inputs")
    parser.add_argument("--apps", action="store_true", help="List apps")
    parser.add_argument("--backlight", type=int, metavar="0-255", help="Set backlight")
    parser.add_argument("--brightness", type=int, metavar="0-100", help="Set brightness")
    parser.add_argument("--contrast", type=int, metavar="0-100", help="Set contrast")
    parser.add_argument("--mode", choices=PICTURE_MODES, help="Set picture mode")
    parser.add_argument("--energy-saving", choices=["off", "min", "medium", "max", "screen_off"],
                       default=None, help="Set energy saving")
    parser.add_argument("--hdr-tone", choices=["on", "off"], help="Set HDR Dynamic Tone Mapping")
    parser.add_argument("--launch", metavar="APP_ID", help="Launch app by ID")
    parser.add_argument("--set-input", metavar="INPUT", help="Set input (e.g. HDMI_2)")
    parser.add_argument("--power-off", action="store_true", help="Power off TV")
    args = parser.parse_args()

    ctrl = LgTvController(args.ip, args.store)

    try:
        print(f"Connecting to {args.ip}...")
        await ctrl.connect()
        print("Connected!\n")

        if args.get:
            print("=== Picture Settings ===")
            print(json.dumps(await ctrl.get_picture(), indent=2))

        if args.power:
            print("=== Power State ===")
            print(json.dumps(await ctrl.get_power(), indent=2))

        if args.inputs:
            print("=== Inputs ===")
            for inp in await ctrl.get_inputs():
                cur = " ← current" if inp.get("connected") else ""
                print(f"  {inp['id']}: {inp.get('label', '')} ({inp.get('appId', '')}){cur}")

        if args.apps:
            print("=== Apps ===")
            for app in await ctrl.get_apps():
                print(f"  {app['id']}: {app.get('title', '')}")

        if args.backlight is not None:
            print(f"Setting backlight to {args.backlight}...")
            print(await ctrl.set_backlight(args.backlight))

        if args.brightness is not None:
            print(f"Setting brightness to {args.brightness}...")
            print(await ctrl.set_brightness(args.brightness))

        if args.contrast is not None:
            print(f"Setting contrast to {args.contrast}...")
            print(await ctrl.set_contrast(args.contrast))

        if args.mode:
            print(f"Setting picture mode to {args.mode}...")
            print(await ctrl.set_picture_mode(args.mode))

        if args.energy_saving:
            print(f"Setting energy saving to {args.energy_saving}...")
            print(await ctrl.set_energy_saving(args.energy_saving))

        if args.hdr_tone:
            print(f"Setting HDR tone mapping to {args.hdr_tone}...")
            print(await ctrl.set_hdr_tone_mapping(args.hdr_tone))

        if args.launch:
            print(f"Launching {args.launch}...")
            print(await ctrl.launch_app(args.launch))

        if args.set_input:
            print(f"Switching to {args.set_input}...")
            print(await ctrl.set_input(args.set_input))

        if args.power_off:
            print("Powering off...")
            print(await ctrl.power_off())

    finally:
        await ctrl.close()
        print("\nDisconnected.")


if __name__ == "__main__":
    asyncio.run(main())
