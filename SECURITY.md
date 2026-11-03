# 🛡️ Security Policy

## Supported Versions

Currently, only the `main` branch of WatchWise is supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| v0.1.x  | :white_check_mark: |
| Older   | :x:                |

## 🚨 Reporting a Vulnerability

Because WatchWise interacts directly with device system states via ADB, security and safety are our highest priorities.

**Please DO NOT publish the following in public GitHub Issues:**
* Watch hardware identifiers (IMEI, MAC addresses, Serial Numbers).
* ADB pairing details or local IP addresses.
* Private, full device inventories.

**How to Report:**
If you discover a vulnerability or experience unexpected/unsafe behavior (e.g., a command bypassing the dry-run gate, or a core package being disabled), please report it privately to the maintainers once a direct contact channel is published. 

Until a dedicated email is set up, avoid running unreviewed plans. If you must discuss a bug publicly, please **redact your command output** to obscure personal identifiers and limit the text to the specific package or error in question.