from typing import List
from models.opportunity import ParsedOpportunity, ActionItem
from models.profile import StudentProfile


class ChecklistService:
    """
    Action Checklist & Next-Steps Generator.
    Converts parsed opportunity requirements and deadlines into personalized,
    actionable to-do checklist items for the student.
    """

    @classmethod
    def generate_checklist(cls, opportunity: ParsedOpportunity, profile: StudentProfile) -> List[ActionItem]:
        items: List[ActionItem] = []

        # 1. Document Preparation tasks (personalized using student profile)
        if opportunity.required_documents:
            for doc in opportunity.required_documents:
                doc_clean = doc.strip()
                doc_lower = doc_clean.lower()

                if "transcript" in doc_lower:
                    items.append(ActionItem(
                        task=f"Request / Download Official Transcript (Current CGPA: {profile.cgpa:.2f})",
                        category="Document"
                    ))
                elif "resume" in doc_lower or "cv" in doc_lower:
                    skills_snippet = ", ".join(profile.skills[:2]) if profile.skills else "skills"
                    items.append(ActionItem(
                        task=f"Tailor Resume highlighting relevant {skills_snippet} projects",
                        category="Document"
                    ))
                elif "statement of purpose" in doc_lower or "sop" in doc_lower:
                    items.append(ActionItem(
                        task=f"Draft & proofread Statement of Purpose ({opportunity.organization})",
                        category="Document"
                    ))
                elif "proposal" in doc_lower or "project abstract" in doc_lower:
                    items.append(ActionItem(
                        task="Draft Project Proposal following org guidelines",
                        category="Document"
                    ))
                elif "recommendation" in doc_lower or "lor" in doc_lower:
                    items.append(ActionItem(
                        task="Contact department professors for 2 Letters of Recommendation",
                        category="Document"
                    ))
                elif "salary" in doc_lower or "income" in doc_lower:
                    items.append(ActionItem(
                        task="Obtain Guardian Income Certificate / Salary Slips for financial review",
                        category="Document"
                    ))
                elif "id" in doc_lower or "cnic" in doc_lower:
                    items.append(ActionItem(
                        task="Prepare scanned copy of Student ID / CNIC",
                        category="Document"
                    ))
                elif "github" in doc_lower or "portfolio" in doc_lower:
                    items.append(ActionItem(
                        task="Update GitHub profile and pin top portfolio repositories",
                        category="Document"
                    ))
                else:
                    items.append(ActionItem(
                        task=f"Prepare required document: {doc_clean}",
                        category="Document"
                    ))
        else:
            items.append(ActionItem(
                task="Prepare standard academic CV and portfolio link",
                category="Document"
            ))

        # 2. Portal & Submission Task
        if opportunity.application_link and opportunity.application_link.startswith("http"):
            items.append(ActionItem(
                task=f"Submit application on official registration portal ({opportunity.organization or 'Host'})",
                category="Application"
            ))
        elif opportunity.contact_email and "no-reply" not in opportunity.contact_email.lower() and "noreply" not in opportunity.contact_email.lower():
            items.append(ActionItem(
                task=f"Send application email with attachments to {opportunity.contact_email}",
                category="Application"
            ))
        else:
            items.append(ActionItem(
                task=f"Complete application / registration via {opportunity.organization or 'official career portal'}",
                category="Application"
            ))


        # 3. Calendar & Deadline Task
        if opportunity.deadline:
            items.append(ActionItem(
                task=f"Set calendar reminder for submission deadline: {opportunity.deadline}",
                category="Calendar"
            ))

        return items
