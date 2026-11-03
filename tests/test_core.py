from types import SimpleNamespace
import json
import pytest
from watchwise.adb import Adb
from watchwise.cli import main
from watchwise.core import (
    ALWAYS_PROTECTED, CORE_PREFIXES, is_core,
    inventory, make_plan, apply, create_backup,
    restore, verify, draft_agent_plan, baseline,
)

def fake(args):
    text = "package:com.example.clock\npackage:android\n" if args[-1:] == ["packages"] else "List of devices attached\nmock\tdevice\n"
    return SimpleNamespace(returncode=0, stdout=text, stderr="")

def rule(package, **extra):
    value = {"package": package, "action": "disable-user", "evidence": "x", "rollback": "enable"}
    value.update(extra)
    return value

def test_mocked_adb_inventory():
    assert inventory(Adb(fake))["packages"] == ["android", "com.example.clock"]

def test_plan_excludes_core_packages():
    profile = {"id":"p", "protected_packages":[], "package_rules":[{"package":"android", "action":"disable-user", "evidence":"x", "rollback":"enable"}, {"package":"com.example.clock", "action":"disable-user", "evidence":"x", "rollback":"enable"}]}
    assert [x["package"] for x in make_plan({"packages":["android", "com.example.clock"]}, profile)["actions"]] == ["com.example.clock"]

def test_apply_is_dry_run_by_default():
    result = apply(Adb(fake), {"inventory_packages":["com.example.clock"], "actions": [{"package":"com.example.clock", "action":"disable-user"}]})
    assert result["mode"] == "dry-run"

def test_protected_action_rejected():
    with pytest.raises(ValueError): apply(Adb(fake), {"actions": [{"package":"android", "action":"disable-user"}]})

def test_backup_captures_state_before_execution():
    plan = {"inventory_packages":["com.example.clock"], "actions":[{"package":"com.example.clock", "action":"disable-user"}]}
    assert create_backup(Adb(fake), plan)["state"] == [{"package": "com.example.clock", "was_disabled":False}]

def test_core_package_needs_evidence_and_enable_rollback():
    profile = {"id":"p", "protected_packages":[], "package_rules":[
        rule("com.samsung.android.evil", evidence=""),
        rule("com.samsung.android.wear.shealth", rollback="uninstall"),
        rule("com.samsung.android.wear.shealth")]}
    plan = make_plan({"packages":["com.samsung.android.evil", "com.samsung.android.wear.shealth"]}, profile)
    assert [x["package"] for x in plan["actions"]] == ["com.samsung.android.wear.shealth"]
    assert {x["package"] for x in plan["rejected"]} == {"com.samsung.android.evil", "com.samsung.android.wear.shealth"}

def test_profile_protected_packages_are_never_planned():
    profile = {"id":"p", "protected_packages":["com.example.clock"], "package_rules":[rule("com.example.clock")]}
    plan = make_plan({"packages":["com.example.clock"]}, profile)
    assert plan["actions"] == [] and plan["rejected"][0]["reason"] == "protected package"
    assert plan["protected_packages"] == ["com.example.clock"]

def test_apply_rejects_core_action_without_evidence():
    plan = {"inventory_packages":["com.samsung.android.wear.shealth"], "protected_packages":[],
            "actions":[{"package":"com.samsung.android.wear.shealth", "action":"disable-user"}]}
    with pytest.raises(ValueError): apply(Adb(fake), plan)

def test_apply_accepts_evidence_backed_core_action():
    plan = {"inventory_packages":["com.samsung.android.wear.shealth"], "protected_packages":[],
            "actions":[rule("com.samsung.android.wear.shealth")]}
    assert apply(Adb(fake), plan)["mode"] == "dry-run"

def test_every_core_namespace_is_covered():
    for prefix in CORE_PREFIXES:
        assert is_core(prefix + "example")
    assert is_core("android") and "android" in ALWAYS_PROTECTED

def test_cli_plan_writes_a_dry_run_plan(tmp_path):
    inv = tmp_path / "inventory.json"
    inv.write_text(json.dumps({"packages": ["com.example.clock"]}), encoding="utf-8")
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({"id": "p", "protected_packages": [], "package_rules": [rule("com.example.clock")]}), encoding="utf-8")
    out = tmp_path / "plan.json"
    main(["plan", "--inventory", str(inv), "--profile", str(profile), "--output", str(out)])
    plan = json.loads(out.read_text(encoding="utf-8"))
    assert plan["dry_run"] is True
    assert [x["package"] for x in plan["actions"]] == ["com.example.clock"]

def test_cli_execution_requires_both_flags(tmp_path):
    with pytest.raises(SystemExit):
        main(["restore", "--backup", str(tmp_path / "b.json"), "--execute"])


# ---------------------------------------------------------------------------
# Tests for fixed/new behaviour
# ---------------------------------------------------------------------------

# --- Fix #1: restore respects was_disabled -----------------------------------

def fake_with_disabled(args):
    """Fake runner where com.example.bloat is already disabled before the plan runs."""
    if args[-2:] == ["packages", "-d"]:
        return SimpleNamespace(returncode=0, stdout="package:com.example.bloat\n", stderr="")
    return SimpleNamespace(returncode=0, stdout="", stderr="")

def test_restore_skips_packages_that_were_already_disabled():
    """Packages that were disabled BEFORE the plan ran must not be re-enabled on restore."""
    backup = {
        "actions": [
            {"package": "com.example.bloat", "action": "disable-user"},
            {"package": "com.example.clock", "action": "disable-user"},
        ],
        "state": [
            {"package": "com.example.bloat", "was_disabled": True},   # pre-existing disable
            {"package": "com.example.clock", "was_disabled": False},  # disabled by plan
        ],
    }
    enabled = []

    def capturing_runner(args):
        if "enable" in args:
            enabled.append(args[-1])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    result = restore(Adb(capturing_runner), backup, execute=True)
    assert result["restored"] == 1
    assert result["skipped_already_disabled"] == 1
    assert "com.example.clock" in enabled
    assert "com.example.bloat" not in enabled


def test_restore_dry_run_returns_all_actions():
    backup = {
        "actions": [{"package": "com.example.clock", "action": "disable-user"}],
        "state": [{"package": "com.example.clock", "was_disabled": False}],
    }
    result = restore(Adb(fake), backup, execute=False)
    assert result["mode"] == "dry-run"
    assert len(result["actions"]) == 1


def test_restore_legacy_backup_without_state_reenables_all():
    """Old-style backups (no state list) re-enable everything to remain safe."""
    backup = {"actions": [{"package": "com.example.clock", "action": "disable-user"}]}
    enabled = []

    def capturing_runner(args):
        if "enable" in args:
            enabled.append(args[-1])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    result = restore(Adb(capturing_runner), backup, execute=True)
    assert result["restored"] == 1
    assert "com.example.clock" in enabled


# --- Fix #2: verify does a real device comparison ---------------------------

def fake_for_verify(args):
    """
    - pm list packages -d  → com.example.bloat is currently disabled
    - everything else      → empty
    """
    if args[-2:] == ["packages", "-d"]:
        return SimpleNamespace(returncode=0, stdout="package:com.example.bloat\n", stderr="")
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_verify_detects_divergence():
    """verify() must flag a package whose current state differs from the backup."""
    backup = {
        "state": [
            # bloat was enabled when backup was taken, but is now disabled → diverged
            {"package": "com.example.bloat", "was_disabled": False},
            # clock was enabled and is still enabled → not diverged
            {"package": "com.example.clock", "was_disabled": False},
        ]
    }
    result = verify(Adb(fake_for_verify), backup)
    assert result["mode"] == "verify"
    assert result["diverged"] is True
    diverged_pkgs = [p for p in result["packages"] if p["diverged"]]
    assert len(diverged_pkgs) == 1
    assert diverged_pkgs[0]["package"] == "com.example.bloat"


def test_verify_no_divergence_when_states_match():
    backup = {
        "state": [
            # bloat was disabled before plan and is still disabled → no divergence
            {"package": "com.example.bloat", "was_disabled": True},
        ]
    }
    result = verify(Adb(fake_for_verify), backup)
    assert result["diverged"] is False
    assert all(not p["diverged"] for p in result["packages"])


# --- Fix #3: agent-plan honours profile protected_packages ------------------

def test_draft_agent_plan_honours_profile_protected():
    inv = {"packages": ["com.example.clock", "com.example.ads"]}
    # com.example.clock is in the profile's protected list
    result = draft_agent_plan(inv, ["com.example.clock", "com.example.ads"],
                              protected=["com.example.clock"])
    planned = [a["package"] for a in result["actions"]]
    assert "com.example.clock" not in planned
    assert "com.example.clock" in result["rejected"]
    assert "com.example.ads" in planned


def test_draft_agent_plan_no_profile_protected_still_blocks_core():
    inv = {"packages": ["com.samsung.android.something", "com.example.ads"]}
    result = draft_agent_plan(inv, ["com.samsung.android.something", "com.example.ads"])
    planned = [a["package"] for a in result["actions"]]
    assert "com.samsung.android.something" not in planned
    assert "com.example.ads" in planned


def test_cli_agent_plan_passes_profile_protected(tmp_path):
    inv = tmp_path / "inventory.json"
    inv.write_text(json.dumps({"packages": ["com.example.clock", "com.example.ads"]}), encoding="utf-8")
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({
        "id": "p", "manufacturer": "X", "model": "Y", "platform": "wear-os-adb",
        "evidence_level": "user-reported",
        "protected_packages": ["com.example.clock"],
        "package_rules": [],
    }), encoding="utf-8")
    out = tmp_path / "agent-plan.json"
    main(["agent-plan", "--inventory", str(inv), "--profile", str(profile),
          "--disable", "com.example.clock", "com.example.ads", "--output", str(out)])
    plan = json.loads(out.read_text(encoding="utf-8"))
    planned = [a["package"] for a in plan["actions"]]
    assert "com.example.clock" not in planned
    assert "com.example.ads" in planned


# --- Fix #4: apply / restore emit valid JSON, not Python repr ---------------

def test_apply_dry_run_output_is_valid_json(tmp_path, capsys):
    plan = {
        "inventory_packages": ["com.example.clock"],
        "actions": [{"package": "com.example.clock", "action": "disable-user"}],
    }
    apply(Adb(fake), plan, execute=False)
    # apply() returns a dict; the CLI wraps it with json.dumps — test via CLI
    inv = tmp_path / "inv.json"
    inv.write_text(json.dumps({"packages": ["com.example.clock"]}), encoding="utf-8")
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({
        "id": "p", "manufacturer": "X", "model": "Y", "platform": "wear-os-adb",
        "evidence_level": "user-reported", "protected_packages": [],
        "package_rules": [{"package": "com.example.clock", "action": "disable-user",
                           "evidence": "x", "rollback": "enable"}],
    }), encoding="utf-8")
    plan_file = tmp_path / "plan.json"
    backup_file = tmp_path / "backup.json"
    main(["plan", "--inventory", str(inv), "--profile", str(profile), "--output", str(plan_file)])
    # Dry-run apply (no --execute --yes): output must be valid JSON
    main(["apply", "--plan", str(plan_file), "--backup", str(backup_file)])
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)   # would raise JSONDecodeError if not valid JSON
    assert parsed["mode"] == "dry-run"


# --- Fix #5: baseline returns structured dicts, not raw strings -------------

def fake_baseline(args):
    if any("df" == a for a in args):
        raw = "Filesystem     1K-blocks  Used Available Use% Mounted on\n/dev/block/dm-0  6291456 3145728   3145728  50% /data\n"
        return SimpleNamespace(returncode=0, stdout=raw, stderr="")
    if any("/proc/meminfo" == a for a in args):
        raw = "MemTotal:        1024000 kB\nMemFree:          512000 kB\n"
        return SimpleNamespace(returncode=0, stdout=raw, stderr="")
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_baseline_disk_is_structured_dict():
    result = baseline(Adb(fake_baseline))
    assert isinstance(result["disk"], dict), "disk must be a parsed dict, not a raw string"
    assert "use_pct" in result["disk"]
    assert result["disk"]["use_pct"] == "50%"


def test_baseline_memory_is_structured_dict():
    result = baseline(Adb(fake_baseline))
    assert isinstance(result["memory"], dict), "memory must be a parsed dict, not a raw string"
    assert "MemTotal" in result["memory"]
    assert result["memory"]["MemTotal"] == "1024000 kB"


# --- Fix #6: Adb serial flag is keyword-only, runner positional still works -

def test_adb_serial_is_keyword_only():
    """Passing a runner as the first positional arg must still work (backwards compat)."""
    called_with = []

    def recording_runner(args):
        called_with.append(args)
        return SimpleNamespace(returncode=0, stdout="List of devices attached\n", stderr="")

    adb = Adb(recording_runner)
    adb.devices()
    assert called_with, "runner should have been called"
    # No '-s' prefix when serial is not set
    assert "-s" not in called_with[0]


def test_adb_serial_prepended_to_commands():
    """When serial= is provided, -s <serial> must appear before the subcommand."""
    called_with = []

    def recording_runner(args):
        called_with.append(args)
        return SimpleNamespace(returncode=0, stdout="List of devices attached\n", stderr="")

    adb = Adb(recording_runner, serial="192.168.1.100:5555")
    adb.devices()
    assert called_with[0][:2] == ["-s", "192.168.1.100:5555"]
