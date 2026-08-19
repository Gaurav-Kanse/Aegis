# RamboPy

RamboPy is an event-driven, kernel-backed system monitor and proactive OOM resource daemon for Linux written in Python. It watches RAM (cgroup v2 & meminfo), temperature (hwmon), Pressure Stall Information (PSI), CPU, Disk, Network throughput, and Battery status, then executes configurable actions: desktop notifications, graceful `SIGTERM` signals to score-ranked process hogs, or job suspensions.

---

## 🏗️ Architecture

```
Watcher Threads ── Event{Severity, Source} ──▶ Policy Engine ──▶ Action (SIGTERM / Notify)
(cgroup v2, PSI,                               (config.toml)
 hwmon, /proc)
```

---

## ⚡ Installation & Quick Start

```bash
cd /home/gaurav/Projects/SystemAnalyzer/RamboPy

# Install editable package or user script
pip install -e .
```

Alternatively, run directly with python:
```bash
python3 -m rambo_py.main --help
```

---

## 🛠️ Commands

| Command | Description |
| --- | --- |
| `rambo-py daemon` | Start the event-driven resource monitor daemon |
| `rambo-py top` | One-shot snapshot of system health and top RAM consumers |
| `rambo-py stats` | Live terminal interactive UI dashboard (Ctrl+C or 'q' to exit) |
| `rambo-py threshold status/set` | View or adjust memory/thermal/network alert thresholds |
| `rambo-py protect list/add/remove` | Manage protected applications (never killed) |
| `rambo-py oom-protect` | Privileged helper setting `oom_score_adj=-1000` |
| `rambo-py history` | Show logged events and kills |
| `rambo-py clean` | Clear logged state history |

---

## ⚙️ Configuration (`~/.config/rambo-py/config.toml`)

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

---

## 🛡️ Kill Policy & Candidate Scoring

Candidate processes are ranked using a multi-factor score:

$$\text{score} = 0.6 \cdot \text{rss}_{\text{norm}} + 0.3 \cdot \text{cpu}_{\text{norm}} + 0.1 \cdot \text{runtime}_{\text{norm}} + 0.3 (\text{interactive}) + 0.2 (\text{expendable})$$

System processes, window managers, IDEs, and protected apps are blacklisted and never targeted.

---

## ⚙️ Systemd Service Integration

```bash
mkdir -p ~/.config/systemd/user
cp systemd/rambo-py.service ~/.config/systemd/user/rambo-py.service
systemctl --user daemon-reload
systemctl --user enable --now rambo-py.service
```
