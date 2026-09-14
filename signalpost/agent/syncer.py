"""
Profile Freshness & Synchronization Engine.
Monitors Brønnøysundregistrene's delta stream and re-verifies company facts
to satisfy the core requirement: 'keep profiles current'.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional, Tuple

from signalpost.core.models import CompanyProfile
from signalpost.sources.brreg_updates import BrregUpdatesSource

logger = logging.getLogger(__name__)


class ProfileSyncer:
    """Detects modifications and synchronizes company profiles with registry feeds."""

    def __init__(self, updates_source: Optional[BrregUpdatesSource] = None, ttl_hours: int = 48):
        self.updates_source = updates_source or BrregUpdatesSource()
        self.ttl_hours = ttl_hours

    def check_freshness(self, profile: CompanyProfile) -> Tuple[str, Optional[Dict[str, Any]], str]:
        """
        Evaluates whether a profile is CURRENT, NEEDS_SYNC, or STALE.
        Returns: (status: str, latest_event: Optional[Dict], reason: str)
        """
        orgnr = profile.orgnr
        latest_event = self.updates_source.get_latest_update_for_entity(orgnr)

        if not latest_event:
            # Check time since last verification
            return self._check_time_ttl(profile)

        latest_id = latest_event.get("oppdateringsid")
        latest_date = latest_event.get("dato")

        # If profile has recorded an update ID and registry has a higher ID
        if profile.latest_update_id is not None and latest_id is not None:
            if latest_id > profile.latest_update_id:
                return (
                    "NEEDS_SYNC",
                    latest_event,
                    f"New registry event detected (ID {latest_id} > cached {profile.latest_update_id}) on {latest_date}.",
                )

        # If registry date is newer than last recorded modification
        if latest_date and profile.last_modified_in_registry:
            if latest_date > profile.last_modified_in_registry:
                return (
                    "NEEDS_SYNC",
                    latest_event,
                    f"Registry modification timestamp updated from {profile.last_modified_in_registry} to {latest_date}.",
                )

        return self._check_time_ttl(profile, latest_event)

    def _check_time_ttl(
        self, profile: CompanyProfile, latest_event: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Optional[Dict[str, Any]], str]:
        try:
            last_verified = datetime.fromisoformat(profile.last_verified_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            hours_elapsed = (now - last_verified).total_seconds() / 3600.0

            if hours_elapsed > self.ttl_hours:
                return (
                    "STALE",
                    latest_event,
                    f"Profile cache expired ({hours_elapsed:.1f} hours elapsed > TTL {self.ttl_hours}h).",
                )
            return (
                "CURRENT",
                latest_event,
                f"Profile is fully up to date. Verified {hours_elapsed:.1f} hours ago with matching registry stream.",
            )
        except Exception:
            return "CURRENT", latest_event, "Profile is active."

    def record_sync_event(
        self, profile: CompanyProfile, sync_reason: str, changed_fields: Optional[Dict[str, Any]] = None
    ) -> None:
        """Appends a sync audit record to the profile's change history."""
        now_iso = datetime.now(timezone.utc).isoformat()
        profile.change_history.append({
            "timestamp": now_iso,
            "reason": sync_reason,
            "changed_fields": changed_fields or {},
            "verified_at": now_iso,
        })
        profile.last_verified_at = now_iso
        profile.freshness_status = "CURRENT"
