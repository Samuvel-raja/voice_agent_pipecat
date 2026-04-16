from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class InterviewMode(str, Enum):
    general = "general"
    technical = "technical"
    final = "final"
    teach_coding = "teach_coding"


class CandidateDetails(BaseModel):
    name: str
    email: Optional[str] = None
    years_experience: Optional[float] = None
    role_applied: Optional[str] = None


class CompanyDetails(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    role_title: Optional[str] = None
    jd_summary: Optional[str] = None
    focus_areas: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)


class InterviewSessionConfig(BaseModel):
    mode: InterviewMode
    candidate: CandidateDetails
    company: Optional[CompanyDetails] = None
    questions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
