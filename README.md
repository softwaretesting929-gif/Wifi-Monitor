# Wifi-Monitor
Wifi Network Monitoring and Control 

🔹 Main Features
List Network Interfaces (ifaces)

Displays all available network interfaces on the system (e.g., wlan0, eth0, en0, Wi-Fi).

Monitor Network Usage (monitor)

Monitors a specific network interface in real time.

Shows:

Total data usage (download + upload)

Instantaneous speed (Download/s, Upload/s)

Uses a human-readable format like KB, MB, GB.

Wi‑Fi Power Control (wifi on/off)

Turns Wi‑Fi on or off depending on the operating system:

Linux → Uses nmcli or ip link set

Windows → Uses netsh interface

macOS → Uses networksetup

Example:

bash
python3 wifi_tool.py wifi off
Monitor Mode Control (Linux only)

Enables or disables monitor mode on Wi‑Fi adapters (useful for sniffing/packet capture).

Example:

bash
python3 wifi_tool.py monitor-mode enable --iface wlan0
🔹 Example Usage
bash
python3 wifi_tool.py ifaces                   # List interfaces
python3 wifi_tool.py monitor --iface wlan0    # Monitor data usage
python3 wifi_tool.py wifi off                 # Turn off Wi-Fi
python3 wifi_tool.py wifi on --iface "Wi-Fi"  # Turn on Wi-Fi
python3 wifi_tool.py monitor-mode enable --iface wlan0  # Enable monitor mode
