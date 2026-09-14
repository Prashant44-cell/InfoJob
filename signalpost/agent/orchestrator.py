"""
SignalPost Orchestrator Agent.
Coordinates sources, entity disambiguation, profile construction,
freshness evaluation, and AI briefing.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from signalpost.agent.ai_synthesizer import AISynthesizer
from signalpost.agent.entity_resolver import EntityResolver
from signalpost.agent.profile_builder import ProfileBuilder
from signalpost.agent.syncer import ProfileSyncer
from signalpost.core.models import CompanyProfile
from signalpost.core.validator import clean_orgnr, validate_norwegian_orgnr
from signalpost.sources.brreg_enhet import BrregEnhetSource
from signalpost.sources.brreg_regnskap import BrregRegnskapSource
from signalpost.sources.brreg_roller import BrregRollerSource
from signalpost.sources.brreg_updates import BrregUpdatesSource
from signalpost.sources.web_verifier import WebFootprintVerifier

logger = logging.getLogger(__name__)


class SignalPostAgent:
    """Autonomous agent for Norwegian company intelligence."""

    def __init__(
        self,
        enhet_src: Optional[BrregEnhetSource] = None,
        roller_src: Optional[BrregRollerSource] = None,
        regnskap_src: Optional[BrregRegnskapSource] = None,
        updates_src: Optional[BrregUpdatesSource] = None,
        web_verifier: Optional[WebFootprintVerifier] = None,
        ai_synthesizer: Optional[AISynthesizer] = None,
    ):
        self.enhet_src = enhet_src or BrregEnhetSource()
        self.roller_src = roller_src or BrregRollerSource()
        self.regnskap_src = regnskap_src or BrregRegnskapSource()
        self.updates_src = updates_src or BrregUpdatesSource()
        self.web_verifier = web_verifier or WebFootprintVerifier()
        self.resolver = EntityResolver()
        self.builder = ProfileBuilder(self.resolver)
        self.syncer = ProfileSyncer(self.updates_src)
        self.ai = ai_synthesizer or AISynthesizer()

    def process_orgnr(
        self, raw_orgnr: str, verify_web: bool = True, generate_summary: bool = True
    ) -> Tuple[bool, Optional[CompanyProfile], str]:
        """
        Executes complete agent lifecycle for a Norwegian organization number:
        1. Validate checksum (Modulo 11)
        2. Query permitted public registries
        3. Disambiguate facts and verify provenance
        4. Check freshness against update stream
        5. Generate AI executive briefing
        """
        cleaned = clean_orgnr(raw_orgnr)
        is_valid, val_reason = validate_norwegian_orgnr(cleaned)
        if not is_valid:
            return False, None, f"Input validation failed: {val_reason}"

        # 1. Fetch Enhetsregisteret (Core Legal Entity)
        enhet_data = self.enhet_src.fetch_enhet(cleaned)
        if not enhet_data:
            return False, None, f"Organization number {cleaned} not found in official Norwegian Enhetsregisteret."

        # 2. Fetch Roller (Governance & Board)
        roller_data = self.roller_src.fetch_roller(cleaned)

        # 3. Fetch Regnskapsregisteret (Financial Statements)
        regnskap_data = self.regnskap_src.fetch_accounts(cleaned)

        # 4. Fetch Updates (Registry delta stream)
        update_data = self.updates_src.get_latest_update_for_entity(cleaned)

        # 5. Fetch Web Footprint (if registered website exists)
        web_data = None
        if verify_web and enhet_data.get("hjemmeside"):
            web_data = self.web_verifier.verify_website(
                enhet_data["hjemmeside"], enhet_data.get("navn", ""), cleaned
            )

        # 6. Build Profile & Disambiguate Facts
        profile = self.builder.build(
            orgnr=cleaned,
            enhet_raw=enhet_data,
            roller_raw=roller_data,
            regnskap_raw=regnskap_data,
            update_raw=update_data,
            web_raw=web_data,
        )

        # 7. Freshness Evaluation
        fresh_status, _, fresh_reason = self.syncer.check_freshness(profile)
        profile.freshness_status = fresh_status

        # 8. AI / Deterministic Executive Briefing
        if generate_summary:
            profile.executive_summary = self.ai.synthesize(profile)

        return True, profile, "Successfully retrieved and verified company profile."

    def sync_existing_profile(self, profile: CompanyProfile) -> Tuple[CompanyProfile, bool, str]:
        """
        Refreshes an existing profile against live feeds, detecting changes.
        """
        fresh_status, latest_event, reason = self.syncer.check_freshness(profile)
        if fresh_status == "CURRENT":
            return profile, False, "Profile is already current."

        # Re-fetch and build
        ok, new_profile, msg = self.process_orgnr(profile.orgnr)
        if not ok or not new_profile:
            return profile, False, f"Sync re-fetch failed: {msg}"

        # Record changes
        self.syncer.record_sync_event(new_profile, sync_reason=reason)
        return new_profile, True, f"Profile successfully updated: {reason}"
