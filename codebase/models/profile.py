from typing import List, Optional
from pydantic import BaseModel, Field


class StudentProfile(BaseModel):
    """Structured form-based student profile as specified in the hackathon competition guidelines."""
    student_id: str = Field(default="student_001", description="Unique identifier for the student")
    name: str = Field(default="Student User", description="Student's full name")
    degree: str = Field(default="BS Computer Science", description="Degree / Major (e.g., BS Computer Science, BBA)")
    semester: int = Field(default=6, ge=1, le=8, description="Current semester (1 to 8)")
    cgpa: Optional[float] = Field(default=None, ge=0.0, le=4.0, description="Current Cumulative GPA (0.00 to 4.00), None if unassigned")
    skills: List[str] = Field(
        default_factory=lambda: ["Python", "Machine Learning", "FastAPI", "Data Analysis"],
        description="Key technical or professional skills"
    )
    interests: List[str] = Field(
        default_factory=lambda: ["Artificial Intelligence", "Software Engineering", "Open Source"],
        description="Career domains and interests"
    )
    preferred_types: List[str] = Field(
        default_factory=lambda: ["Internship", "Scholarship", "Research / Fellowship", "Hackathon / Competition"],
        description="Preferred opportunity categories"
    )
    financial_need: bool = Field(
        default=False,
        description="Whether the student has high financial need for need-based scholarships"
    )
    location_preference: str = Field(
        default="Any (Remote or On-site)",
        description="Location preference (e.g. Remote, Lahore, Islamabad, Global)"
    )
    past_experience: Optional[str] = Field(
        default="Built ML models and fullstack web apps. Previous summer intern at tech firm.",
        description="Brief summary of past experience or projects"
    )
