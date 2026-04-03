---
name: lg-tv-control
description: Discover and control LG webOS TVs via WebSocket API. Features network scanning, brightness control, settings management, and auto-restore guardian daemon.
license: MIT
---

# LG TV Control

Control LG webOS TVs over the local network without needing developer mode or SSH.

## Quick Start

```bash
# 1. Scan network for LG TV
python3 scripts/discover.py

# 2. Control brightness
python3 scripts/lg_tv_control.py --ip <TV_IP> --backlight 80

# 3. Run brightness guardian (auto-restore if TV dims itself)
python3 scripts/lg_brightness_guard.py --ip <TV_IP> --target 100
```

## Setup

```bash
pip install bscpylgtv websockets
```

## Key Findings (webOS 6.0 / OLED55C1PCB)

### What works via WebSocket (port 3001)
- Power state, volume, inputs, app launch/close ✅
- Picture settings read (`get_picture_settings`) ✅
- Picture settings write (`set_settings`) ✅
- Subscriptions (`subscribe_picture_settings`) ✅
- `com.webos.service.oledepl` TPC/GSR (OLED panel power management) ✅
- `com.webos.settingsservice` via direct `ssap://` ❌ (404)
- System logs access ❌ (blocked)

### set_settings — primary way to write picture settings
Use `set_settings('picture', dict)` instead of `set_system_settings`:
```python
# CORRECT: uses Luna endpoint internally
await client.set_settings('picture', {'backlight': 100, 'contrast': 100})

# Does NOT work: SSAP endpoint rejects most keys
await client.set_system_settings('picture', {'backlight': 100})  # ❌ blocked
```
TV takes ~1 second to apply changes after `set_settings` returns `True`.

### Critical discovery: string values required
All picture settings must be passed as **strings**, not integers:
```python
# WRONG - will silently fail
{"backlight": 50}

# CORRECT
{"backlight": "50"}
```

### Pairing dialog: root cause found and fixed
**Early versions** of these scripts missed `await client.async_init()`, causing `client_key` to always be `None`, making the TV show a pairing popup on every connection.

**Fixed**: all scripts now call `await self.client.async_init()` before `await self.client.connect()`. With the stored key loaded, TV accepts the connection silently — **no popup after initial pairing**.

After first pairing, the key is saved in `.lg_tv_store.db`. Subsequent connections reuse it without prompting.

### First-time pairing
On first connect, a pairing request appears on the TV. Accept it — the client key is saved automatically. Subsequent connections are silent.

## TV Settings Reference (OLED55C1, webOS 6.0)

All auto-dim features found to be already off on this TV:

| Setting | Default | Notes |
|---------|---------|-------|
| `energySaving` | off | |
| `motionEyeCare` | off | |
| `dynamicContrast` | off | |
| `dynamicColor` | off | |
| `ambientLightCompensation` | off | |
| `peakBrightness` | off | |
| `hdrDynamicToneMapping` | on | May compress HDR brightness |
| `localDimming` | medium | |
| `pictureMode` | dolbyHdrCinemaBright | Current mode |

### Brightness range
- Standard: **0-100**
- Extended: **0-255** (TV accepts higher values)

## Network Discovery

Use port scan to find TV IP:

```bash
# Scan common LG TV subnet
for ip in 192.168.x.{1..254}; do
  nc -z -w1 "$ip" 3001 && echo "LG TV: $ip"
done
```

TV identification: port 3000/3001 open = LG webOS TV

## Files

```
lg-tv-control/
├── .lg_tv_key          ← TV pairing client key
├── .lg_tv_store.db    ← Paired device credentials (SQLite)
├── scripts/
│   ├── discover.py           ← Network scanner
│   ├── lg_tv_control.py      ← CLI control
│   └── lg_brightness_guard.py ← Auto-restore daemon
└── docs/
    └── api_reference.md      ← Full API details
```

## Running Scripts

```bash
# Discover TV on network
python3 scripts/discover.py --subnet 192.168.2

# Get current settings
python3 scripts/lg_tv_control.py --ip 192.168.2.40 --get

# Control brightness
python3 scripts/lg_tv_control.py --ip 192.168.2.40 --backlight 80

# Run guardian daemon
python3 scripts/lg_brightness_guard.py --ip 192.168.2.40 --target 100 --interval 5
```

## Limitations

1. **macOS with SOCKS proxy (Clash)**: Scripts patch `urllib.request.getproxies` to bypass SOCKS for local TV access. Must be patched before bscpylgtv imports websockets.
2. **No system logs** — TV logging services are blocked from network access
3. **No HDR state query** — Current HDR mode cannot be read via API
4. **TV must be on** — WebSocket connection requires TV to be powered on
5. **`set_system_settings` (SSAP) is restricted** — most keys (`energySaving`, `backlight`, `brightness`, `contrast`) are rejected. Use `set_settings` (Luna) instead.
6. **`set_configs` does not work on newer WebOS** — returns True but has no effect.
