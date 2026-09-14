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
            "Apify Real-Time Actor Crawler",
        ],
    }


@app.get("/api/apify/search")
def apify_search(query: str = Query(..., min_length=1)):
    """
    Search and enrich company data using the Apify actor source
    alongside pre-harvested Brønnøysundregistrene data.
    """
    from signalpost.sources.apify_source import ApifyCompanySource

    clean_query = query.strip()
    digits_only = "".join(filter(str.isdigit, clean_query))

    matched_profile = None
    if len(digits_only) == 9:
        is_valid, _ = validate_norwegian_orgnr(digits_only)
        if is_valid:
            matched_profile = storage.get_profile(digits_only)
            if not matched_profile:
                ok, prof, _ = agent.process_orgnr(digits_only)
                if ok and prof:
                    storage.save_profile(prof)
                    matched_profile = prof

    if not matched_profile:
        matches = storage.list_profiles(limit=5, search=clean_query)
        if matches:
            matched_profile = matches[0]

    apify_source = ApifyCompanySource()
    actor_results = apify_source.fetch_company_realtime(clean_query)

    return {
        "query": clean_query,
        "matched_profile": matched_profile,
        "apify_actor_id": apify_source.actor_id,
        "apify_results": actor_results,
        "status": "success",
    }


@app.post("/api/agent/query")
def agent_query(payload: dict):
    """
    Direct Q&A Copilot answering queries grounded in the official company facts.
    """
    orgnr = payload.get("orgnr", "").strip()
    question = payload.get("question", "").strip()

    if not orgnr or not question:
        raise HTTPException(status_code=400, detail="Both 'orgnr' and 'question' are required.")

    profile = storage.get_profile(orgnr)
    if not profile:
        ok, profile, msg = agent.process_orgnr(orgnr)
        if not ok or not profile:
            raise HTTPException(status_code=404, detail=f"Company {orgnr} not found.")

    q_lower = question.lower()
    answer = ""
    citations = []

    if any(w in q_lower for w in ["ceo", "daglig", "manager", "leader"]):
        ceo = profile.ceo_name or "Not registered"
        answer = f"The Chief Executive Officer (Daglig Leder) of {profile.name} is {ceo}."
        citations.append({"source": "Brønnøysundregistrene (Roller)", "key": "ceo", "value": ceo})
    elif any(w in q_lower for w in ["chair", "board", "styreleder"]):
        chair = profile.board_chair or "Not registered"
        answer = f"The Board Chair (Styreleder) of {profile.name} is {chair}."
        citations.append({"source": "Brønnøysundregistrene (Roller)", "key": "board_chair", "value": chair})
    elif any(w in q_lower for w in ["revenue", "turnover", "profit", "ebit", "financial", "accounts"]):
        if profile.latest_financials and profile.latest_financials.revenue:
            f = profile.latest_financials
            answer = (
                f"For the audited fiscal year {f.year}, {profile.name} reported turnover/revenue of "
                f"{f.revenue:,.0f} {f.currency}, operating profit (EBIT) of {f.operating_profit:,.0f} {f.currency}, "
                f"and total equity of {f.total_equity:,.0f} {f.currency}."
            )
            citations.append({"source": "Brønnøysundregistrene (Regnskapsregisteret)", "year": f.year})
        else:
            answer = f"Audited annual financial statements for {profile.name} are pending filing in Regnskapsregisteret."
    elif any(w in q_lower for w in ["employee", "staff", "workers", "headcount"]):
        cnt = profile.employee_count or 0
        answer = f"{profile.name} has {cnt:,} registered employees according to the Norwegian State Register of Employers and Employees (Aa-registeret / NAV)."
        citations.append({"source": "NAV / Aa-registeret via Enhetsregisteret", "count": cnt})
    elif any(w in q_lower for w in ["vat", "mva", "tax"]):
        vat_str = "is registered for VAT (Merverdiavgiftsregisteret)" if profile.is_vat_registered else "is not currently registered for VAT / MVA"
        answer = f"{profile.name} {vat_str}."
        citations.append({"source": "Skatteetaten / Enhetsregisteret", "is_vat_registered": profile.is_vat_registered})
    elif any(w in q_lower for w in ["address", "location", "city", "where"]):
        addr = profile.business_address
        if addr:
            answer = f"{profile.name} is officially registered at {addr.adresse or ''}, {addr.postnummer or ''} {addr.poststed or ''}, Norway."
        else:
            answer = f"Registered address for {profile.name} is on file in Brønnøysundregistrene."
        citations.append({"source": "Brønnøysundregistrene Enhetsregisteret"})
    else:
        # High precision synthesis fallback
        answer = agent.ai.synthesize(profile)
        citations.append({"source": "SignalPost AI Synthesizer & Multi-Registry Grounding Engine"})

    return {
        "orgnr": orgnr,
        "company_name": profile.name,
        "question": question,
        "answer": answer,
        "citations": citations,
        "freshness_status": profile.freshness_status,
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

    @app.get("/styles.css")
    def serve_styles():
        return FileResponse(os.path.join(WEB_DIR, "styles.css"), media_type="text/css")

    @app.get("/app.js")
    def serve_app_js():
        return FileResponse(os.path.join(WEB_DIR, "app.js"), media_type="application/javascript")

