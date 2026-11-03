from typing import Literal
from pydantic import BaseModel, Field

class Case(BaseModel):
    id: str
    title: str
    steps: list[str]
    expected: list[str]

class Cases(BaseModel):
    cases: list[Case] = Field(min_length=1, max_length=12)

class Code(BaseModel):
    code: str

class Diagnosis(BaseModel):
    category: Literal["product_defect", "test_defect", "environment", "unknown"]
    explanation: str
    revised_code: str | None = None
