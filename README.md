# ⌚ WatchWise

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**WatchWise** is a conservative, AI-agent-friendly toolkit for understanding and maintaining Wear OS watches over ADB. 

WatchWise is built around **explicit consent, device profiles, transactional backups, and absolute reversibility.**

> **Status:** Public-ready foundation.  
> ⚠️ *Note: This is not an aggressive debloater. It does not automatically disable, uninstall, root, or flash anything without your explicit, reviewed consent.*

---

## ✨ Key Features

*   **🔒 Safety First:** All commands default to read-only or dry-run. Changes require explicit `--execute --yes` flags.
*   **🤖 AI-Agent Friendly:** Outputs pure JSON and enforces a two-part execution gate, making it perfectly safe to hand over to a local AI assistant.
*   **🔄 Fully Reversible:** Creates a transactional state backup (`backup.json`) *before* applying any changes, ensuring you can always restore to your previous state.
*   **🛡️ Core Protection:** Hardcoded safeguards prevent disabling critical `android`, `com.google.`, or `com.samsung.` system packages.

---

## 🚀 Quick Start (Windows)

### 1. Automated Setup (Recommended for AI Agents & Users)
Run the automated setup script to install Python 3.10+ and Android Platform Tools (`adb`) via Windows Package Manager (`winget`):

```powershell
.\setup.ps1
```

### 2. Manual Setup
If you prefer, install [Python 3.10+](https://www.python.org/downloads/) and [Android Platform Tools](https://developer.android.com/studio/command-line/adb) manually. Ensure `adb` is in your system PATH.

### 3. Connect Your Watch
1. Enable **Developer Options** on your watch (Tap "Build number" 7 times in Settings > System > About).
2. Enable **ADB Debugging** and **Wireless Debugging**.
3. Connect via terminal: `adb connect <WATCH_IP>:<PORT>`

### 4. The WatchWise Workflow
Run these commands in order to safely discover, plan, and apply changes:

```powershell
# 1. Discover devices
./scripts/watchwise.ps1 discover

# 2. Capture current state
./scripts/watchwise.ps1 inventory --output inventory.json
./scripts/watchwise.ps1 baseline --output baseline.json

# 3. Generate a reviewable plan using a profile
./scripts/watchwise.ps1 plan --inventory inventory.json --profile profiles/galaxy-watch4-sm-r870.json --output plan.json

# 4. Preview the plan (Dry-Run)
./scripts/watchwise.ps1 apply --plan plan.json --backup backup.json

# 5. EXECUTE the plan (Requires both flags, saves backup first)
./scripts/watchwise.ps1 apply --plan plan.json --backup backup.json --execute --yes
```

---

## 🧰 Command Reference

| Command | Description |
| :--- | :--- |
| `discover` | Lists connected ADB devices. |
| `inventory` | Collects all currently installed packages on the device. |
| `baseline` | Captures disk space and memory usage metrics. |
| `plan` | Produces a `plan.json` showing actions to take based on the inventory and profile. |
| `agent-plan`| Allows an AI to dynamically request package disables against the safety net. |
| `apply` | **Dry-run by default.** Applies the plan and generates a backup. |
| `restore` | **Dry-run by default.** Reverts changes using a previously generated `backup.json`. |
| `verify` | Checks the current device state against a recorded backup. |

---

## 📱 Device Profiles

WatchWise relies on JSON profiles to determine what is safe to modify. 
*   `profiles/galaxy-watch4-sm-r870.json` is provided as a **reference profile**, not independently validated support. 
*   Package rules are intentionally empty until independently tested on documented firmware builds. WatchWise will not recommend disabling a package merely because it is present in an inventory.

## 📚 Documentation
*   🤖 **[AI Agent Prompt](PROMPT.md)** - System prompt for handing this tool to an AI.
*   🧠 **[Agent Architecture](AGENTS.md)** - How WatchWise interacts with LLMs.
*   🤝 **[Contributing](CONTRIBUTING.md)** - Guidelines for creating profiles and testing.
*   🛡️ **[Security Policy](SECURITY.md)** - How to report unsafe behavior.