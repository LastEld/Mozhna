"""Deterministic, EUR-only Money Kernel (policy mozhna.money.v1).

Implementation policy selected for the owner's one-shot implementation request:
* snapshots are reconciled own cash, not credit limits or transaction histories;
* commitments are still unpaid; overdue commitments are charged immediately;
* only confirmed income dated after today is forecast, never observed cash;
* reserve is held immediately, remaining living budget is spread over the next
  horizon_days (integer remainder on the earliest days), goal is due at the end;
* snapshots older than 24h, incomplete data and unsafe arithmetic yield UNKNOWN.

These are explicit modelling assumptions, not evidence of bank reconciliation.
No network, persistence, LLM or binary floating-point money arithmetic is used.
"""

from __future__ import annotations

from datetime import date as CalendarDate, datetime, timedelta, timezone
from hashlib import sha256
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

SAFE_INTEGER = 2**53 - 1
POLICY_VERSION = "mozhna.money.v1"
Money = Annotated[int, Field(strict=True, ge=-SAFE_INTEGER, le=SAFE_INTEGER)]
NonnegativeMoney = Annotated[int, Field(strict=True, ge=0, le=SAFE_INTEGER)]
_candidate_adapter = TypeAdapter(NonnegativeMoney)


class Commitment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=200)
    label: str = Field(min_length=1, max_length=200)
    amount_minor: NonnegativeMoney
    due_date: CalendarDate


class Income(Commitment):
    confirmed: bool = False


class MoneySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    balance_minor: Money | None = None
    currency: Literal["EUR"] = "EUR"
    as_of: datetime | None = None
    horizon_days: Annotated[int, Field(strict=True, ge=1, le=366)] = 30
    reserve_minor: NonnegativeMoney | None = None
    goal_minor: NonnegativeMoney | None = None
    living_budget_minor: NonnegativeMoney | None = None
    commitments: list[Commitment] | None = Field(default=None, max_length=1000)
    incomes: list[Income] | None = Field(default=None, max_length=1000)
    data_complete: bool = True

    @field_validator("as_of")
    @classmethod
    def aware_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.utcoffset() is None:
                raise ValueError("as_of must include a timezone")
            return value.astimezone(timezone.utc)
        return value

    @model_validator(mode="after")
    def unique_flow_ids(self) -> MoneySnapshot:
        for kind in (self.commitments, self.incomes):
            if kind is not None and len({item.id for item in kind}) != len(kind):
                raise ValueError("flow IDs must be unique within commitments/incomes")
        return self


def _hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def evaluate(
    snapshot: MoneySnapshot | dict,
    amount_minor: int = 0,
    date: CalendarDate | str | None = None,
    *,
    now: datetime | None = None,
) -> dict:
    """Return a JSON-ready calculation. Inject ``now`` for deterministic replay.

    Limits describe a purchase today BEFORE candidate deduction. Decisions use
    raw headroom AFTER the candidate exactly once at its requested date. A future
    purchase never makes an already-existing shortfall disappear.
    """
    snapshot = MoneySnapshot.model_validate(snapshot)
    amount_minor = _candidate_adapter.validate_python(amount_minor)
    current = now or datetime.now(timezone.utc)
    if current.utcoffset() is None:
        raise ValueError("now must include a timezone")
    current = current.astimezone(timezone.utc)
    today = current.date()
    purchase_date = CalendarDate.fromisoformat(date) if isinstance(date, str) else date or today
    if isinstance(purchase_date, datetime) or not isinstance(purchase_date, CalendarDate):
        raise ValueError("date must be an ISO calendar date")
    horizon_end = today + timedelta(days=snapshot.horizon_days)
    snapshot_json = snapshot.model_dump(mode="json")
    snapshot_hash = _hash(snapshot_json)
    calculation_id = _hash({"snapshot": snapshot_hash, "amount_minor": amount_minor,
                            "date": purchase_date.isoformat(), "now": current.isoformat(),
                            "policy": POLICY_VERSION})
    missing = [key for key in ("balance_minor", "as_of", "reserve_minor", "goal_minor",
                               "living_budget_minor", "commitments", "incomes")
               if getattr(snapshot, key) is None]
    if not snapshot.data_complete:
        missing.append("data_incomplete")
    if snapshot.as_of is not None:
        if current - snapshot.as_of > timedelta(hours=24):
            missing.append("stale_snapshot")
        if snapshot.as_of > current:
            missing.append("future_snapshot")
    if purchase_date < today or purchase_date > horizon_end:
        missing.append("candidate_date_outside_horizon")
    assumptions = [
        "Balance is reconciled own liquid cash; excludes credit limits and already settled transactions.",
        "Commitments are unpaid and not already deducted from balance; overdue commitments are due now.",
        "Only confirmed income after today is forecast; income through today must be reconciled in balance.",
        "Same-day commitments are evaluated before same-day future income (intraday order is unknown).",
        "Reserve is protected now; remaining living budget is allocated daily; goal contribution is due at horizon end.",
        "Limits describe an immediate purchase before the candidate; candidate is deducted exactly once on its date.",
        "UTC calendar dates; single pooled EUR balance. Per-account payment feasibility is not established.",
    ]
    warnings = []
    commitments = snapshot.commitments or []
    incomes = snapshot.incomes or []
    outside = [flow.id for flow in commitments if flow.due_date > horizon_end]
    if outside:
        warnings.append("commitments_beyond_horizon")
    excluded_incomes = [flow.id for flow in incomes
                        if not flow.confirmed or flow.due_date <= today or flow.due_date > horizon_end]
    if excluded_incomes:
        warnings.append("income_excluded_from_forecast")
    overdue = [flow.id for flow in commitments if flow.due_date < today]
    if overdue:
        warnings.append("overdue_commitments_charged_now")
    eligible = [flow for flow in incomes if flow.confirmed and today < flow.due_date <= horizon_end]
    result = {
        "calculation_id": calculation_id,
        "snapshot_hash": snapshot_hash,
        "policy_version": POLICY_VERSION,
        "as_of": snapshot.as_of.isoformat() if snapshot.as_of else None,
        "evaluated_at": current.isoformat(),
        "horizon_days": snapshot.horizon_days,
        "horizon_end": horizon_end.isoformat(),
        "currency": snapshot.currency,
        "basis": "conditional_confirmed_income_forecast" if eligible else "cash_only",
        "assumptions": assumptions,
        "warnings": warnings,
        "missing_inputs": missing,
        "planned_limit_minor": None,
        "essential_limit_minor": None,
        "essential_headroom_minor": None,
        "planned_headroom_minor": None,
        "decision": "UNKNOWN",
        "candidate_minor": amount_minor,
        "candidate_date": purchase_date.isoformat(),
        "affected_commitments": [],
        "commitments_beyond_horizon": outside,
        "excluded_income_ids": excluded_incomes,
        "explanation_factors": [],
    }
    if missing:
        result["explanation_factors"] = [{"code": code} for code in missing]
        return result

    # Integers remain unbounded internally, then every exposed money value is
    # checked. Never emit unsafe JSON numbers or hide a negative raw headroom.
    assert snapshot.balance_minor is not None
    assert snapshot.reserve_minor is not None
    assert snapshot.goal_minor is not None
    assert snapshot.living_budget_minor is not None
    daily, remainder = divmod(snapshot.living_budget_minor, snapshot.horizon_days)
    cash = snapshot.balance_minor
    candidate_applied = 0
    base_essential: list[int] = []
    base_planned: list[int] = []
    candidate_essential: list[int] = []
    candidate_planned: list[int] = []
    affected: set[str] = set()
    unsafe = False
    goal_allocated = 0

    def record() -> None:
        nonlocal unsafe
        essential = cash - snapshot.reserve_minor
        planned = essential - goal_allocated
        after_essential = essential - candidate_applied
        after_planned = planned - candidate_applied
        base_essential.append(essential)
        base_planned.append(planned)
        candidate_essential.append(after_essential)
        candidate_planned.append(after_planned)
        if any(abs(value) > SAFE_INTEGER for value in
               (cash, essential, planned, after_essential, after_planned)):
            unsafe = True

    for offset in range(snapshot.horizon_days + 1):
        day = today + timedelta(days=offset)
        if day == purchase_date:
            candidate_applied = amount_minor
        if offset:
            cash -= daily + (1 if offset <= remainder else 0)
        if day == horizon_end:
            goal_allocated = snapshot.goal_minor
        due = sorted((flow for flow in commitments if max(flow.due_date, today) == day),
                     key=lambda flow: flow.id)
        for flow in due:
            cash -= flow.amount_minor
            if cash - snapshot.reserve_minor - candidate_applied < 0:
                affected.add(flow.id)
        # Conservative ordering prevents an un-timed incoming transfer from
        # promising coverage of an obligation earlier on the same calendar day.
        record()
        for income in eligible:
            if income.due_date == day:
                cash += income.amount_minor
        record()

    if unsafe:
        result["missing_inputs"].append("arithmetic_outside_safe_integer_range")
        result["explanation_factors"] = [{"code": "arithmetic_outside_safe_integer_range"}]
        return result
    essential = min(candidate_essential)
    planned = min(candidate_planned)
    decision = "CANNOT" if essential < 0 else "CAN_WITH_TRADEOFF" if planned < 0 else "CAN"
    result.update({
        "essential_limit_minor": max(0, min(base_essential)),
        "planned_limit_minor": max(0, min(base_planned)),
        "essential_headroom_minor": essential,
        "planned_headroom_minor": planned,
        "decision": decision,
        "affected_commitments": sorted(affected),
        "explanation_factors": [
            {"code": "essential_headroom_after_candidate", "amount_minor": essential},
            {"code": "planned_headroom_after_candidate", "amount_minor": planned},
            {"code": "goal_contribution_at_risk", "amount_minor": min(snapshot.goal_minor, max(0, -planned))},
        ],
    })
    return result


# Short aliases for non-HTTP callers; the API uses the descriptive public names.
Snapshot = MoneySnapshot
calculate = evaluate
