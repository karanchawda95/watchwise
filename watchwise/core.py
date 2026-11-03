import json
from datetime import datetime, timezone
from pathlib import Path

CORE_PREFIXES = ("com.android.", "com.google.android.", "com.samsung.android.")
ALWAYS_PROTECTED = {"android"}


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def is_core(package):
    """Namespaces that hold the watch UI, radio stack, GMS and the vendor layer."""
    return package in ALWAYS_PROTECTED or package.startswith(CORE_PREFIXES)


def evidence_backed(rule):
    """A core-namespace action is only allowed with documented evidence and a real rollback."""
    return bool(str(rule.get("evidence", "")).strip()) and rule.get("rollback") == "enable"


def _parse_df(raw):
    """Parse `df /data` output into a structured dict (keys are in 1K blocks)."""
    lines = [l for l in raw.strip().splitlines() if l and not l.startswith("Filesystem")]
    if not lines:
        return {}
    parts = lines[0].split()
    keys = ["filesystem", "size_1k", "used_1k", "available_1k", "use_pct", "mounted_on"]
    return dict(zip(keys, parts))


def _parse_meminfo(raw):
    """Parse /proc/meminfo into a flat dict of {key: value_string} pairs."""
    result = {}
    for line in raw.strip().splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            result[k.strip()] = v.strip()
    return result


def inventory(adb):
    return {
        "captured_at": now(),
        "packages": sorted(filter(None, adb.shell("pm", "list", "packages").replace("package:", "").splitlines())),
    }


def baseline(adb):
    """Capture structured disk and memory metrics. All fields are parsed into dicts, not raw text."""
    return {
        "captured_at": now(),
        "disk": _parse_df(adb.shell("df", "/data")),
        "memory": _parse_meminfo(adb.shell("cat", "/proc/meminfo")),
    }


def make_plan(inv, profile):
    present = set(inv.get("packages", []))
    protected = set(profile.get("protected_packages", []))
    actions, rejected = [], []
    for rule in profile["package_rules"]:
        package = rule["package"]
        if package not in present:
            rejected.append({"package": package, "reason": "not installed on this device"})
        elif package in ALWAYS_PROTECTED or package in protected:
            rejected.append({"package": package, "reason": "protected package"})
        elif rule.get("action") != "disable-user":
            rejected.append({"package": package, "reason": "unsupported action"})
        elif is_core(package) and not evidence_backed(rule):
            rejected.append({"package": package, "reason": "core namespace requires evidence and an enable rollback"})
        else:
            actions.append(rule)
    return {
        "created_at": now(),
        "profile": profile["id"],
        "dry_run": True,
        "protected_packages": sorted(protected),
        "inventory_packages": sorted(present),
        "actions": actions,
        "rejected": rejected,
    }


def ensure_safe_plan(plan):
    known = set(plan.get("inventory_packages", []))
    protected = set(plan.get("protected_packages", []))
    for action in plan.get("actions", []):
        package = action.get("package", "")
        if action.get("action") != "disable-user":
            raise ValueError("Plan contains protected, unknown, or unsupported action")
        if package not in known or package in ALWAYS_PROTECTED or package in protected:
            raise ValueError("Plan contains protected, unknown, or unsupported action")
        if is_core(package) and not evidence_backed(action):
            raise ValueError("Plan contains protected, unknown, or unsupported action")


def create_backup(adb, plan):
    """Capture rollback-relevant state before changes; caller must persist this first."""
    ensure_safe_plan(plan)
    disabled = set(adb.shell("pm", "list", "packages", "-d").replace("package:", "").splitlines())
    return {
        "created_at": now(),
        "actions": plan["actions"],
        "state": [{"package": a["package"], "was_disabled": a["package"] in disabled} for a in plan["actions"]],
    }


def apply(adb, plan, execute=False):
    ensure_safe_plan(plan)
    if not execute:
        return {"mode": "dry-run", "actions": plan.get("actions", [])}
    for action in plan["actions"]:
        adb.shell("pm", "disable-user", "--user", "0", action["package"])
    return {"mode": "executed", "changed": len(plan["actions"])}


def restore(adb, backup, execute=False):
    """Re-enable only packages that were enabled before the plan ran (was_disabled == False).

    Falls back to re-enabling all actions if the backup pre-dates the state-tracking field
    (i.e. was created before this fix), so old backup files remain usable.
    """
    if not execute:
        return {"mode": "dry-run", "actions": backup.get("actions", [])}

    state_entries = backup.get("state", [])
    restored, skipped = 0, 0

    if state_entries:
        # New-style backup: honour was_disabled so we don't accidentally enable
        # packages that were already disabled before the plan ran.
        for entry in state_entries:
            if not entry.get("was_disabled", False):
                adb.shell("pm", "enable", entry["package"])
                restored += 1
            else:
                skipped += 1
    else:
        # Legacy backup (no state list): re-enable everything to stay safe.
        for action in backup.get("actions", []):
            adb.shell("pm", "enable", action["package"])
            restored += 1

    return {"mode": "executed", "restored": restored, "skipped_already_disabled": skipped}


def verify(adb, backup):
    """Compare backup state against the current device state and report divergences."""
    currently_disabled = set(
        filter(None, adb.shell("pm", "list", "packages", "-d").replace("package:", "").splitlines())
    )

    results = []
    for entry in backup.get("state", []):
        pkg = entry["package"]
        now_disabled = pkg in currently_disabled
        results.append({
            "package": pkg,
            "backup_was_disabled": entry["was_disabled"],
            "currently_disabled": now_disabled,
            "diverged": entry["was_disabled"] != now_disabled,
        })

    any_diverged = any(r["diverged"] for r in results)
    return {
        "mode": "verify",
        "diverged": any_diverged,
        "packages": results,
    }


def draft_agent_plan(inv, disable_packages, protected=None):
    """Build a plan from an AI agent's package list, enforcing both core and profile protections.

    Args:
        inv: inventory dict (output of ``inventory()``).
        disable_packages: iterable of package names the agent wants to disable.
        protected: optional set of profile-level protected packages to honour in
                   addition to the hardcoded core-namespace guard.
    """
    present = set(inv.get("packages", []))
    protected = set(protected or [])
    actions = []
    rejected = []

    for package in disable_packages:
        # Safety net: must be installed, must not be a core-namespace package,
        # and must not be listed in the profile's protected_packages.
        if package in present and not is_core(package) and package not in protected:
            actions.append({
                "package": package,
                "action": "disable-user",
                "evidence": "AI Agent Evaluation",
                "rollback": "enable",
            })
        else:
            rejected.append(package)

    return {
        "created_at": now(),
        "profile": "ai-agent-dynamic",
        "dry_run": True,
        "inventory_packages": sorted(present),
        "actions": actions,
        "rejected": rejected,
    }
