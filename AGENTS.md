# 🧠 Agent Instructions & Architecture

WatchWise is uniquely designed to act as a safe, predictable bridge between Large Language Models (LLMs) and local Android devices. 

Unlike traditional bash scripts that execute linearly, WatchWise forces a **planning and state-capture phase**, making it an ideal toolchain for AI agents.

## 🏗️ Core Architecture Principles

1. **Keep the Core Dependency-Free**
   The Python core relies only on the standard library (`json`, `subprocess`, `argparse`). Agents do not need to manage virtual environments or resolve complex pip dependencies to use the basic toolkit.

2. **JSON-First Output**
   Every command outputs clean, structured JSON. Agents should parse `inventory.json`, `baseline.json`, and `plan.json` programmatically rather than trying to parse raw shell `stdout`.

3. **The Two-Part Execution Gate**
   To prevent AI hallucination or "runaway execution," state-mutating commands (`apply`, `restore`) will **fail safely** (dry-run) unless both `--execute` and `--yes` are provided simultaneously. Agents must be prompted to wait for human confirmation before appending these flags.

## 🛡️ Profile & Package Rules

* **Evidence-Based:** Never add package actions to a profile without independent device/firmware evidence, a rollback plan, and tests.
* **Labeling:** User-reported device facts must be labeled as `"evidence_level": "user-reported"`; do not present them to the LLM as validated compatibility.
* **No Uninstalls:** Do not add automatic package disable or uninstall behavior. Changes must remain reversible (`pm disable-user`, not `pm uninstall`).