"""Spoolman discovery: HTTP probe + LAN /24 sweep on port 7912.

The Snapmaker Buildroot rootfs has no mDNS resolver (no Avahi /
``nss-mdns``), so ``spoolman.local`` cannot be looked up. We use a TCP
sweep over the local /24 instead, then HTTP-confirm any open host actually
serves the Spoolman API.
"""

import socket
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def probe_spoolman(url):
    """Return True if a Spoolman instance responds at the given base URL."""
    try:
        req = urllib.request.Request(
            url.rstrip('/') + '/api/v1/info', method='GET'
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _local_ipv4_for_default_route():
    """Return this host's primary outbound IPv4 address.

    Uses the connect()-on-UDP trick: no traffic is sent, but the kernel
    chooses the source address it would use to reach the public IP, which
    is the address bound to the default-route interface.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 1))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return None


def _probe_tcp(ip, port, timeout):
    """Return True if a TCP connection to (ip, port) succeeds within timeout."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        return True
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def lan_sweep_for_spoolman(port=7912, connect_timeout=0.3, max_workers=32):
    """Scan the local /24 for hosts answering on ``port``, then HTTP-probe
    each candidate to confirm it is a real Spoolman instance.

    Returns a list of base URLs (e.g. ``http://192.168.2.30:7912``) ordered
    by response order. Returns ``[]`` if the host has no usable IPv4
    address or no Spoolman instance is found.
    """
    local_ip = _local_ipv4_for_default_route()
    if not local_ip:
        return []
    parts = local_ip.split('.')
    if len(parts) != 4:
        return []
    prefix = '.'.join(parts[:3]) + '.'

    targets = [prefix + str(i) for i in range(1, 255) if (prefix + str(i)) != local_ip]

    open_hosts = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_probe_tcp, ip, port, connect_timeout): ip for ip in targets}
        for fut in as_completed(futures):
            try:
                if fut.result():
                    open_hosts.append(futures[fut])
            except Exception:
                pass

    found = []
    for ip in open_hosts:
        url = "http://{}:{}".format(ip, port)
        if probe_spoolman(url):
            found.append(url)
    return found
