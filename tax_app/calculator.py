"""Deterministic rules for a supported single-filer scenario, in baht."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def numeric_amount(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("Use a numeric baht amount.")
    return value


Money = Annotated[Decimal, Field(ge=0, le=1_000_000_000, decimal_places=2),
                  BeforeValidator(numeric_amount)]
ZERO = Decimal(0)


class TaxInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tax_year: Literal[2568]
    annual_income: Money
    life_premium: Money = ZERO
    health_premium: Money = ZERO
    receipt_general: Money = ZERO
    receipt_special: Money = ZERO
    withheld: Money | None = None


BRACKETS = [(150_000, 0), (300_000, 5), (500_000, 10), (750_000, 15),
            (1_000_000, 20), (2_000_000, 25), (5_000_000, 30), (None, 35)]


def tax_bracket(net_income):
    tax = ZERO
    lower = ZERO
    for upper, rate in BRACKETS:
        limit = net_income if upper is None else min(net_income, Decimal(upper))
        tax += (limit - lower) * rate / 100
        if upper is None or net_income <= upper:
            break
        lower = limit
    return tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_tax(profile: TaxInput):
    expense = min(profile.annual_income * Decimal("0.5"), 100_000)
    life = min(profile.life_premium, 100_000)
    health = min(profile.health_premium, 25_000, 100_000 - life)
    receipts = profile.receipt_general + profile.receipt_special
    receipt_base = min(receipts, 30_000)
    receipt_extra = min(profile.receipt_special, 20_000, receipts - receipt_base)
    before = max(ZERO, profile.annual_income - expense - 60_000)
    net = max(ZERO, before - life - health - receipt_base - receipt_extra)
    tax = tax_bracket(net)
    baseline = tax_bracket(before)
    return {
        "inputs": profile.model_dump(mode="json"),
        "expense": str(expense),
        "personal": "60000",
        "allowed": {
            "life_premium": str(life),
            "health_premium": str(health),
            "receipt_base": str(receipt_base),
            "receipt_extra": str(receipt_extra),
        },
        "disallowed": {
            "life_premium": str(profile.life_premium - life),
            "health_premium": str(profile.health_premium - health),
            "receipts": str(receipts - receipt_base - receipt_extra),
        },
        "net_income": str(net),
        "tax_before_optional": str(baseline),
        "tax": str(tax),
        "tax_saved": str(baseline - tax),
        "balance": None if profile.withheld is None else str(tax - profile.withheld),
    }
