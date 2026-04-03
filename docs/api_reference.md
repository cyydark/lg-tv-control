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

### Via luna_request (luna:// → alert hack)

```python
from bscpylgtv import endpoints

# WARNING: Triggers TV confirmation dialog on every call
# WARNING: All values MUST be strings, not integers

await client.luna_request(
    "com.webos.settingsservice/setSystemSettings",
    {"category": "picture", "settings": {"backlight": "80"}}
)

await client.luna_request(
    "com.webos.settingsservice/setSystemSettings",
    {"category": "picture", "settings": {"brightness": "50"}}
)

await client.luna_request(
    "com.webos.settingsservice/setSystemSettings",
    {"category": "picture", "settings": {"contrast": "85"}}
)

await client.luna_request(
    "com.webos.settingsservice/setSystemSettings",
    {"category": "picture", "settings": {"pictureMode": "game"}}
)

await client.luna_request(
    "com.webos.settingsservice/setSystemSettings",
    {"category": "picture", "settings": {"energySaving": "off"}}
)

await client.luna_request(
    "com.webos.settingsservice/setSystemSettings",
    {"category": "picture", "settings": {"hdrDynamicToneMapping": "off"}}
)
```

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

- `com.webos.settingsservice` via direct `ssap://` request (404)
- System log services (blocked)
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
