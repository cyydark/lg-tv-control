---
name: lg-tv-control
description: 通过 WebSocket API 发现并控制 LG webOS 电视。支持网络扫描、亮度控制、设置管理以及自动恢复守护进程。
license: MIT
---

# LG 电视控制

无需开发者模式或 SSH，直接通过局域网控制 LG webOS 电视。

## 快速开始

```bash
# 1. 扫描网络查找电视
python3 scripts/discover.py

# 2. 控制亮度
python3 scripts/lg_tv_control.py --ip <电视IP> --backlight 80

# 3. 运行亮度守护进程（检测到电视自动调暗时自动恢复）
python3 scripts/lg_brightness_guard.py --ip <电视IP> --target 100
```

## 安装

```bash
pip install bscpylgtv websockets
```

## 关键发现（webOS 6.0 / OLED55C1PCB）

### WebSocket (端口 3001) 可用功能
- 电源状态、音量、输入源、应用启停 ✅
- 读取画面设置 (`get_picture_settings`) ✅
- 写入画面设置 (`set_settings`) ✅
- 实时订阅 (`subscribe_picture_settings`) ✅
- `com.webos.service.oledepl` TPC/GSR（OLED 面板功耗管理）✅
- 直接 `ssap://` 调用 `settingsservice` ❌ (404)
- 系统日志访问 ❌ (被阻止)

### set_settings — 写入画面设置的主要方式
使用 `set_settings('picture', dict)` 而不是 `set_system_settings`：
```python
# 正确：内部使用 Luna 端点，可写入
await client.set_settings('picture', {'backlight': 100, 'contrast': 100})

# 无效：SSAP 端点拒绝大多数 key
await client.set_system_settings('picture', {'backlight': 100})  # ❌ 被拒绝
```
`set_settings` 返回 `True` 后电视约需 1 秒才应用更改。

### 关键发现：必须用字符串格式
所有画面参数必须传**字符串**，不能用整数：
```python
# 错误 - 会静默失败
{"backlight": 50}

# 正确
{"backlight": "50"}
```

### 配对提示：根因已找到并修复
**早期脚本**漏掉了 `await client.async_init()`，导致 `client_key` 始终为 `None`，每次连接电视都弹出配对提示。

**已修复**：所有脚本现在在 `await self.client.connect()` 前调用 `await self.client.async_init()`。存储的密钥被正确加载后，电视静默接受连接——**首次配对后不再弹出提示**。

首次配对后密钥保存在 `.lg_tv_store.db`。后续连接直接复用，不再弹出提示。

### 首次配对
首次连接时电视会显示配对提示，点"是"确认即可。密钥自动保存，后续连接无提示。

## 电视设置参考（OLED55C1, webOS 6.0）

这台电视上所有自动调暗功能均已关闭：

| 设置 | 当前值 | 说明 |
|------|--------|------|
| `energySaving` | off | |
| `motionEyeCare` | off | |
| `dynamicContrast` | off | |
| `dynamicColor` | off | |
| `ambientLightCompensation` | off | |
| `peakBrightness` | off | |
| `hdrDynamicToneMapping` | on | 可能压缩 HDR 亮度 |
| `localDimming` | medium | |
| `pictureMode` | dolbyHdrCinemaBright | 当前模式 |

### 亮度范围
- 标准范围：**0-100**
- 扩展范围：**0-255**（电视接受更高值）

## 网络发现

用端口扫描查找电视 IP：

```bash
# 扫描常见子网
for ip in 192.168.x.{1..254}; do
  nc -z -w1 "$ip" 3001 && echo "发现 LG 电视: $ip"
done
```

判断依据：端口 3000/3001 开放 = LG webOS 电视

## 文件结构

```
lg-tv-control/
├── .lg_tv_key          ← 电视配对密钥
├── .lg_tv_store.db    ← 配对凭证（SQLite）
├── scripts/
│   ├── discover.py           ← 网络扫描
│   ├── lg_tv_control.py      ← 控制命令行工具
│   └── lg_brightness_guard.py ← 自动恢复守护进程
└── docs/
    └── api_reference.md      ← 完整 API 参考
```

## 运行脚本

```bash
# 扫描电视
python3 scripts/discover.py --subnet 192.168.2

# 查看当前设置
python3 scripts/lg_tv_control.py --ip 192.168.2.40 --get

# 控制亮度
python3 scripts/lg_tv_control.py --ip 192.168.2.40 --backlight 80

# 运行亮度守护进程
python3 scripts/lg_brightness_guard.py --ip 192.168.2.40 --target 100 --interval 5
```

## 已知限制

1. **macOS + SOCKS 代理（Clash）**：脚本在 import 时 patch `urllib.request.getproxies` 以绕过本地 TV 访问的 SOCKS 代理。必须在 bscpylgtv 导入 websockets 前执行。
2. **无法访问系统日志** — 电视日志服务从网络被阻止
3. **无法查询 HDR 状态** — 当前 HDR 模式无法通过 API 读取
4. **`set_system_settings` (SSAP) 受限** — 大多数 key（`energySaving`、`backlight`、`brightness`、`contrast`）被拒绝，改用 `set_settings` (Luna)
5. **`set_configs` 在新版 WebOS 上不生效** — 返回 True 但无实际效果
6. **电视必须开机** — WebSocket 连接需要电视处于开机状态
