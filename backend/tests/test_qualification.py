"""Tests for AI qualification agent — rule-based pre-screening.

Tests the pre_screen function which runs WITHOUT calling any LLM.
"""

import sys
import os

# Add ai-core to path for direct import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ai-core"))

from agents.qualification import QualificationInput, pre_screen


def make_input(**kwargs) -> QualificationInput:
    defaults = {
        "total_debt": 850_000,
        "creditors_count": 3,
        "creditor_types": ["bank"],
        "monthly_income": None,
        "is_employed": False,
        "has_property": False,
        "property_types": [],
        "has_transactions_3y": False,
        "marital_status": "single",
        "has_enforcement_proceedings": False,
    }
    defaults.update(kwargs)
    return QualificationInput(**defaults)


def test_reject_low_debt():
    result = pre_screen(make_input(total_debt=20_000))
    assert result["pass"] is False
    assert "25 000" in result["reason"]


def test_pass_normal_debt():
    result = pre_screen(make_input(total_debt=500_000))
    assert result["pass"] is True


def test_flag_transactions():
    result = pre_screen(make_input(has_transactions_3y=True))
    assert "risk:transactions_3y" in result["flags"]


def test_flag_real_estate():
    result = pre_screen(make_input(has_property=True, property_types=["apartment"]))
    assert "risk:real_estate" in result["flags"]


def test_flag_vehicle():
    result = pre_screen(make_input(has_property=True, property_types=["car"]))
    assert "risk:vehicle" in result["flags"]


def test_flag_many_creditors():
    result = pre_screen(make_input(creditors_count=15))
    assert "complexity:many_creditors" in result["flags"]


def test_restructuring_option():
    result = pre_screen(make_input(total_debt=500_000, monthly_income=50_000))
    assert "option:restructuring" in result["flags"]


def test_extrajudicial_option():
    result = pre_screen(make_input(
        total_debt=300_000,
        has_enforcement_proceedings=True,
        has_property=False,
    ))
    assert "option:extrajudicial" in result["flags"]


def test_no_flags_simple_case():
    result = pre_screen(make_input(total_debt=600_000, creditors_count=2))
    assert result["pass"] is True
    assert "risk:transactions_3y" not in result["flags"]
    assert "risk:real_estate" not in result["flags"]
