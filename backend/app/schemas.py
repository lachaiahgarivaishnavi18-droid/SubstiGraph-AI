from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Literal

class ProductInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    product_name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=80)
    brand: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=100)
    subcategory: str = Field(min_length=1, max_length=100)
    description: str = Field(default='', max_length=2000)
    price: float = Field(gt=0, allow_inf_nan=False)
    cost: float = Field(ge=0, allow_inf_nan=False)
    attributes: dict[str, str | float | int | bool] = Field(default_factory=dict)
    specifications: dict[str, str | float | int | bool] = Field(default_factory=dict)
    color: str = ''
    size: str = ''
    material: str = ''
    product_rating: float = Field(default=0, ge=0, le=5)
    stock_quantity: int = Field(default=0, ge=0)
    supplier_id: str = Field(min_length=1)
    sales_quantity: int = Field(default=0, ge=0)
    status: Literal['active', 'discontinued'] = 'active'

class Weights(BaseModel):
    attribute: float = Field(default=30, ge=0, le=100)
    semantic: float = Field(default=25, ge=0, le=100)
    category: float = Field(default=15, ge=0, le=100)
    price: float = Field(default=15, ge=0, le=100)
    availability: float = Field(default=10, ge=0, le=100)
    brand: float = Field(default=5, ge=0, le=100)
    @model_validator(mode='after')
    def total(self):
        if abs(sum(self.model_dump().values()) - 100) > 0.001:
            raise ValueError('Weights must sum to 100')
        return self

class SubstituteRequest(BaseModel):
    product_id: int
    max_price_deviation: float = Field(default=0.4, ge=0, le=2)
    require_available: bool = True
    limit: int = Field(default=5, ge=0, le=5000)
    required_specs: dict[str, str | float | int | bool] = Field(default_factory=dict)

class OptimizeRequest(BaseModel):
    budget: float = Field(default=5000, gt=0, le=10000000)
    max_products: int = Field(default=30, ge=1, le=500)
    min_per_category: int = Field(default=1, ge=0, le=50)

class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1500)

class GroundedAnswer(BaseModel):
    answer: str
    evidence_ids: list[int]
