# Aegis

Aegis is an event-driven, kernel-backed system monitor and proactive resource/OOM daemon for Linux with a Nothing-inspired GTK4 & Libadwaita desktop interface. It monitors RAM (cgroup v2 & meminfo), temperature (hwmon), Pressure Stall Information (PSI), CPU, Disk, Network throughput, and Battery status, executing configurable notifications or graceful process recovery actions.

---

## 📦 Installation (Fedora RPM)

Aegis is packaged as a native Fedora RPM.

```bash
# Build the RPM package (from repository source)
./scripts/build-rpm.sh

# Install the Aegis package
sudo dnf install ./dist/aegis-0.1.0-1.fc44.noarch.rpm
```

---

## ⚡ Quick Start

After installing Aegis:

### 1. Enable & Start Systemd User Daemon
```bash
systemctl --user enable --now aegis.service
```

### 2. Launch the Aegis GTK GUI
```bash
aegis-gui
```
Or launch **Aegis** directly from your desktop Application Menu (**Applications → Aegis**).

---

## 🛠️ CLI Reference

The installed `aegis` command line tool provides complete terminal control:

| Command | Description |
| --- | --- |
| `aegis --version` | Display Aegis version information |
| `aegis --help` | Display command usage and available subcommands |
| `aegis gui` | Launch the GTK4 + Libadwaita desktop application |
| `aegis daemon` | Run the event-driven monitor daemon directly |
| `aegis top` | One-shot snapshot of system health and top RAM consumers |
| `aegis stats` | Interactive live terminal dashboard (TUI) |
| `aegis threshold status/set` | View or adjust memory/thermal/network alert thresholds |
| `aegis protect list/add/remove` | Manage protected process whitelist (never targeted) |
| `aegis oom-protect` | Privileged helper setting `oom_score_adj=-1000` |
| `aegis history` | View logged events, alerts, and kill actions |
| `aegis clean` | Clear logged state history |

---

## ⚙️ Configuration (`~/.config/aegis/config.toml`)

User configuration is automatically created at `~/.config/aegis/config.toml`:

```toml
protect = ["nvim", "gnome-shell", "code", "python3"]
expendable = ["steam"]

[memory]
soft_pct = 90
hard_pct = 96
max_pct = 99

[temperature]
warning = 85
critical = 90
action = "kill"

[network]
alert_mbps = 900
action = "notify"

[cpu]
alert_pct = 90
action = "notify"

[disk]
space_alert_pct = 90

[kill]
policy = "score"
cooldown = "30s"
max_per_min = 3
oom_prefer = true
oom_protect = true

[kill.weights]
rss = 0.6
cpu = 0.3
runtime = 0.1
```

*Note: User configuration in `~/.config/aegis/` is preserved across package updates and uninstalls.*

---

## 📁 File Locations & State

* **Configuration**: `~/.config/aegis/config.toml`
* **IPC Socket**: `~/.local/state/aegis/ipc.sock` (permissions `0600`)
* **Event History Logs**: `~/.local/state/aegis/events.json`
* **Systemd User Service**: `/usr/lib/systemd/user/aegis.service`
* **Polkit Security Rule**: `/usr/share/polkit-1/rules.d/99-aegis.rules`

---

## 📋 Systemd Service & Logs

To check daemon status:
```bash
systemctl --user status aegis.service
```

To view live journald logs:
```bash
journalctl --user -u aegis.service -f
```

---

## 🗑️ Uninstallation

To remove Aegis cleanly:
```bash
# Stop and disable user daemon
systemctl --user disable --now aegis.service

# Remove package
sudo dnf remove aegis
```
*Note: Your personal settings (`~/.config/aegis`) and state history (`~/.local/state/aegis`) are preserved.*

---

## 💻 Development & Building from Source

To run Aegis directly from the source repository:

```bash
# Run unit test suite
python3 -m unittest discover -s tests

# Run development runner
./aegis-runner top
./aegis-runner gui
```
