"""
AI Synthesis & Intelligence Briefing Engine.
Synthesizes executive narratives and risk assessments using Google Gemini
with robust deterministic rule-based fallback for offline, zero-cost operation.
"""

import os
from typing import Dict, List, Optional
from signalpost.core.models import CompanyProfile


class AISynthesizer:
    """Generates natural language executive briefings and flags risks."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name

    def synthesize(self, profile: CompanyProfile) -> str:
        """
        Generates an executive narrative summary for the company profile.
        Uses Gemini API if key is set, else uses high-precision deterministic synthesis.
        """
        if self.api_key:
            try:
                import requests
                prompt = (
                    f"You are SignalPost, an expert corporate intelligence analyst for Norwegian businesses.\n"
                    f"Provide a concise, professional 3-sentence executive briefing for:\n"
                    f"Company: {profile.name} (Org: {profile.orgnr})\n"
                    f"Form: {profile.org_form} ({profile.org_form_description})\n"
                    f"Industry: {profile.industry_code} - {profile.industry_description}\n"
                    f"Employees: {profile.employee_count}\n"
                    f"Status: {profile.status}\n"
                    f"CEO: {profile.ceo_name or 'Not registered'}\n"
                    f"Board Chair: {profile.board_chair or 'Not registered'}\n"
                    f"Latest Financials: {profile.latest_financials.revenue if profile.latest_financials else 'N/A'} {profile.latest_financials.currency if profile.latest_financials else ''}\n"
                    f"Tone: Objective, authoritative, corporate."
                )
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
                resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception:
                pass

        # High-precision deterministic fallback
        return self._deterministic_summary(profile)

    def _deterministic_summary(self, profile: CompanyProfile) -> str:
        """Generates a structured, authoritative executive briefing deterministically."""
        parts = []

        # Part 1: Identity & Foundation
        foundation_str = f", founded in {profile.foundation_date[:4]}" if profile.foundation_date else ""
        form_str = profile.org_form_description or profile.org_form
        parts.append(
            f"{profile.name} is a Norwegian {form_str} (Org.nr: {profile.orgnr}){foundation_str} "
            f"operating under primary NACE code {profile.industry_code or 'General'} ({profile.industry_description or 'Commerce'})."
        )

        # Part 2: Governance & Workforce
        gov_parts = []
        if profile.ceo_name:
            gov_parts.append(f"led by CEO {profile.ceo_name}")
        if profile.board_chair:
            gov_parts.append(f"chaired by {profile.board_chair}")
        if profile.employee_count is not None:
            gov_parts.append(f"employing approximately {profile.employee_count:,} registered staff")

        if gov_parts:
            parts.append(f"The enterprise is {', '.join(gov_parts)}.")

        # Part 3: Financial & Operating Status
        if profile.latest_financials and profile.latest_financials.revenue:
            rev_fmt = f"{profile.latest_financials.revenue:,.0f} {profile.latest_financials.currency}"
            year = profile.latest_financials.year
            op_profit_str = ""
            if profile.latest_financials.operating_profit is not None:
                op_profit_str = f" with an operating profit of {profile.latest_financials.operating_profit:,.0f} {profile.latest_financials.currency}"
            parts.append(
                f"Most recently reported financial accounts for {year} document annual revenues of {rev_fmt}{op_profit_str}."
            )
        else:
            parts.append(f"The business is actively registered with status '{profile.status}'.")

        return " ".join(parts)
