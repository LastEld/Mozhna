from datetime import date
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from .money import MoneySnapshot

Minor = Annotated[int, Field(strict=True, ge=0, le=9_007_199_254_740_991)]
SignedMinor = Annotated[int, Field(strict=True, ge=-9_007_199_254_740_991, le=9_007_199_254_740_991)]

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Login(Input):
    password: str = Field(max_length=1024)

class SnapshotUpdate(Input):
    expected_version: int = Field(ge=0)
    snapshot: MoneySnapshot

class Simulation(Input):
    amount_minor: Minor

class PlanCreate(Input):
    title: str = Field(min_length=1,max_length=200)
    need: str = Field(default='',max_length=2000)
    baseline_minor: Minor
    alternative_minor: Minor
    frequency_per_month: int = Field(ge=1,le=1000)
    setup_cost_minor: Minor = 0
    currency: Literal['EUR'] = 'EUR'

class PlanChange(Input):
    expected_version: int = Field(ge=1)
    status: Literal['active','rejected','completed']
    rejection_reason: str = Field(default='',max_length=2000)

class Observation(Input):
    amount_minor: Minor
    note: str = Field(default='',max_length=2000)
    date: date

class TransactionCreate(Input):
    date: date
    amount_minor: SignedMinor
    currency: Literal['EUR'] = 'EUR'
    description: str = Field(min_length=1,max_length=500)
    category: str = Field(default='uncategorized',max_length=100)
    external_id: str | None = Field(default=None,max_length=200)

class ImportRequest(Input):
    csv_text: str = Field(min_length=1,max_length=2_000_000)
    currency: Literal['EUR'] = 'EUR'

class JobCreate(Input):
    kind: Literal['compare_plan','income_search','draft_application']
    payload: dict = Field(default_factory=dict)
    provider: Literal['manual','anthropic','gemini'] = 'manual'
    idempotency_key: str = Field(min_length=1,max_length=128)

class Erase(Input):
    confirmation: Literal['DELETE']

class Calculation(BaseModel):
    calculation_id: str
    snapshot_hash: str
    policy_version: str
    as_of: str | None
    evaluated_at: str
    horizon_days: int
    horizon_end: str
    currency: str
    basis: str
    assumptions: list[str]
    warnings: list[str]
    missing_inputs: list[str]
    planned_limit_minor: int | None
    essential_limit_minor: int | None
    essential_headroom_minor: int | None
    planned_headroom_minor: int | None
    decision: Literal['CAN','CAN_WITH_TRADEOFF','CANNOT','UNKNOWN']
    candidate_minor: int
    candidate_date: str
    affected_commitments: list[str]
    commitments_beyond_horizon: list[str]
    excluded_income_ids: list[str]
    explanation_factors: list[dict]

class SnapshotView(BaseModel):
    version: int
    snapshot: MoneySnapshot | None
    calculation: Calculation | None

class UserView(BaseModel):
    id: str
    name: str

class AuthView(BaseModel):
    user: UserView
    csrf_token: str

class PlanView(PlanCreate):
    id: str
    version: int
    created_at: str
    status: Literal['proposed','active','rejected','completed']
    observations: list[Observation]
    rejection_reason: str = ''
    scenario_savings_minor: int
    first_month_savings_minor: int
    observed_spend_minor: int
    observed_difference_minor: int

class TransactionView(TransactionCreate):
    id: str
    version: int
    created_at: str

class JobView(BaseModel):
    id: str
    kind: str
    provider: str
    status: str
    payload: dict
    result: dict | None
    error: str | None
    attempts: int
    version: int
    created_at: str
    updated_at: str

from typing import Generic, TypeVar
T = TypeVar('T')
class Page(BaseModel, Generic[T]):
    items: list[T]

class ScheduleCreate(Input):
    plan_id: str
    interval_hours: int = Field(default=24,ge=1,le=168)

class ScheduleView(BaseModel):
    id: str
    plan_id: str
    interval_hours: int
    next_due: float

class ProviderView(BaseModel):
    id: str
    name: str
    available: bool
    model: str | None = None
    reason: str | None = None
    capabilities: list[str]

class ProviderStateView(BaseModel):
    items: list[ProviderView]
    metered_inference_enabled: bool
    limitations: list[str]
    daily_job_limit: int
