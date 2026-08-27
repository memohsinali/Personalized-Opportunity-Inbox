import re
from datetime import datetime, date
from typing import List, Tuple
from models.profile import StudentProfile
from models.opportunity import ParsedOpportunity, ScoringBreakdown, RankedOpportunity
from config import WEIGHT_PROFILE_FIT, WEIGHT_URGENCY, WEIGHT_COMPLETENESS


class ScoringEngine:
    """
    Deterministic Mathematical Scoring & Ranking Engine.
    Evaluates:
      1. Profile Fit Score (Weight: 40%)
      2. Urgency Score (Weight: 35%)
      3. Completeness & Impact Score (Weight: 25%)
    Deducts penalty for ineligibility and generates evidence-backed explanations.
    """

    REFERENCE_DATE = date(2026, 3, 1)  # Fixed benchmark reference date for deterministic testing

    @classmethod
    def calculate_urgency_score(cls, opportunity: ParsedOpportunity) -> Tuple[float, str, int]:
        """
        Calculates Urgency Score (0 - 100) based on days until deadline.
        Brackets:
          - 0 to 2 days: 100 pts (Critical Urgency)
          - 3 to 7 days: 80 pts (High Urgency)
          - 8 to 14 days: 55 pts (Medium Urgency)
          - 15+ days: 30 pts (Low Urgency)
          - Past deadline: -1000 pts (Expired)
        """
        days_left = opportunity.days_until_deadline
        
        # Try parsing deadline string if days_until_deadline is missing
        if days_left is None and opportunity.deadline:
            try:
                dl_date = datetime.strptime(opportunity.deadline[:10], "%Y-%m-%d").date()
                days_left = (dl_date - cls.REFERENCE_DATE).days
            except Exception:
                days_left = 14  # Default fallback

        if days_left is None:
            return 40.0, "No specific deadline provided (moderate urgency)", 14

        if days_left < 0:
            return -1000.0, f"Deadline passed {abs(days_left)} days ago (EXPIRED)", days_left
        elif days_left <= 2:
            return 100.0, f"Critical Urgency: Closes in {days_left} day(s) (🚨 Immediate Action Required)", days_left
        elif days_left <= 7:
            return 80.0, f"High Urgency: Closes in {days_left} days (⚡ Prepare documents this week)", days_left
        elif days_left <= 14:
            return 55.0, f"Medium Urgency: Closes in {days_left} days (⏳ Two weeks remaining)", days_left
        else:
            return 30.0, f"Low Urgency: Closes in {days_left} days (📅 Planned for later)", days_left

    @classmethod
    def calculate_profile_fit_score(cls, profile: StudentProfile, opportunity: ParsedOpportunity) -> Tuple[float, List[str], List[str], bool]:
        """
        Calculates Profile Fit Score (0 - 100) across 4 dimensions (25 pts each):
          1. CGPA requirement match
          2. Major / Degree program match
          3. Skills & Interests overlap
          4. Preferred Opportunity Type match
        """
        score = 0.0
        fit_reasons = []
        ineligibility_reasons = []
        is_eligible = True

        eligibility = opportunity.eligibility

        # 1. CGPA Match (25 pts)
        if eligibility.min_cgpa is not None and eligibility.min_cgpa > 0:
            if profile.cgpa is None or profile.cgpa <= 0.0:
                is_eligible = False
                ineligibility_reasons.append(f"Minimum CGPA of {eligibility.min_cgpa:.2f} required (CGPA unassigned in profile)")
            elif profile.cgpa >= eligibility.min_cgpa:
                score += 25.0
                fit_reasons.append(f"CGPA {profile.cgpa:.2f} meets minimum requirement of {eligibility.min_cgpa:.2f} (+25 pts)")
            else:
                is_eligible = False
                ineligibility_reasons.append(f"Student CGPA ({profile.cgpa:.2f}) is below minimum required {eligibility.min_cgpa:.2f}")
        else:
            score += 25.0
            fit_reasons.append("No minimum CGPA requirement (+25 pts)")

        # 2. Major / Degree Program Match (25 pts)
        if eligibility.eligible_majors:
            major_matched = False
            for m in eligibility.eligible_majors:
                # Partial match (e.g. "Computer Science" in "BS Computer Science")
                if m.lower() in profile.degree.lower() or profile.degree.lower() in m.lower():
                    major_matched = True
                    break
            
            if major_matched:
                score += 25.0
                fit_reasons.append(f"Student major ({profile.degree}) directly matches target field (+25 pts)")
            else:
                is_eligible = False
                ineligibility_reasons.append(f"Degree ({profile.degree}) does not match required fields: {', '.join(eligibility.eligible_majors)}")
        else:
            score += 25.0
            fit_reasons.append("Open to all degrees & majors (+25 pts)")

        # 3. Semester Check (Modifier)
        if eligibility.eligible_semesters:
            if profile.semester in eligibility.eligible_semesters:
                fit_reasons.append(f"Current semester ({profile.semester}) is eligible")
            else:
                is_eligible = False
                ineligibility_reasons.append(f"Semester {profile.semester} is not in target semesters: {eligibility.eligible_semesters}")

        # 4. Financial Need Check (if applicable)
        if eligibility.financial_need_required:
            if profile.financial_need:
                score = min(100.0, score + 10.0)
                fit_reasons.append("Student demonstrated financial need aligns with scholarship (+10 pts bonus)")
            else:
                fit_reasons.append("Opportunity prioritizes financial need")

        # 5. Skills & Interests Overlap (25 pts)
        text_corpus = f"{opportunity.title} {opportunity.summary} {opportunity.benefits or ''} {opportunity.eligibility.other_requirements or ''}".lower()
        matched_skills = [s for s in profile.skills if s.lower() in text_corpus]
        matched_interests = [i for i in profile.interests if i.lower() in text_corpus]

        total_matches = len(matched_skills) + len(matched_interests)
        if total_matches >= 3:
            score += 25.0
            fit_reasons.append(f"Strong skill/interest match ({', '.join(matched_skills + matched_interests)}) (+25 pts)")
        elif total_matches >= 1:
            score += 15.0
            fit_reasons.append(f"Partial skill/interest match ({', '.join(matched_skills + matched_interests)}) (+15 pts)")
        else:
            score += 5.0
            fit_reasons.append("General opportunity with minimal skill overlap (+5 pts)")

        # 6. Preferred Opportunity Type Match (25 pts)
        opp_type_lower = opportunity.opportunity_type.lower()
        type_matched = any(p.lower() in opp_type_lower or opp_type_lower in p.lower() for p in profile.preferred_types)
        if type_matched:
            score += 25.0
            fit_reasons.append(f"Opportunity type '{opportunity.opportunity_type}' matches student preference (+25 pts)")
        else:
            score += 10.0
            fit_reasons.append(f"Opportunity type '{opportunity.opportunity_type}' is secondary preference (+10 pts)")

        # Cap fit score at 100
        score = min(100.0, max(0.0, score))
        return score, fit_reasons, ineligibility_reasons, is_eligible

    @classmethod
    def calculate_completeness_score(cls, opportunity: ParsedOpportunity) -> Tuple[float, List[str]]:
        """
        Calculates Completeness & Actionability Score (0 - 100):
          - Clear application URL / contact: 40 pts
          - Tangible perks / stipend / award: 30 pts
          - Clear required documents checklist: 30 pts
        """
        score = 0.0
        reasons = []

        # 1. Actionable link or contact (40 pts)
        if opportunity.application_link and opportunity.application_link.startswith("http"):
            score += 40.0
            reasons.append("Direct verified application portal URL available (+40 pts)")
        elif opportunity.contact_email:
            score += 25.0
            reasons.append("Contact email provided for application (+25 pts)")
        else:
            score += 10.0
            reasons.append("General announcement without direct URL (+10 pts)")

        # 2. Tangible Perks / Benefits (30 pts)
        if opportunity.benefits and len(opportunity.benefits.strip()) > 5:
            score += 30.0
            reasons.append(f"Explicit benefits identified ({opportunity.benefits[:40]}...) (+30 pts)")
        else:
            score += 10.0
            reasons.append("Standard academic/networking benefit (+10 pts)")

        # 3. Clear Documentation Checklist (30 pts)
        if opportunity.required_documents and len(opportunity.required_documents) > 0:
            score += 30.0
            reasons.append(f"{len(opportunity.required_documents)} specific required documents enumerated (+30 pts)")
        else:
            score += 10.0
            reasons.append("General application without explicit document list (+10 pts)")

        score = min(100.0, max(0.0, score))
        return score, reasons

    @classmethod
    def rank_opportunities(cls, profile: StudentProfile, opportunities: List[ParsedOpportunity]) -> List[RankedOpportunity]:
        """
        Takes parsed opportunities, applies the deterministic scoring formula,
        sorts by final composite score, and attaches evidence tags and action checklists.
        """
        valid_opportunities = [opp for opp in opportunities if opp.is_opportunity]
        ranked_list: List[RankedOpportunity] = []

        for opp in valid_opportunities:
            # 1. Fit Score
            fit_score, fit_reasons, ineligibility_reasons, is_eligible = cls.calculate_profile_fit_score(profile, opp)
            
            # 2. Urgency Score
            urgency_score, urgency_reason, days_left = cls.calculate_urgency_score(opp)
            
            # 3. Completeness Score
            completeness_score, completeness_reasons = cls.calculate_completeness_score(opp)

            # Ineligibility Penalty
            penalty = 0.0
            if not is_eligible:
                penalty = 45.0  # Heavy penalty for violating strict hard criteria (CGPA/Degree/Semester)

            # Expired check
            if urgency_score < 0:
                final_score = -100.0
            else:
                weighted_fit = WEIGHT_PROFILE_FIT * fit_score
                weighted_urgency = WEIGHT_URGENCY * urgency_score
                weighted_completeness = WEIGHT_COMPLETENESS * completeness_score
                final_score = max(0.0, round((weighted_fit + weighted_urgency + weighted_completeness) - penalty, 2))

            scoring_breakdown = ScoringBreakdown(
                fit_score=round(fit_score, 1),
                fit_reasons=fit_reasons,
                urgency_score=round(urgency_score, 1),
                urgency_reason=urgency_reason,
                completeness_score=round(completeness_score, 1),
                completeness_reasons=completeness_reasons,
                ineligible_penalty=penalty,
                is_eligible=is_eligible,
                ineligibility_reasons=ineligibility_reasons,
                final_score=final_score,
            )

            # Generate evidence tag
            if urgency_score < 0:
                evidence_tag = "❌ Deadline Expired: Submissions closed"
            elif not is_eligible:
                evidence_tag = f"⚠️ Ineligibility Alert: {ineligibility_reasons[0] if ineligibility_reasons else 'Criteria mismatch'}"
            elif fit_score >= 85 and urgency_score >= 80:
                evidence_tag = f"🔥 Top Priority Match: Outstanding profile alignment & closes in {days_left}d"
            elif fit_score >= 80:
                evidence_tag = f"⭐ High Fit Match: Strong degree and skill alignment ({int(fit_score)}% fit)"
            elif urgency_score >= 80:
                evidence_tag = f"🚨 Action Required: High urgency closing in {days_left}d"
            else:
                evidence_tag = f"📋 Recommended: Good general opportunity match ({int(final_score)}% score)"

            # Fallback checklist if checklist_service is not yet imported
            action_checklist = []
            try:
                from .checklist_service import ChecklistService
                action_checklist = ChecklistService.generate_checklist(opp, profile)
            except Exception:
                from models.opportunity import ActionItem
                action_checklist = [
                    ActionItem(task=f"Review requirements for {opp.title}", category="Application")
                ]

            ranked_list.append(
                RankedOpportunity(
                    rank=0,  # Assigned after sorting
                    opportunity=opp,
                    scoring=scoring_breakdown,
                    evidence_tag=evidence_tag,
                    action_checklist=action_checklist,
                )
            )

        # Sort descending by final score
        ranked_list.sort(key=lambda x: x.scoring.final_score, reverse=True)

        # Assign 1-indexed ranks
        for idx, item in enumerate(ranked_list, start=1):
            item.rank = idx

        return ranked_list
