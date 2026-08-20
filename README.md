# Aegis

**Aegis** is an event-driven, kernel-backed system monitor, proactive Out-Of-Memory (OOM) daemon, and native Linux desktop application written in Python, GTK4, and Libadwaita.

Featuring a Nothing-inspired monochrome interface, Aegis continuously monitors RAM (cgroup v2 & `/proc/meminfo`), Pressure Stall Information (PSI), CPU utilization, thermal sensors (hwmon), disk usage, network throughput, and battery status. It provides real-time telemetry, whitelist process protection, configurable alerts, desktop notifications, and proactive process recovery before kernel OOM lockups occur.

---

## Highlights

* **Proactive Resource Recovery**: Calculates multi-factor candidate scores ($\text{RSS} + \text{CPU} + \text{Runtime}$) to rank RAM hogs and take action before system freezes.
* **Whitelist & Priority Protection**: Built-in whitelist protection for critical apps (`gnome-shell`, `nvim`, `code`, `python3`) and custom priority adjustments (`oom_score_adj`).
* **Nothing-Inspired UI**: Dark monochrome GTK4 & Libadwaita GUI featuring Cairo health ring gauges, telemetry trend lines with threshold alerts, and high-density process tables.
* **Unix Socket IPC**: Non-blocking JSON-RPC socket server (`~/.local/state/aegis/ipc.sock`) for decoupled GUI and daemon communication.
* **Native Linux Integration**: Systemd user service (`aegis.service`), Polkit authorization rules, Desktop AppStream launcher, and journald log integration.
* **Fedora RPM Packaged**: Fully compliant Fedora RPM packaging built using standard RPM macros.

---

## Architecture

```
                       AEGIS SYSTEM MONITOR
                                 │
           ┌─────────────────────┴─────────────────────┐
           │                                           │
     Aegis Daemon                                Aegis GTK GUI
  (Watchers & Engine)                          (GTK4 + Libadwaita)
           │                                           │
           └─────────────────────┬─────────────────────┘
                                 │
                         Unix Socket IPC
                          (JSON-RPC)
                                 │
                                 ▼
                     Linux Kernel Subsystems
                   (cgroups v2, PSI, hwmon, /proc)
```

---

## Installation (Fedora RPM)

Aegis is distributed as a native Fedora RPM package.

### Build from Source
```bash
# Build the RPM package and SHA256 checksums
./scripts/build-rpm.sh
```

### Install RPM Package
```bash
sudo dnf install ./dist/aegis-0.1.0-1.fc44.noarch.rpm
```

---

## Quick Start

After installing Aegis:

### 1. Enable & Start System Daemon
Enable the systemd user service so Aegis starts automatically on login:
```bash
systemctl --user enable --now aegis.service
```

### 2. Launch Desktop Interface
Launch the GTK4 GUI from the terminal:
```bash
aegis-gui
```
Or open **Aegis** from your desktop launcher (**Applications → System → Aegis**).

---

## Desktop Interface Pages

The Aegis GUI is divided into six specialized views:

* **System Overview**: Centralized health ring gauge, subsystem status badges, summary metric cards, top RAM consumers, recent events timeline, and live resource graph.
* **Processes**: Real-time process manager with instant search, multi-field sorting (Score, CPU, RAM, Runtime), whitelist protection toggles, and terminate controls.
* **Analytics**: Time-series telemetry graphs (`5m`, `30m`, `1h`) with metric tabs (CPU, RAM, Temp, Disk, Network, PSI), numerical Y-axis scales, X-axis time markers, and 90% alert threshold indicators.
* **Event Log**: Live audit trail of system alerts, resource warnings, and kill actions with search filtering and severity classification (`INFO`, `WARNING`, `CRITICAL`).
* **Protection & Policy**: Manage `Protected` (never targeted) and `Expendable` (OOM priority) whitelist process rules with real-time conflict handling.
* **Settings**: Preference panel for adjusting runtime memory thresholds, thermal kill limits, network/disk alerts, and kill policy parameters with atomic configuration persistence.

---

## CLI Reference

The installed `aegis` command line tool provides terminal management:

| Command | Description |
| --- | --- |
| `aegis --version` | Display Aegis version information (`aegis 0.1.0`) |
| `aegis --help` | Show command usage and available subcommands |
| `aegis gui` | Launch the GTK4 + Libadwaita desktop interface |
| `aegis daemon` | Run the event-driven monitor daemon directly |
| `aegis top` | One-shot snapshot of system health & top RAM consumers |
| `aegis stats` | Terminal interactive live monitoring dashboard (TUI) |
| `aegis threshold status` | View active memory, thermal, CPU, and network thresholds |
| `aegis threshold set` | Update memory, thermal, or alert limits from terminal |
| `aegis protect list` | List processes in the protection whitelist |
| `aegis protect add --name <app>` | Add process binary name to protection whitelist |
| `aegis protect remove --name <app>` | Remove process binary name from protection whitelist |
| `aegis oom-protect` | Privileged helper setting `oom_score_adj=-1000` |
| `aegis history [-n count]` | View logged system events and kill audit entries |
| `aegis clean` | Clear logged state history |

---

## Configuration (`~/.config/aegis/config.toml`)

User preferences are loaded from `~/.config/aegis/config.toml`:

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

*User configuration in `~/.config/aegis/` is preserved during upgrades and package uninstalls.*

---

## Candidate Scoring Engine

When memory pressure crosses hard limits, target candidates are selected using a multi-factor score:

$$\text{Score} = 0.6 \cdot \text{RSS}_{\text{norm}} + 0.3 \cdot \text{CPU}_{\text{norm}} + 0.1 \cdot \text{Runtime}_{\text{norm}} + 0.3 (\text{Interactive}) + 0.2 (\text{Expendable})$$

System processes, display managers (`gnome-shell`, `wayland`), IDEs, and user-protected whitelist binaries are blacklisted and never targeted.

---

## System Files & State Directories

* **User Configuration**: `~/.config/aegis/config.toml`
* **IPC Socket**: `~/.local/state/aegis/ipc.sock` (mode `0600`)
* **Event Log History**: `~/.local/state/aegis/events.json`
* **Systemd User Unit**: `/usr/lib/systemd/user/aegis.service`
* **Desktop Launcher**: `/usr/share/applications/org.aegis.Aegis.desktop`
* **AppStream Metadata**: `/usr/share/metainfo/org.aegis.Aegis.metainfo.xml`
* **Scalable Icon**: `/usr/share/icons/hicolor/scalable/apps/aegis.svg`
* **Polkit Security Rule**: `/usr/share/polkit-1/rules.d/99-aegis.rules`

---

## Service Control & Journal Logs

Check user service status:
```bash
systemctl --user status aegis.service
```

Stream live daemon logs:
```bash
journalctl --user -u aegis.service -f
```

---

## Uninstallation

To cleanly remove Aegis while retaining personal settings:

```bash
# Stop and disable systemd user daemon
systemctl --user disable --now aegis.service

# Remove RPM package
sudo dnf remove aegis
```

---

## Development & Source Testing

To run Aegis directly from the source repository:

```bash
# Run unit test suite
python3 -m unittest discover -s tests

# Run development runner
./aegis-runner top
./aegis-runner gui
```

---

## License

Distributed under the [MIT License](LICENSE). Copyright (c) 2026 Gaurav.
