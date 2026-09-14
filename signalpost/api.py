"""
REST API and Web Dashboard Backend for SignalPost Agent.
Powered by FastAPI.
"""

import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from signalpost.agent.orchestrator import SignalPostAgent
from signalpost.core.validator import validate_norwegian_orgnr
from signalpost.db.storage import ProfileStorage

app = FastAPI(
    title="SignalPost API",
    description="Autonomous Norwegian Company Intelligence Agent API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = SignalPostAgent()
storage = ProfileStorage()

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "SignalPost Agent", "version": "1.0.0"}


@app.get("/api/company/{orgnr}")
def get_company_profile(orgnr: str, force_refresh: bool = False):
    """
    Given a Norwegian company number, runs the SignalPost agent
    to fetch, disambiguate, and return verified facts with source links and dates.
    """
    is_valid, reason = validate_norwegian_orgnr(orgnr)
    if not is_valid:
        raise HTTPException(status_code=400, detail=reason)

    if not force_refresh:
        cached = storage.get_profile(orgnr)
        if cached:
            return cached

    ok, profile, msg = agent.process_orgnr(orgnr)
    if not ok or not profile:
        raise HTTPException(status_code=404, detail=msg)

    storage.save_profile(profile)
    return profile


@app.post("/api/company/{orgnr}/sync")
def sync_company_profile(orgnr: str):
    """
    Checks the Brønnøysundregistrene delta stream and refreshes
    the company profile to keep it current.
    """
    cached = storage.get_profile(orgnr)
    if not cached:
        ok, profile, msg = agent.process_orgnr(orgnr)
        if not ok or not profile:
            raise HTTPException(status_code=404, detail=msg)
        storage.save_profile(profile)
        return {"updated": True, "reason": "Fresh initial lookup performed.", "profile": profile}

    updated_profile, was_updated, reason = agent.sync_existing_profile(cached)
    storage.save_profile(updated_profile)
    return {
        "updated": was_updated,
        "reason": reason,
        "freshness_status": updated_profile.freshness_status,
        "profile": updated_profile,
    }


@app.get("/api/profiles")
def list_profiles(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
):
    """Returns paginated company profiles from the pre-harvested dataset."""
    total = storage.count_profiles()
    profiles = storage.list_profiles(limit=limit, offset=offset, search=search)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "profiles": profiles,
    }


@app.get("/api/stats")
def get_stats():
    """Returns high-level statistics across the harvested company dataset."""
    total = storage.count_profiles()
    sample = storage.list_profiles(limit=1000, offset=0)
    
    total_employees = sum(p.employee_count or 0 for p in sample)
    total_facts = sum(len(p.facts) for p in sample)
    active_count = sum(1 for p in sample if p.status == "Active / Operating" or "Active" in p.status)

    return {
        "total_profiles": total,
        "total_facts_verified": total_facts,
        "total_employees_represented": total_employees,
        "active_companies": active_count,
        "sources_monitored": [
            "Brønnøysundregistrene (Enhetsregisteret)",
            "Brønnøysundregistrene (Roller & Styre)",
            "Brønnøysundregistrene (Regnskapsregisteret)",
            "Brønnøysundregistrene (Oppdateringer Stream)",
            "Official Company Domains & Web Presence",
        ],
    }


# Mount frontend and data static files
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
if os.path.exists(DATA_DIR):
    app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

if os.path.exists(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/")
    def serve_ui():
        return FileResponse(os.path.join(WEB_DIR, "index.html"))
