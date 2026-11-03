import argparse
import json

from .adb import Adb
from .core import (
    baseline, inventory, make_plan, read_json, write_json,
    apply, restore, create_backup, verify, draft_agent_plan,
)


def gated(args):
    if args.execute and not args.yes:
        raise SystemExit("Execution requires both --execute and --yes.")
    return args.execute and args.yes


def _print_json(value):
    """Print a value as valid, pretty-printed JSON (not a Python repr)."""
    print(json.dumps(value, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(prog="watchwise")
    p.add_argument("--serial", "-s", default=None,
                   help="ADB device serial (required when multiple devices are connected)")
    sub = p.add_subparsers(dest="command", required=True)

    # discover
    sub.add_parser("discover")

    # inventory / baseline
    for name in ("inventory", "baseline"):
        sub.add_parser(name).add_argument("--output", required=True)

    # plan
    plan_p = sub.add_parser("plan")
    plan_p.add_argument("--inventory", required=True)
    plan_p.add_argument("--profile", required=True)
    plan_p.add_argument("--output", required=True)

    # agent-plan
    agent_p = sub.add_parser("agent-plan")
    agent_p.add_argument("--inventory", required=True)
    agent_p.add_argument("--profile", default=None,
                         help="Optional profile JSON; its protected_packages are honoured")
    agent_p.add_argument("--disable", nargs="+", required=True,
                         help="List of packages to disable")
    agent_p.add_argument("--output", required=True)

    # apply
    apply_p = sub.add_parser("apply")
    apply_p.add_argument("--plan", required=True)
    apply_p.add_argument("--backup", required=True)
    apply_p.add_argument("--execute", action="store_true")
    apply_p.add_argument("--yes", action="store_true")

    # restore / verify
    for name in ("restore", "verify"):
        x = sub.add_parser(name)
        x.add_argument("--backup", required=True)
        x.add_argument("--execute", action="store_true")
        x.add_argument("--yes", action="store_true")

    a = p.parse_args(argv)
    adb = Adb(serial=a.serial)

    if a.command == "discover":
        print(adb.devices())
        return

    if a.command == "inventory":
        write_json(a.output, inventory(adb))
        return

    if a.command == "baseline":
        write_json(a.output, baseline(adb))
        return

    if a.command == "plan":
        write_json(a.output, make_plan(read_json(a.inventory), read_json(a.profile)))
        return

    if a.command == "agent-plan":
        # Pass profile's protected_packages through so the agent cannot bypass them.
        protected = read_json(a.profile).get("protected_packages", []) if a.profile else []
        write_json(a.output, draft_agent_plan(read_json(a.inventory), a.disable, protected=protected))
        return

    execute = gated(a)

    if a.command == "apply":
        plan = read_json(a.plan)
        if execute:
            write_json(a.backup, create_backup(adb, plan))
        _print_json(apply(adb, plan, execute))
        return

    backup = read_json(a.backup)

    if a.command == "restore":
        _print_json(restore(adb, backup, execute))
        return

    if a.command == "verify":
        _print_json(verify(adb, backup))
        return


if __name__ == "__main__":
    main()
