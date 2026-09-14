"""
Domain models for SignalPost agent.
Defines Fact, CompanyProfile, and Update tracking schemas with complete provenance.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FactCategory(str, Enum):
    IDENTIFICATION = "Identification & Legal Registration"
    LOCATION = "Registered Office & Location"
    INDUSTRY = "Industry & Business Activities"
    WORKFORCE = "Workforce & Employment"
    GOVERNANCE = "Corporate Governance & Roles"
    FINANCIALS = "Financial Performance (Audited Accounts)"
    LEGAL_STATUS = "Legal Status & Solvency"
    ONLINE = "Official Web & Digital Footprint"


class Fact(BaseModel):
    key: str = Field(..., description="Unique machine identifier for fact (e.g. legal_name, ceo)")
    label: str = Field(..., description="Human-readable fact title")
    value: Any = Field(..., description="Fact value (string, number, list, or structured object)")
    category: str = Field(..., description="Fact category grouping")
    source_name: str = Field(..., description="Human-readable authority/source name")
    source_url: str = Field(..., description="Permitted public source URL")
    source_date: Optional[str] = Field(None, description="Official registration or publication date")
    retrieved_at: str = Field(..., description="Timestamp when agent retrieved/verified this fact")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Verification confidence score (0.0 - 1.0)")
    verified: bool = Field(True, description="Whether entity disambiguation confirmed provenance")
    validation_notes: str = Field("Verified via official public registry", description="Verification details")


class RoleItem(BaseModel):
    role_code: str
    role_description: str
    person_name: Optional[str] = None
    birth_date: Optional[str] = None
    is_deceased: Optional[bool] = False
    is_deregistered: Optional[bool] = False
    organization_name: Optional[str] = None
    organization_orgnr: Optional[str] = None
    last_updated: Optional[str] = None


class FinancialYearData(BaseModel):
    year: int
    period_start: str
    period_end: str
    currency: str = "NOK"
    revenue: Optional[float] = None
    operating_profit: Optional[float] = None
    net_profit: Optional[float] = None
    total_assets: Optional[float] = None
    total_equity: Optional[float] = None
    total_debt: Optional[float] = None
    source_url: str
    submission_id: Optional[str] = None


class UpdateEvent(BaseModel):
    update_id: int
    orgnr: str
    timestamp: str
    change_type: str = "EnhetEndret"
    notes: Optional[str] = None


class CompanyProfile(BaseModel):
    orgnr: str = Field(..., description="9-digit Norwegian organization number")
    name: str = Field(..., description="Official legal entity name")
    org_form: str = Field("AS", description="Organization form code (e.g. AS, ASA, ENK)")
    org_form_description: str = Field("", description="Full organization form description")
    status: str = Field("Active", description="Legal active status (Active, In Liquidation, Bankrupt, Dissolved)")
    freshness_status: str = Field("CURRENT", description="Freshness status: CURRENT, STALE, NEEDS_SYNC")
    last_verified_at: str = Field(..., description="ISO8601 timestamp of last agent verification")
    last_modified_in_registry: Optional[str] = Field(None, description="Latest update timestamp from Brreg stream")
    latest_update_id: Optional[int] = Field(None, description="ID from Brreg oppdateringer stream")
    entity_match_score: float = Field(1.0, description="Confidence that facts belong to this exact entity")
    
    # Structured key facts
    foundation_date: Optional[str] = None
    registration_date: Optional[str] = None
    business_address: Optional[Dict[str, Any]] = None
    postal_address: Optional[Dict[str, Any]] = None
    industry_code: Optional[str] = None
    industry_description: Optional[str] = None
    employee_count: Optional[int] = None
    employee_registration_date: Optional[str] = None
    website_url: Optional[str] = None
    phone: Optional[str] = None
    is_vat_registered: Optional[bool] = None
    share_capital: Optional[float] = None
    share_capital_currency: Optional[str] = "NOK"
    is_part_of_group: Optional[bool] = None
    
    # Roles & Governance
    ceo_name: Optional[str] = None
    board_chair: Optional[str] = None
    auditor_name: Optional[str] = None
    key_roles: List[RoleItem] = Field(default_factory=list)
    
    # Financial Statements
    latest_financials: Optional[FinancialYearData] = None
    
    # Complete provenance-backed facts ledger
    facts: List[Fact] = Field(default_factory=list)
    
    # AI / Executive Synthesis
    executive_summary: Optional[str] = None
    risk_indicators: List[str] = Field(default_factory=list)
    
    # Audit & change history
    change_history: List[Dict[str, Any]] = Field(default_factory=list)
