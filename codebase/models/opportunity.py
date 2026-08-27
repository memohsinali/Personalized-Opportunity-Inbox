from typing import List, Optional
from pydantic import BaseModel, Field


class EligibilityCriteria(BaseModel):
    """Structured eligibility constraints extracted from email text."""
    min_cgpa: Optional[float] = Field(default=None, description="Minimum CGPA required (if specified)")
    eligible_majors: List[str] = Field(default_factory=list, description="Target majors/degrees or empty if open to all")
    eligible_semesters: List[int] = Field(default_factory=list, description="Target semesters or empty if open to all")
    financial_need_required: bool = Field(default=False, description="Whether financial need is required")
    other_requirements: Optional[str] = Field(default=None, description="Other restrictions or eligibility notes")


class ParsedOpportunity(BaseModel):
    """Structured extraction output from raw email text."""
    email_id: str = Field(description="Unique email identifier")
    is_opportunity: bool = Field(description="True if email contains a genuine opportunity, False if spam/general notice")
    rejection_reason: Optional[str] = Field(default=None, description="Reason if email was classified as non-opportunity")
    
    title: str = Field(default="", description="Name or title of the opportunity")
    organization: str = Field(default="", description="Host organization, university, or company")
    opportunity_type: str = Field(default="Other", description="Scholarship, Internship, Hackathon / Competition, Research / Fellowship, Workshop / Conference, Job")
    
    deadline: Optional[str] = Field(default=None, description="ISO format date string (e.g. 2026-03-15)")
    days_until_deadline: Optional[int] = Field(default=None, description="Estimated days remaining until deadline")
    
    eligibility: EligibilityCriteria = Field(default_factory=EligibilityCriteria, description="Eligibility criteria parsed from text")
    required_documents: List[str] = Field(default_factory=list, description="Documents required (e.g. Resume, Transcript, SOP)")
    benefits: Optional[str] = Field(default=None, description="Stipend, prize money, travel grant, or learning benefits")
    
    application_link: Optional[str] = Field(default=None, description="URL to apply or view details")
    contact_email: Optional[str] = Field(default=None, description="Contact email for queries")
    summary: str = Field(default="", description="Concise 1-2 sentence overview of the opportunity")
    raw_snippet: Optional[str] = Field(default=None, description="Relevant excerpt from original email")


class ScoringBreakdown(BaseModel):
    """Transparent deterministic score breakdown for judge inspectability."""
    fit_score: float = Field(default=0.0, description="0 to 100 Profile Fit Score (Weight: 40%)")
    fit_reasons: List[str] = Field(default_factory=list, description="Bullet reasons for fit score")
    
    urgency_score: float = Field(default=0.0, description="0 to 100 Urgency Score (Weight: 35%)")
    urgency_reason: str = Field(default="", description="Reason for urgency score")
    
    completeness_score: float = Field(default=0.0, description="0 to 100 Completeness/Quality Score (Weight: 25%)")
    completeness_reasons: List[str] = Field(default_factory=list, description="Bullet reasons for completeness score")
    
    ineligible_penalty: float = Field(default=0.0, description="Penalty deducted if student violates strict criteria")
    is_eligible: bool = Field(default=True, description="Whether student meets minimum mandatory criteria")
    ineligibility_reasons: List[str] = Field(default_factory=list, description="Specific criteria student failed")
    
    final_score: float = Field(default=0.0, description="Weighted final composite priority score (0 to 100)")


class ActionItem(BaseModel):
    """Actionable to-do checklist item for the student."""
    task: str = Field(description="Action task description")
    category: str = Field(default="Document", description="Category: Document, Application, Calendar, or Contact")
    is_completed: bool = Field(default=False, description="Checkbox state")


class RankedOpportunity(BaseModel):
    """Final ranked opportunity presentation model for the dashboard."""
    rank: int = Field(description="Priority rank (#1 is top)")
    opportunity: ParsedOpportunity
    scoring: ScoringBreakdown
    evidence_tag: str = Field(description="One-line human readable rationale for why this is ranked here")
    action_checklist: List[ActionItem] = Field(default_factory=list, description="To-do checklist for student")
