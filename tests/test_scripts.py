"""Unit tests for lg-tv-control scripts."""
import subprocess
from unittest.mock import patch, MagicMock, AsyncMock, call

import pytest

# Ensure discover module is importable
import sys
sys.path.insert(0, "scripts")


class TestDiscover:
    """Tests for scripts/discover.py."""

    def test_check_port_success(self):
        """nc returns 0 → port is open."""
        from discover import check_port

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            found, ip, port = check_port("192.168.2.40", 3001)

            assert found is True
            assert ip == "192.168.2.40"
            assert port == 3001
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args == ["nc", "-z", "-w1", "192.168.2.40", "3001"]

    def test_check_port_failure(self):
        """nc returns non-zero → port is closed."""
        from discover import check_port

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            found, ip, port = check_port("192.168.2.99", 3001)

            assert found is False
            assert ip == "192.168.2.99"

    def test_check_port_timeout(self):
        """nc times out → treat as closed."""
        from discover import check_port

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("nc", 1)
            found, ip, port = check_port("192.168.2.1", 3000)

            assert found is False

    def test_scan_subnet_finds_tv(self):
        """scan_subnet returns matching IPs."""
        from discover import scan_subnet

        call_count = [0]

        def fake_check_port(ip, port):
            call_count[0] += 1
            # Only .10 and .20 are "open"
            return ip.endswith(".10") or ip.endswith(".20"), ip, port

        with patch("discover.check_port", side_effect=fake_check_port):
            results = scan_subnet("192.168.2", ports=[3001])

        assert len(results) == 2
        assert ("192.168.2.10", 3001) in results
        assert ("192.168.2.20", 3001) in results

    def test_scan_subnet_none_found(self):
        """All ports closed → empty results."""
        from discover import scan_subnet

        with patch("discover.check_port", return_value=(False, "", 0)):
            results = scan_subnet("192.168.2", ports=[3001])

        assert results == []


class TestBrightnessGuardianInit:
    """Tests for BrightnessGuardian.__init__."""

    def test_init_requires_ip(self):
        """ip is a required positional argument."""
        from lg_brightness_guard import BrightnessGuardian

        guardian = BrightnessGuardian(ip="192.168.2.40")
        assert guardian.ip == "192.168.2.40"

    def test_init_defaults(self):
        """Default values are applied."""
        from lg_brightness_guard import BrightnessGuardian

        guardian = BrightnessGuardian(ip="192.168.2.40", target=80, poll=10, threshold=5)
        assert guardian.target == 80
        assert guardian.poll == 10
        assert guardian.threshold == 5
        assert guardian.last_backlight is None
        assert guardian.client is None
        assert guardian.is_running is False

    def test_restore_backlight_uses_set_settings(self):
        """restore_backlight calls client.set_settings, not luna_request."""
        from lg_brightness_guard import BrightnessGuardian
        import asyncio

        guardian = BrightnessGuardian(ip="192.168.2.40", target=100)
        mock_client = AsyncMock()
        guardian.client = mock_client

        async def run():
            await guardian.restore_backlight()

        asyncio.run(run())

        mock_client.set_settings.assert_called_once_with(
            "picture", {"backlight": "100"}
        )
        # Must NOT use luna_request
        mock_client.luna_request.assert_not_called()


class TestLgTvControllerSetters:
    """Tests for LgTvController set_* methods."""

    def test_set_backlight_uses_set_settings(self):
        """set_backlight calls client.set_settings with clamped int."""
        from lg_tv_control import LgTvController
        import asyncio

        ctrl = LgTvController("192.168.2.40")
        mock_client = AsyncMock()
        ctrl.client = mock_client

        async def run():
            # Test clamping: 300 → 255
            await ctrl.set_backlight(300)
            await ctrl.set_backlight(-5)   # → 0
            await ctrl.set_backlight(80)   # unchanged

        asyncio.run(run())

        # Check all 3 calls individually
        all_calls = mock_client.set_settings.call_args_list
        assert all_calls[0] == call("picture", {"backlight": "255"})
        assert all_calls[1] == call("picture", {"backlight": "0"})
        assert all_calls[2] == call("picture", {"backlight": "80"})

    def test_set_brightness_clamped(self):
        """set_brightness clamps to 0-100."""
        from lg_tv_control import LgTvController
        import asyncio

        ctrl = LgTvController("192.168.2.40")
        mock_client = AsyncMock()
        ctrl.client = mock_client

        async def run():
            await ctrl.set_brightness(150)

        asyncio.run(run())

        # 150 → 100 (clamped)
        mock_client.set_settings.assert_called_once_with(
            "picture", {"brightness": "100"}
        )

    def test_set_picture_mode_string(self):
        """set_picture_mode passes mode string as-is."""
        from lg_tv_control import LgTvController
        import asyncio

        ctrl = LgTvController("192.168.2.40")
        mock_client = AsyncMock()
        ctrl.client = mock_client

        async def run():
            await ctrl.set_picture_mode("hdrGame")

        asyncio.run(run())

        mock_client.set_settings.assert_called_once_with(
            "picture", {"pictureMode": "hdrGame"}
        )
