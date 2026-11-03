import json
from pathlib import Path

import pytest

from watchwise.core import ALWAYS_PROTECTED

PROFILES = sorted(Path(__file__).resolve().parent.parent.joinpath("profiles").rglob("*.json"))
REQUIRED = {"id", "manufacturer", "model", "platform", "evidence_level", "protected_packages", "package_rules"}

def test_profiles_exist():
    assert PROFILES

@pytest.mark.parametrize("path", PROFILES, ids=lambda p: p.stem)
def test_profile_matches_schema(path):
    profile = json.loads(path.read_text(encoding="utf-8"))
    assert REQUIRED <= set(profile)
    assert profile["platform"] == "wear-os-adb"
    assert profile["evidence_level"] in {"user-reported", "independently-validated"}
    assert isinstance(profile["protected_packages"], list)
    for rule in profile["package_rules"]:
        assert rule["action"] == "disable-user"
        assert rule["evidence"].strip() and rule["rollback"] == "enable"
        assert not rule["package"].startswith("com.android.")
        assert rule["package"] not in ALWAYS_PROTECTED
        assert rule["package"] not in profile["protected_packages"]

def test_reference_profile_keeps_unvalidated_rules_empty():
    profile = json.loads(Path(__file__).resolve().parent.parent.joinpath("profiles/galaxy-watch4-sm-r870.json").read_text(encoding="utf-8"))
    assert profile["package_rules"] == []
