#!/usr/bin/env python3
import argparse
import platform
import subprocess
import sys
import time
from datetime import datetime

try:
    import psutil
except ImportError:
    print("psutil not installed. Install with: pip install psutil", file=sys.stderr)
    sys.exit(1)

def human_bytes(n):
    # Convert bytes to human readable string
    sizes = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    f = float(n)
    while f >= 1024 and i < len(sizes) - 1:
        f /= 1024.0
        i += 1
    return f"{f:.2f} {sizes[i]}"

def list_interfaces():
    counters = psutil.net_io_counters(pernic=True)
    return list(counters.keys())

def get_iface_counters(iface):
    counters = psutil.net_io_counters(pernic=True)
    if iface not in counters:
        raise ValueError(f"Interface '{iface}' not found. Available: {', '.join(counters.keys())}")
    c = counters[iface]
    return c.bytes_recv, c.bytes_sent

def detect_wifi_like_interfaces():
    names = list_interfaces()
    # Common Wi-Fi name patterns: Linux "wlan0" / "wlp*" / "wlo*", macOS "en0"/"en1", Windows "Wi-Fi"
    candidates = []
    for n in names:
        ln = n.lower()
        if ln.startswith("wl") or ln.startswith("wlan") or ln in ("en0", "en1") or "wi-fi" in ln or "wifi" in ln:
            candidates.append(n)
    return candidates or names  # fallback to all if none matches

def monitor_interface(iface, interval=1.0):
    # Live monitor: total and instantaneous speed
    try:
        prev_rx, prev_tx = get_iface_counters(iface)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)

    print(f"Monitoring interface: {iface} (Ctrl+C to stop)")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 72)
    print(f"{'Elapsed':>8}  {'RX total':>12}  {'TX total':>12}  {'Down/s':>10}  {'Up/s':>10}")
    print("-" * 72)

    start = time.time()
    try:
        while True:
            time.sleep(interval)
            cur_rx, cur_tx = get_iface_counters(iface)
            d_rx = cur_rx - prev_rx
            d_tx = cur_tx - prev_tx
            prev_rx, prev_tx = cur_rx, cur_tx
            elapsed = time.time() - start
            down_s = d_rx / interval
            up_s = d_tx / interval
            print(f"{int(elapsed):>8}s  {human_bytes(cur_rx):>12}  {human_bytes(cur_tx):>12}  {human_bytes(down_s)+'/s':>10}  {human_bytes(up_s)+'/s':>10}")
    except KeyboardInterrupt:
        print("\nStopped.")

def run_cmd(cmd):
    # Helper to run a system command and return (rc, out, err)
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()

def wifi_power(state: str, iface_hint: str = None):
    """
    Turn Wi-Fi radio on/off depending on OS.
    state: 'on' or 'off'
    iface_hint: optional interface name (used on macOS), otherwise attempts common defaults.
    """
    osname = platform.system().lower()
    state = state.lower()
    if state not in ("on", "off"):
        raise ValueError("state must be 'on' or 'off'")

    if "linux" in osname:
        # Use NetworkManager CLI if available
        rc, out, err = run_cmd(f"nmcli radio wifi {state}")
        if rc == 0:
            print(out or f"Wi-Fi {state}")
            return
        # Fallback: ip link down/up on a Wi-Fi interface
        iface = iface_hint or (detect_wifi_like_interfaces() if detect_wifi_like_interfaces() else None)
        if not iface:
            print("Could not determine Wi-Fi interface for fallback.", file=sys.stderr)
            sys.exit(3)
        cmd = f"sudo ip link set {iface} {'up' if state=='on' else 'down'}"
        print(f"nmcli failed, falling back to: {cmd}")
        rc, out, err = run_cmd(cmd)
        if rc != 0:
            print(err or "Failed to toggle Wi‑Fi", file=sys.stderr)
            sys.exit(4)
        print(out or f"Interface {iface} {'up' if state=='on' else 'down'}")

    elif "windows" in osname:
        # Interface commonly named "Wi-Fi"
        iface = iface_hint or "Wi-Fi"
        cmd = f'netsh interface set interface "{iface}" admin={"enable" if state=="on" else "disable"}'
        rc, out, err = run_cmd(cmd)
        if rc != 0:
            print(err or "Failed to toggle Wi‑Fi")
            sys.exit(5)
        print(out or f"Wi‑Fi {state}")

    elif "darwin" in osname or "mac" in osname:
        # macOS Wi‑Fi often en0; use networksetup
        iface = iface_hint or "en0"
        cmd = f'/usr/sbin/networksetup -setairportpower {iface} {"on" if state=="on" else "off"}'
        rc, out, err = run_cmd(cmd)
        if rc != 0:
            print(err or "Failed to toggle Wi‑Fi", file=sys.stderr)
            sys.exit(6)
        print(out or f"Wi‑Fi {state} on {iface}")
    else:
        print(f"Unsupported OS: {platform.system()}", file=sys.stderr)
        sys.exit(7)

def linux_monitor_mode_enable(iface):
    """
    OPTIONAL: enable monitor mode on Linux for 802.11 sniffing.
    Requires compatible adapter and root.
    """
    cmds = [
        f"sudo ip link set {iface} down",
        f"sudo iw dev {iface} set type monitor",
        f"sudo ip link set {iface} up",
    ]
    for c in cmds:
        rc, out, err = run_cmd(c)
        if rc != 0:
            print(f"Failed: {c}\n{err}", file=sys.stderr)
            sys.exit(8)
    print(f"Monitor mode requested on {iface}. Verify with: iw dev {iface} info")

def linux_monitor_mode_disable(iface):
    cmds = [
        f"sudo ip link set {iface} down",
        f"sudo iw dev {iface} set type managed",
        f"sudo ip link set {iface} up",
    ]
    for c in cmds:
        rc, out, err = run_cmd(c)
        if rc != 0:
            print(f"Failed: {c}\n{err}", file=sys.stderr)
            sys.exit(9)
    print(f"Managed mode restored on {iface}.")

def main():
    parser = argparse.ArgumentParser(description="Wi‑Fi data usage monitor and Wi‑Fi control")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("ifaces", help="List network interfaces")
    p_list.set_defaults(func=lambda args: print("\n".join(list_interfaces())))

    p_mon = sub.add_parser("monitor", help="Monitor interface usage")
    p_mon.add_argument("--iface", help="Interface name (e.g., wlo1, wlan0, en0, Wi-Fi)")
    p_mon.add_argument("--interval", type=float, default=1.0, help="Refresh interval seconds")
    def do_monitor(args):
        iface = args.iface or (detect_wifi_like_interfaces() if detect_wifi_like_interfaces() else None)
        if not iface:
            print("No interfaces found.", file=sys.stderr)
            sys.exit(10)
        monitor_interface(iface, args.interval)
    p_mon.set_defaults(func=do_monitor)

    p_wifi = sub.add_parser("wifi", help="Turn Wi‑Fi on/off")
    p_wifi.add_argument("state", choices=["on", "off"], help="Wi‑Fi radio state")
    p_wifi.add_argument("--iface", help="Interface hint (macOS/Windows name or Linux device)")
    p_wifi.set_defaults(func=lambda args: wifi_power(args.state, args.iface))

    p_monmode = sub.add_parser("monitor-mode", help="Linux only: set/unset monitor mode")
    p_monmode.add_argument("action", choices=["enable", "disable"], help="Enable/disable monitor mode")
    p_monmode.add_argument("--iface", required=True, help="Wireless interface (e.g., wlan0, wlp3s0)")
    def do_monmode(args):
        if platform.system().lower() != "linux":
            print("Monitor mode helper is Linux-only.", file=sys.stderr)
            sys.exit(11)
        if args.action == "enable":
            linux_monitor_mode_enable(args.iface)
        else:
            linux_monitor_mode_disable(args.iface)
    p_monmode.set_defaults(func=do_monmode)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
