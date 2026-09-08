from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from mozhna.money import SAFE_INTEGER, MoneySnapshot, evaluate

NOW = datetime(2026, 9, 7, 12, tzinfo=timezone.utc)


def snapshot(**changes):
    values = dict(balance_minor=100000, currency="EUR", as_of=NOW,
                  horizon_days=30, reserve_minor=20000, goal_minor=5000,
                  living_budget_minor=10000,
                  commitments=[dict(id="rent", label="Rent", amount_minor=60000,
                                    due_date="2026-09-08")], incomes=[])
    values.update(changes)
    return MoneySnapshot(**values)


@pytest.mark.parametrize("amount,decision", [(4000, "CAN"), (7000, "CAN_WITH_TRADEOFF"), (12000, "CANNOT")])
def test_acceptance_examples_and_candidate_deducted_once(amount, decision):
    result = evaluate(snapshot(), amount, now=NOW)
    assert result["essential_limit_minor"] == 10000
    assert result["planned_limit_minor"] == 5000
    assert result["essential_headroom_minor"] == 10000 - amount
    assert result["planned_headroom_minor"] == 5000 - amount
    assert result["decision"] == decision


def test_negative_headroom_not_hidden_by_zero_limit():
    result = evaluate(snapshot(balance_minor=10000), 0, now=NOW)
    assert result["essential_limit_minor"] == 0
    assert result["essential_headroom_minor"] == -80000
    assert result["decision"] == "CANNOT"


@pytest.mark.parametrize("changes,reason", [
    ({"as_of": NOW - timedelta(hours=24, seconds=1)}, "stale_snapshot"),
    ({"as_of": NOW + timedelta(seconds=1)}, "future_snapshot"),
    ({"reserve_minor": None}, "reserve_minor"),
    ({"commitments": None}, "commitments"),
    ({"data_complete": False}, "data_incomplete"),
])
def test_unknown_hides_dependent_amounts(changes, reason):
    result = evaluate(snapshot(**changes), now=NOW)
    assert result["decision"] == "UNKNOWN"
    assert result["planned_limit_minor"] is None
    assert reason in result["missing_inputs"]


def test_exact_freshness_boundary_is_valid():
    assert evaluate(snapshot(as_of=NOW - timedelta(hours=24)), now=NOW)["decision"] == "CAN"


def test_future_income_does_not_cover_earlier_shortfall():
    income = dict(id="salary", label="Salary", amount_minor=100000,
                  due_date="2026-09-20", confirmed=True)
    result = evaluate(snapshot(balance_minor=50000, incomes=[income]), now=NOW)
    assert result["decision"] == "CANNOT"
    assert result["basis"] == "conditional_confirmed_income_forecast"
    assert "rent" in result["affected_commitments"]


def test_same_day_future_income_cannot_assume_it_arrives_before_rent():
    income = dict(id="salary", label="Salary", amount_minor=100000,
                  due_date="2026-09-08", confirmed=True)
    assert evaluate(snapshot(balance_minor=50000, incomes=[income]), now=NOW)["decision"] == "CANNOT"


def test_unconfirmed_and_past_income_never_increase_limit():
    income = [dict(id="maybe", label="Maybe", amount_minor=100000,
                   due_date="2026-09-20", confirmed=False),
              dict(id="past", label="Settled", amount_minor=100000,
                   due_date="2026-09-06", confirmed=True)]
    result = evaluate(snapshot(incomes=income), now=NOW)
    assert result["planned_limit_minor"] == 5000
    assert result["excluded_income_ids"] == ["maybe", "past"]
    assert result["basis"] == "cash_only"


def test_forecast_changes_future_capacity_but_not_observed_cash():
    income = dict(id="salary", label="Salary", amount_minor=100000,
                  due_date="2026-09-08", confirmed=True)
    data = snapshot(balance_minor=10000, reserve_minor=0, goal_minor=0,
                    living_budget_minor=0, commitments=[], incomes=[income])
    assert evaluate(data, 15000, now=NOW)["decision"] == "CANNOT"
    later = evaluate(data, 15000, date="2026-09-09", now=NOW)
    assert later["decision"] == "CAN"
    assert later["essential_limit_minor"] == 10000  # today's limit


def test_overdue_unpaid_commitment_charged_now_and_beyond_horizon_visible():
    flows = [dict(id="old", label="Unpaid", amount_minor=3000, due_date="2026-08-01"),
             dict(id="next", label="Later", amount_minor=99999, due_date="2026-12-01")]
    result = evaluate(snapshot(balance_minor=10000, reserve_minor=0, goal_minor=0,
                               living_budget_minor=0, commitments=flows), now=NOW)
    assert result["essential_limit_minor"] == 7000
    assert result["commitments_beyond_horizon"] == ["next"]
    assert "overdue_commitments_charged_now" in result["warnings"]


def test_living_budget_integer_remainder_is_fully_allocated():
    result = evaluate(snapshot(balance_minor=1000, reserve_minor=0, goal_minor=0,
                               living_budget_minor=101, commitments=[], horizon_days=3), now=NOW)
    assert result["planned_limit_minor"] == 899


@pytest.mark.parametrize("value", [1.1, "100", True, SAFE_INTEGER + 1])
def test_strict_minor_units(value):
    with pytest.raises(ValidationError):
        snapshot(balance_minor=value)
    with pytest.raises(ValidationError):
        evaluate(snapshot(), value, now=NOW)


def test_aggregate_overflow_is_unknown():
    flows = [dict(id=str(i), label="Liability", amount_minor=SAFE_INTEGER,
                  due_date="2026-09-08") for i in range(2)]
    result = evaluate(snapshot(commitments=flows), now=NOW)
    assert result["decision"] == "UNKNOWN"
    assert "arithmetic_outside_safe_integer_range" in result["missing_inputs"]


@pytest.mark.parametrize("date", ["2026-09-06", "2026-10-08"])
def test_candidate_outside_horizon_is_unknown(date):
    assert evaluate(snapshot(), date=date, now=NOW)["decision"] == "UNKNOWN"


def test_replay_is_identical_and_snapshot_not_mutated():
    data = snapshot()
    before = data.model_dump_json()
    first = evaluate(data, 7000, now=NOW)
    assert first == evaluate(data, 7000, now=NOW)
    assert before == data.model_dump_json()
    assert first["calculation_id"] != evaluate(data, 7001, now=NOW)["calculation_id"]


def test_currency_timezone_duplicate_id_validation():
    with pytest.raises(ValidationError):
        snapshot(currency="USD")
    with pytest.raises(ValidationError):
        snapshot(as_of=NOW.replace(tzinfo=None))
    flow = dict(id="same", label="Rent", amount_minor=1, due_date="2026-09-08")
    with pytest.raises(ValidationError):
        snapshot(commitments=[flow, flow])
