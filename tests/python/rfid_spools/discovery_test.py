"""Tests for ``rfid_spools.discovery``."""

import socket
from unittest.mock import MagicMock, patch

from rfid_spools import discovery


# ── probe_spoolman ───────────────────────────────────────────────────────────
class TestProbeSpoolman:
    def test_returns_true_on_2xx(self):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch.object(discovery.urllib.request, 'urlopen', return_value=mock_resp):
            assert discovery.probe_spoolman('http://x:7912') is True

    def test_returns_false_on_4xx(self):
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch.object(discovery.urllib.request, 'urlopen', return_value=mock_resp):
            assert discovery.probe_spoolman('http://x:7912') is False

    def test_returns_false_on_timeout(self):
        with patch.object(discovery.urllib.request, 'urlopen',
                          side_effect=socket.timeout('timed out')):
            assert discovery.probe_spoolman('http://x:7912') is False

    def test_returns_false_on_url_error(self):
        with patch.object(discovery.urllib.request, 'urlopen',
                          side_effect=discovery.urllib.error.URLError('refused')):
            assert discovery.probe_spoolman('http://x:7912') is False

    def test_strips_trailing_slash_in_url(self):
        captured = {}

        def fake_urlopen(req, timeout):
            captured['url'] = req.full_url
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        with patch.object(discovery.urllib.request, 'urlopen', side_effect=fake_urlopen):
            discovery.probe_spoolman('http://x:7912/')
        assert captured['url'] == 'http://x:7912/api/v1/info'


# ── _probe_tcp ───────────────────────────────────────────────────────────────
class TestProbeTcp:
    def test_returns_true_on_open(self):
        sock = MagicMock()
        sock.connect = MagicMock()  # success
        with patch.object(discovery.socket, 'socket', return_value=sock):
            assert discovery._probe_tcp('1.2.3.4', 7912, 0.1) is True
        sock.close.assert_called()

    def test_returns_false_on_refused(self):
        sock = MagicMock()
        sock.connect.side_effect = ConnectionRefusedError()
        with patch.object(discovery.socket, 'socket', return_value=sock):
            assert discovery._probe_tcp('1.2.3.4', 7912, 0.1) is False
        sock.close.assert_called()

    def test_returns_false_on_timeout(self):
        sock = MagicMock()
        sock.connect.side_effect = socket.timeout()
        with patch.object(discovery.socket, 'socket', return_value=sock):
            assert discovery._probe_tcp('1.2.3.4', 7912, 0.1) is False


# ── lan_sweep_for_spoolman ───────────────────────────────────────────────────
class TestLanSweep:
    def test_returns_empty_when_no_local_ipv4(self):
        with patch.object(discovery, '_local_ipv4_for_default_route',
                          return_value=None):
            assert discovery.lan_sweep_for_spoolman() == []

    def test_returns_empty_for_malformed_ip(self):
        with patch.object(discovery, '_local_ipv4_for_default_route',
                          return_value='not.an.ip'):
            assert discovery.lan_sweep_for_spoolman() == []

    def test_skips_self_and_returns_only_http_confirmed(self):
        # Only 192.168.1.30 has Spoolman; 192.168.1.99 has port open but no API.
        def fake_probe_tcp(ip, port, timeout):
            return ip in ('192.168.1.30', '192.168.1.99')

        def fake_probe_http(url):
            return url == 'http://192.168.1.30:7912'

        with patch.object(discovery, '_local_ipv4_for_default_route',
                          return_value='192.168.1.10'), \
             patch.object(discovery, '_probe_tcp', side_effect=fake_probe_tcp), \
             patch.object(discovery, 'probe_spoolman', side_effect=fake_probe_http):
            result = discovery.lan_sweep_for_spoolman()
        assert result == ['http://192.168.1.30:7912']
