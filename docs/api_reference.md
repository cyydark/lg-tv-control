# LG webOS TV API Reference

## Library: bscpylgtv

```bash
pip install bscpylgtv websockets
```

## Connection

```python
from bscpylgtv import webos_client, StorageSqliteDict

store_path = ".lg_tv_store.db"  # symlinked to ~/.lg_tv_store.db

async def connect(ip: str):
    storage = StorageSqliteDict(store_path)
    await storage.async_init()
    client = webos_client.WebOsClient(
        ip,
        storage=storage,
        without_ssl=False,
        connect_retry_attempts=3,
        timeout_connect=10,
    )
    await client.async_init()  # ← loads client_key from storage — REQUIRED
    await client.connect()
    return client
```

### First-time pairing
On first connect, a pairing request appears on the TV screen.
Accept it — the client key is saved to `lg_tv_store.db`.

## Endpoints

### Via bscpylgtv client methods (recommended)

| Method | Description |
|--------|-------------|
| `client.get_power_state()` | Returns `{"state": "Active"}` or `"Off"` |
| `client.get_picture_settings()` | Returns `{"contrast", "backlight", "brightness", "color"}` |
| `client.set_settings('picture', dict)` | Write picture settings (uses Luna, works) |
| `client.get_inputs()` | List all inputs (HDMI_1, HDMI_2, etc.) |
| `client.get_apps_all()` | List all installed apps |
| `client.get_current_app()` | Returns current app ID string |
| `client.get_audio_status()` | Volume, mute state |
| `client.get_system_info()` | Model name, firmware version |
| `client.get_software_info()` | webOS version, auth flags |
| `client.launch_app(app_id)` | Launch app by ID |
| `client.close_app(app_id)` | Close running app |
| `client.set_input(input_id)` | Switch to HDMI_1, HDMI_2, etc. |
| `client.power_off()` | Turn TV off |
| `client.send_enter_key()` | Send ENTER (IME) |
| `client.input_command("ENTER")` | Send ENTER via input socket |
| `subscribe_picture_settings(callback)` | Real-time picture settings subscription |
| `client.enable_tpc_or_gsr(algo, enable)` | Toggle TPC/GSR for OLED panel power management |

### Writing picture settings

**`set_settings('picture', dict)`** — use this, works reliably:

```python
# Write backlight (TV takes ~1 second to apply after return)
await client.set_settings('picture', {
    'backlight': 100,
    'contrast': 100,
    'brightness': 50,
    'color': 55,
})
```

**`set_system_settings(category, dict)`** — SSAP endpoint, most keys are blocked:

```python
# ❌ REJECTED: "Some keys are not allowed"
await client.set_system_settings('picture', {'backlight': 100})

# ✅ Only these work (non-picture categories)
await client.set_system_settings('option', {'audioGuidance': 'off'})
```

### Via luna_request (luna:// → alert hack)

## Picture Settings

### Values
| Setting | Range | Notes |
|---------|-------|-------|
| `backlight` | 0-255 | String required |
| `brightness` | 0-100 | String required |
| `contrast` | 0-100 | String required |
| `color` | 0-100 | String required |

### Picture Modes (OLED55C1)
```
cinema, dolbyHdrCinema, dolbyHdrCinemaBright, dolbyHdrDarkAmazon,
dolbyHdrGame, dolbyHdrStandard, dolbyHdrVivid, dolbyStandard,
eco, expert1, expert2, filmMaker, game, hdrCinema, hdrCinemaBright,
hdrExternal, hdrFilmMaker, hdrGame, hdrStandard, hdrVivid,
normal, photo, sports, vivid
```

### Energy Saving
```
off, min, medium, max, screen_off
```

### Inputs
```
atv, av1, av2, camera, comp1, comp2, comp3, default, dtv,
gallery, hdmi1, hdmi1_pc, hdmi2, hdmi2_pc, hdmi3, hdmi3_pc,
hdmi4, hdmi4_pc, ip, movie, photo, pictest, rgb, scart, smhl
```

## Known App IDs (OLED55C1)

| App | ID |
|-----|-----|
| Settings | `com.palm.app.settings` |
| HDMI 2 | `com.webos.app.hdmi2` |
| HDMI 1 | `com.webos.app.hdmi1` |
| YouTube | `youtube.leanback.v4` |

## What Does NOT Work

- `set_system_settings` (SSAP) with picture keys — rejects `backlight`, `brightness`, `contrast`, `energySaving`
- `set_configs` — returns True but has no effect on newer WebOS (see bscpylgtv source note)
- `com.webos.settingsservice` via direct `ssap://` request (404)
- System log services (blocked)
- `set_oled_light`, `set_brightness` — driver error, not supported on this model
- Subscriptions for energy saving changes
- No TV confirmation dialogs when paired (credentials in `.lg_tv_store.db` suppress all dialogs)

## Useful bscpylgtv Endpoints

```python
from bscpylgtv import endpoints

endpoints.LUNA_SET_SYSTEM_SETTINGS  # "com.webos.settingsservice/setSystemSettings"
endpoints.GET_SYSTEM_SETTINGS        # "settings/getSystemSettings" (read-only)
endpoints.SEND_ENTER                # "com.webos.service.ime/sendEnterKey"
endpoints.INPUT_SOCKET              # dynamically resolved
```
