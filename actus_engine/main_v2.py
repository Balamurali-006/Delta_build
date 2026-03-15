# =============================================================================
# main.py  —  FinTwin Component 1
# Pipeline: Contract (PDF / text)  →  Groq  →  ACTUS JSON  →  Cash Flows
#
# Your existing actus_simulation.py already works.
# This backend wraps it with an API so any frontend can call it.
#
# Endpoints
# ─────────────────────────────────────────────────────────────────────
#  POST /parse-contract      raw text  → ACTUS JSON
#  POST /parse-pdf           PDF file  → ACTUS JSON
#  POST /simulate            ACTUS JSON → cash flows (uses awesome_actus_lib)
#  POST /full-pipeline       text/PDF  → ACTUS JSON + cash flows in one call
#  GET  /health
# =============================================================================

import os
import io
import json
import re
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import pdfplumber
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

# ── your existing simulation code ──────────────────────────────────────────
from awesome_actus_lib import ANN, PAM, LAM, PublicActusService

AWESOME_ACTUS_AVAILABLE = True

load_dotenv()

# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

app = FastAPI(
    title="FinTwin — Contract → ACTUS → Cash Flows",
    description="""
Upload any financial contract → AI extracts ACTUS terms → simulate cash flows.

**Pipeline:**
1. You upload a contract (PDF or raw text)
2. Groq (Llama-3.3-70b) reads it and extracts structured ACTUS fields
3. The ACTUS JSON is fed into `awesome_actus_lib` (your existing simulation)
4. You get back a full cash flow schedule as a JSON array
""",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Groq client (singleton)
# ---------------------------------------------------------------------------
_groq_client: Optional[Groq] = None

def get_groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set in environment / .env")
        _groq_client = Groq(api_key=api_key)
        log.info("Groq client initialised")
    return _groq_client



# =============================================================================
# ── Pydantic models ──────────────────────────────────────────────────────────
# =============================================================================

class ParseTextRequest(BaseModel):
    text: str                        # raw contract text to parse
    contract_id: str = "contract01"  # optional ID for the ACTUS object


class SimulateRequest(BaseModel):
    """
    Pass in the ACTUS JSON that came back from /parse-contract or
    /parse-pdf, or build it yourself.
    """
    actus_json: dict
    contract_id: str = "contract01"


class FullPipelineTextRequest(BaseModel):
    text: str
    contract_id: str = "contract01"


# =============================================================================
# ── GROQ PROMPT ──────────────────────────────────────────────────────────────
# =============================================================================

SYSTEM_PROMPT = """
You are a financial contract analysis expert specialising in ACTUS
(Algorithmic Contract Types Unified Standards).

Your task is to read the contract text and output a SINGLE valid JSON object
containing the ACTUS fields required to simulate cash flows using the
Python library `awesome_actus_lib`.

─── ACTUS CONTRACT TYPE SELECTION ───────────────────────────────────────────
Choose the best match:

  PAM  – Principal At Maturity
         Interest paid periodically; full principal repaid at maturity.
         Use for: bullet loans, working-capital loans, corporate bonds.

  ANN  – Annuity
         Fixed equal payments (EMI) covering both interest and principal.
         Balance reaches zero at maturity.
         Use for: home loans, car loans, retail/SME EMI loans.

  LAM  – Linear Amortiser
         Principal reduced by equal amounts each period; interest on
         remaining balance (payments decrease over time).
         Use for: agriculture loans, declining-balance term loans.

─── FIELD EXTRACTION RULES ──────────────────────────────────────────────────
1.  Interest rates → decimal:  11.5 %  →  0.115    8 % → 0.08
2.  All dates → "YYYY-MM-DD"
3.  Indian currency shorthand:
       "40 lakhs" → 4000000    "1 crore" → 10000000
4.  Payment cycle codes:
       monthly   → "P1ML0"
       quarterly → "P3ML0"
       semi-annual → "P6ML0"
       annual    → "P1YL0"
5.  statusDate   = one day before initialExchangeDate
6.  contractDealDate = same as initialExchangeDate (use startDate from contract)
7.  cycleAnchorDateOfInterestPayment   = first payment date (one cycle after start)
8.  cycleAnchorDateOfPrincipalRedemption = same as above (for ANN / LAM)
9.  For PAM contracts, omit cycleOfPrincipalRedemption fields entirely.
10. rateMultiplier = 1.0 and rateSpread = 0.0 unless contract says otherwise.
11. If a field is not mentioned, use the default shown in the output schema.
12. currency: use ISO code — "INR", "USD", "EUR", "GBP"

─── OUTPUT FORMAT ────────────────────────────────────────────────────────────
Return ONLY raw JSON — no markdown fences, no explanation, no extra text.

{
  "contractType": "ANN",           // PAM | ANN | LAM
  "contractID": "<given id>",
  "contractRole": "RPA",
  "counterpartyID": "CP01",
  "creatorID": "CREATOR01",
  "calendar": "NOCALENDAR",
  "businessDayConvention": "SCF",
  "currency": "INR",
  "contractDealDate": "YYYY-MM-DD",
  "initialExchangeDate": "YYYY-MM-DD",
  "statusDate": "YYYY-MM-DD",
  "maturityDate": "YYYY-MM-DD",
  "notionalPrincipal": <number>,
  "nominalInterestRate": <decimal>,
  "dayCountConvention": "A365",
  "cycleOfInterestPayment": "P1ML0",
  "cycleAnchorDateOfInterestPayment": "YYYY-MM-DD",
  "cycleOfPrincipalRedemption": "P1ML0",          // ANN / LAM only
  "cycleAnchorDateOfPrincipalRedemption": "YYYY-MM-DD",  // ANN / LAM only
  "nextPrincipalRedemptionPayment": <number or null>,     // ANN only, null if unknown
  "rateMultiplier": 1.0,
  "rateSpread": 0.0,
  "confidence": "HIGH | MEDIUM | LOW",
  "missingFields": [],
  "warnings": []
}
"""


# =============================================================================
# ── CORE FUNCTIONS ────────────────────────────────────────────────────────────
# =============================================================================

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract plain text from a PDF using pdfplumber."""
    pages = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
    text = "\n\n".join(pages)
    if len(text.strip()) < 30:
        raise ValueError(
            "Could not extract text from PDF. "
            "Make sure it is a text-based PDF (not a scanned image)."
        )
    log.info(f"PDF extracted: {len(text)} chars from {len(pages)} pages")
    return text


def contract_text_to_actus_json(
    text: str,
    contract_id: str,
    groq_client: Groq,
) -> dict:
    """
    Send contract text to Groq and get back a validated ACTUS JSON dict.
    """
    t0 = time.time()
    # Truncate to stay within context window (modern models can handle more, so 30k is safe)
    truncated = text[:30000] 

    response = groq_client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Contract ID to use: {contract_id}\n\n"
                    f"Extract ACTUS fields from the following contract:\n\n"
                    f"{truncated}"
                ),
            },
        ],
        temperature=0.1,
        max_tokens=1500,
    )

    raw = response.choices[0].message.content.strip()
    log.info(f"Groq responded in {time.time()-t0:.1f}s  model={response.model}")

    # Strip accidental markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    try:
        actus_json = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error(f"Groq returned non-JSON: {raw[:300]}")
        raise ValueError(f"AI returned invalid JSON: {e}")

    # Stamp the contract_id we were given (override whatever Groq put)
    actus_json["contractID"] = contract_id

    # Auto-correct percentage rates (e.g. 11.5 instead of 0.115)
    rate = actus_json.get("nominalInterestRate", 0)
    if rate and rate > 1.0:
        actus_json["nominalInterestRate"] = round(rate / 100, 6)
        actus_json.setdefault("warnings", []).append(
            f"Interest rate auto-corrected from {rate}% to {rate/100}"
        )

    log.info(
        f"ACTUS extraction complete — type={actus_json.get('contractType')}  "
        f"principal={actus_json.get('notionalPrincipal')}  "
        f"rate={actus_json.get('nominalInterestRate')}  "
        f"confidence={actus_json.get('confidence')}"
    )
    return actus_json


def _clean_date(d):
    if isinstance(d, str) and "T" in d:
        return d.split("T")[0]
    return d

def _to_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default

def run_actus_simulation(actus_json: dict, contract_id: str) -> list[dict]:
    if not AWESOME_ACTUS_AVAILABLE:
        raise RuntimeError(
            "awesome_actus_lib is not installed. "
            "Please install it to enable cash flow simulation. "
            "This package provides the ACTUS contract simulation engine."
        )
    
    ct = actus_json.get("contractType", "").upper()

    # ── shared kwargs for all contract types ──────────────────────────

    common = dict(
        calendar           = actus_json.get("calendar",              "NOCALENDAR"),
        businessDayConvention = actus_json.get("businessDayConvention", "SCF"),
        contractID         = contract_id,
        contractRole       = actus_json.get("contractRole",          "RPA"),
        counterpartyID     = actus_json.get("counterpartyID",        "CP01"),
        creatorID          = actus_json.get("creatorID",             "CREATOR01"),
        contractDealDate   = _clean_date(actus_json["contractDealDate"]),
        initialExchangeDate= _clean_date(actus_json["initialExchangeDate"]),
        statusDate         = _clean_date(actus_json["statusDate"]),
        currency           = actus_json.get("currency",              "INR"),
        notionalPrincipal  = _to_float(actus_json["notionalPrincipal"]),
        nominalInterestRate= _to_float(actus_json["nominalInterestRate"]),
        dayCountConvention = actus_json.get("dayCountConvention",    "A365"),
        maturityDate       = _clean_date(actus_json["maturityDate"]),
        cycleOfInterestPayment            = actus_json.get("cycleOfInterestPayment", "P1ML0"),
        cycleAnchorDateOfInterestPayment  = _clean_date(actus_json.get("cycleAnchorDateOfInterestPayment")),
        rateMultiplier     = _to_float(actus_json.get("rateMultiplier", 1.0), 1.0),
        rateSpread         = _to_float(actus_json.get("rateSpread",     0.0), 0.0),
    )

    # ── contract-type-specific kwargs ────────────────────────────────
    if ct == "ANN":
        redemption_payment = _to_float(actus_json.get("nextPrincipalRedemptionPayment"))
        contract_obj = ANN(
            **common,
            cycleOfPrincipalRedemption           = actus_json.get("cycleOfPrincipalRedemption", "P1ML0"),
            cycleAnchorDateOfPrincipalRedemption = _clean_date(actus_json.get("cycleAnchorDateOfPrincipalRedemption")),
            nextPrincipalRedemptionPayment        = redemption_payment,
        )

    elif ct == "LAM":
        contract_obj = LAM(
            **common,
            cycleOfPrincipalRedemption           = actus_json.get("cycleOfPrincipalRedemption", "P1ML0"),
            cycleAnchorDateOfPrincipalRedemption = _clean_date(actus_json.get("cycleAnchorDateOfPrincipalRedemption")),
            nextPrincipalRedemptionPayment        = _to_float(actus_json.get("nextPrincipalRedemptionPayment")),
        )

    elif ct == "PAM":
        contract_obj = PAM(**common)

    else:
        raise ValueError(
            f"Unsupported contractType '{ct}'. "
            f"This backend supports PAM, ANN, LAM."
        )

    # ── run simulation ────────────────────────────────────────────────
    service      = PublicActusService()
    event_stream = service.generateEvents(portfolio=contract_obj)
    df           = event_stream.events_df

    log.info(f"Simulation complete — {len(df)} cash flow events")

    # ── convert DataFrame → list of plain dicts ───────────────────────
    cash_flows = []
    for _, row in df.iterrows():
        cash_flows.append({
            "type":           row["type"],
            "time":           str(row["time"]),
            "payoff":         round(float(row["payoff"]),         4),
            "currency":       str(row["currency"]),
            "nominalValue":   round(float(row["nominalValue"]),   4),
            "nominalRate":    round(float(row["nominalRate"]),    6),
            "nominalAccrued": round(float(row["nominalAccrued"]), 4),
            "contractId":     str(row["contractId"]),
        })

    return cash_flows


def build_summary(cash_flows: list[dict], actus_json: dict) -> dict:
    """Compute a plain-language summary from the cash flow list."""
    interest_total  = sum(cf["payoff"] for cf in cash_flows if cf["type"] == "IP")
    principal_total = sum(cf["payoff"] for cf in cash_flows if cf["type"] == "PR")
    maturity_total  = sum(cf["payoff"] for cf in cash_flows if cf["type"] == "MD")
    total_paid      = interest_total + principal_total + maturity_total

    return {
        "contractType":    actus_json.get("contractType"),
        "contractID":      actus_json.get("contractID"),
        "currency":        actus_json.get("currency", "INR"),
        "principal":       actus_json.get("notionalPrincipal"),
        "nominalRate":     actus_json.get("nominalInterestRate"),
        "startDate":       actus_json.get("initialExchangeDate"),
        "maturityDate":    actus_json.get("maturityDate"),
        "totalEvents":     len(cash_flows),
        "totalInterest":   round(interest_total,  2),
        "totalPrincipal":  round(principal_total + maturity_total, 2),
        "totalCashFlow":   round(total_paid, 2),
        "confidence":      actus_json.get("confidence", "MEDIUM"),
        "warnings":        actus_json.get("warnings", []),
        "missingFields":   actus_json.get("missingFields", []),
    }


# =============================================================================
# ── API ENDPOINTS ─────────────────────────────────────────────────────────────
# =============================================================================

# ── GET /health ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health():
    groq_key_present = bool(os.getenv("GROQ_API_KEY"))
    health_status = "ok" if (groq_key_present and AWESOME_ACTUS_AVAILABLE) else "degraded"
    messages = []
    if not groq_key_present:
        messages.append("GROQ_API_KEY missing")
    if not AWESOME_ACTUS_AVAILABLE:
        messages.append("awesome_actus_lib not installed")
    
    return {
        "status":  health_status,
        "groqKey": groq_key_present,
        "actusLibAvailable": AWESOME_ACTUS_AVAILABLE,
        "model":   os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "warnings": messages,
        "time":    datetime.now().isoformat(),
    }


# ── POST /parse-contract ─────────────────────────────────────────────────────
@app.post("/parse-contract", tags=["Pipeline"])
def parse_contract(req: ParseTextRequest):
    """
    Step 1 — Text → ACTUS JSON.

    Send raw contract text, get back the ACTUS JSON fields that
    awesome_actus_lib needs.  Does NOT run the simulation yet.
    """
    if len(req.text.strip()) < 40:
        raise HTTPException(400, "Contract text is too short (< 40 characters).")

    try:
        groq  = get_groq()
        actus = contract_text_to_actus_json(req.text, req.contract_id, groq)
        return {"success": True, "actusJson": actus}

    except RuntimeError as e:          # missing API key
        raise HTTPException(503, str(e))
    except ValueError as e:            # bad Groq response
        raise HTTPException(422, str(e))
    except Exception as e:
        log.exception("Unexpected error in /parse-contract")
        raise HTTPException(500, f"Parsing failed: {e}")


# ── POST /parse-pdf ───────────────────────────────────────────────────────────
@app.post("/parse-pdf", tags=["Pipeline"])
def parse_pdf(
    file:        UploadFile = File(..., description="PDF contract file"),
    contract_id: str        = "contract01",
):
    """
    Step 1 (PDF variant) — PDF upload → ACTUS JSON.

    Extracts text from the PDF, then does the same Groq extraction as
    /parse-contract.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only .pdf files accepted.")

    pdf_bytes = file.file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(400, "Uploaded file is empty.")
    if len(pdf_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large — max 10 MB.")

    try:
        text  = extract_text_from_pdf(pdf_bytes)
        groq  = get_groq()
        actus = contract_text_to_actus_json(text, contract_id, groq)
        return {
            "success":         True,
            "extractedChars":  len(text),
            "actusJson":       actus,
        }

    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        log.exception("Unexpected error in /parse-pdf")
        raise HTTPException(500, f"PDF processing failed: {e}")


@app.post("/simulate", tags=["Pipeline"])
def simulate(payload: dict):
    """
    Step 2 — ACTUS JSON → Cash Flows.
    
    This endpoint is now flexible:
    1. It accepts {"actus_json": {...}, "contract_id": "..."} (standard)
    2. It also accepts the ACTUS engine portfolio format: {"contracts": [...]}
    """
    
    # Check if this is the "contracts" portfolio format
    if "contracts" in payload and isinstance(payload["contracts"], list):
        if not payload["contracts"]:
            raise HTTPException(400, "Contracts list is empty.")
        actus_json = payload["contracts"][0]
        contract_id = actus_json.get("contractID", "contract01")
    else:
        # standard SimulateRequest-like format
        actus_json = payload.get("actus_json")
        contract_id = payload.get("contract_id", "contract01")
    
    if not actus_json:
        raise HTTPException(
            422, "Please provide 'actus_json' or a 'contracts' list."
        )

    # Basic required-field check
    for field in ["contractType", "notionalPrincipal", "nominalInterestRate",
                  "initialExchangeDate", "maturityDate"]:
        if field not in actus_json:
            raise HTTPException(
                422, f"Missing required ACTUS field: '{field}'"
            )

    try:
        # Handle T00:00:00 and string numbers inside run_actus_simulation
        cash_flows = run_actus_simulation(actus_json, contract_id)
        summary    = build_summary(cash_flows, actus_json)
        return {
            "success":    True,
            "summary":    summary,
            "cashFlows":  cash_flows,
        }

    except ValueError as e:          # unsupported contract type
        raise HTTPException(422, str(e))
    except Exception as e:
        log.exception("Unexpected error in /simulate")
        raise HTTPException(500, f"Simulation failed: {e}")


# ── POST /full-pipeline ───────────────────────────────────────────────────────
@app.post("/full-pipeline", tags=["Pipeline"])
def full_pipeline(req: FullPipelineTextRequest):
    """
    One-shot endpoint — Contract text → ACTUS JSON → Cash Flows.

    Combines /parse-contract + /simulate into a single call.
    This is the endpoint your frontend should call.
    """
    if len(req.text.strip()) < 40:
        raise HTTPException(400, "Contract text is too short.")

    try:
        groq       = get_groq()
        actus_json = contract_text_to_actus_json(req.text, req.contract_id, groq)
        
        # Validation
        for field in ["contractType", "notionalPrincipal", "nominalInterestRate",
                    "initialExchangeDate", "maturityDate",
                    "contractDealDate", "statusDate"]:
            if field not in actus_json:
                log.warning(f"AI missed required field: {field}")
                # Try to fallback or raise
        
        cash_flows = run_actus_simulation(actus_json, req.contract_id)
        summary    = build_summary(cash_flows, actus_json)

        return {
            "success":    True,
            "actusJson":  actus_json,
            "summary":    summary,
            "cashFlows":  cash_flows,
        }

    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        log.exception("Unexpected error in /full-pipeline")
        raise HTTPException(500, f"Pipeline failed: {e}")


# ── POST /full-pipeline-pdf ───────────────────────────────────────────────────
@app.post("/full-pipeline-pdf", tags=["Pipeline"])
def full_pipeline_pdf(
    file:        UploadFile = File(...),
    contract_id: str        = "contract01",
):
    """
    One-shot endpoint for PDF upload.
    PDF → text extraction → ACTUS JSON → Cash Flows.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only .pdf files accepted.")

    pdf_bytes = file.file.read()
    if not pdf_bytes:
        raise HTTPException(400, "Empty file.")

    try:
        text       = extract_text_from_pdf(pdf_bytes)
        groq       = get_groq()
        actus_json = contract_text_to_actus_json(text, contract_id, groq)
        
        # Validation
        for field in ["contractType", "notionalPrincipal", "nominalInterestRate",
                    "initialExchangeDate", "maturityDate",
                    "contractDealDate", "statusDate"]:
            if field not in actus_json:
                log.warning(f"AI missed required field: {field}")

        cash_flows = run_actus_simulation(actus_json, contract_id)
        summary    = build_summary(cash_flows, actus_json)

        return {
            "success":        True,
            "extractedChars": len(text),
            "actusJson":      actus_json,
            "summary":        summary,
            "cashFlows":      cash_flows,
        }

    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        log.exception("Unexpected error in /full-pipeline-pdf")
        raise HTTPException(500, f"Pipeline failed: {e}")


# ── POST /predict-risk ────────────────────────────────────────────────────────
@app.post("/predict-risk", tags=["Pipeline"])
def predict_risk_endpoint(payload: dict):
    """
    Run AI risk prediction on ACTUS engine output.

    Expects the full ACTUS output dict:
    {
        "success": true,
        "actusJson": {...},
        "summary": {...},
        "cashFlows": [...]
    }

    Returns risk prediction:
    {
        "contract_id": str,
        "default_probability": float,
        "risk_category": "LOW" | "MEDIUM" | "HIGH",
        "expected_loss": float,
        "recommendation": str,
        "negotiation_tips": [str]  (only for HIGH risk)
    }
    """
    import sys as _sys
    from pathlib import Path as _Path

    ai_dir = _Path(__file__).resolve().parent.parent / "Ai_prediction"

    if not ai_dir.exists():
        raise HTTPException(500, f"Ai_prediction directory not found at {ai_dir}")

    original_cwd = os.getcwd()
    try:
        os.chdir(str(ai_dir))
        if str(ai_dir) not in _sys.path:
            _sys.path.insert(0, str(ai_dir))

        from load_model import predict_risk as _predict_risk

        result = _predict_risk(payload)

        if "error" in result:
            raise HTTPException(422, result["error"])

        log.info(
            f"AI Risk prediction complete — "
            f"category={result.get('risk_category')}  "
            f"prob={result.get('default_probability')}"
        )

        return {"success": True, "riskPrediction": result}

    except ImportError as e:
        log.exception("Cannot import AI model")
        raise HTTPException(503, f"AI model not available: {e}")
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Unexpected error in /predict-risk")
        raise HTTPException(500, f"Risk prediction failed: {e}")
    finally:
        os.chdir(original_cwd)


# ── GET /liquidity-forecast ───────────────────────────────────────────────────
@app.get("/liquidity-forecast", tags=["Liquidity"])
def liquidity_forecast_endpoint():
    """
    Runs the Liquidity_Engine/liquidity_forecaster.py script and returns the 
    generated liquidity_report.json.
    """
    import sys
    import subprocess
    from pathlib import Path

    base_dir = Path(__file__).resolve().parent.parent
    liquidity_dir = base_dir / "Liquidity_Engine"
    script_path = liquidity_dir / "liquidity_forecaster.py"
    report_path = liquidity_dir / "liquidity_report.json"

    if not script_path.exists():
        raise HTTPException(500, "liquidity_forecaster.py not found.")

    try:
        # Run the script using the current Python executable (the venv)
        # Note: This might take a bit since it requests /simulate
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(liquidity_dir),
            capture_output=True,
            text=True
        )

        log.info(f"Liquidity subproc stdout: {result.stdout}")
        if result.stderr:
            log.warning(f"Liquidity subproc stderr: {result.stderr}")

        if not report_path.exists():
            raise HTTPException(500, "Forecast ran but report JSON was not created.")

        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {"success": True, "forecast": data}

    except Exception as e:
        log.exception("Unexpected error in /liquidity-forecast")
        raise HTTPException(500, f"Liquidity forecast failed: {e}")


# ── POST /negotiate ────────────────────────────────────────────────────────
@app.post("/negotiate", tags=["Intelligence"])
def negotiate_endpoint(payload: dict):
    """
    Run AI Negotiation Agent on ACTUS engine output.

    Expects:
    {
        "actusOutput": {...},
        "riskData": {...}
    }
    """
    import sys as _sys
    from pathlib import Path as _Path

    base_dir = _Path(__file__).resolve().parent.parent
    neg_dir = base_dir / "Negotiation_Agent"

    if not neg_dir.exists():
        raise HTTPException(500, f"Negotiation_Agent directory not found.")

    original_cwd = os.getcwd()
    try:
        os.chdir(str(neg_dir))
        if str(neg_dir) not in _sys.path:
            _sys.path.insert(0, str(neg_dir))

        from negotiator import negotiate_terms

        actus_output = payload.get("actusOutput", {})
        risk_result = payload.get("riskData", {})

        result = negotiate_terms(actus_output, risk_result)

        if not result:
            raise HTTPException(500, "Negotiation failed (returned None). Verify GROQ_API_KEY.")

        return {"success": True, "negotiated_terms": result}
    except Exception as e:
        log.exception("Unexpected error in /negotiate")
        raise HTTPException(500, f"Negotiation failed: {e}")
    finally:
        os.chdir(original_cwd)


# ── POST /stress-test ───────────────────────────────────────────────────────
@app.post("/stress-test", tags=["Intelligence"])
def stress_test_endpoint(payload: dict):
    """
    Run Scenario Stress Testing Agent.
    
    Expects:
    {
        "actusOutput": {...},
        "riskData": {...},
        "scenario": "Interest rates rise by 2%"
    }
    """
    import sys as _sys
    from pathlib import Path as _Path
    import tempfile
    import json

    base_dir = _Path(__file__).resolve().parent.parent
    stress_dir = base_dir / "ScenarioStressTesting"

    if not stress_dir.exists():
        raise HTTPException(500, f"ScenarioStressTesting directory not found.")

    original_cwd = os.getcwd()
    try:
        os.chdir(str(stress_dir))
        if str(stress_dir) not in _sys.path:
            _sys.path.insert(0, str(stress_dir))

        import stress_test_agent
        import importlib
        importlib.reload(stress_test_agent)
        from stress_test_agent import StressTestingAgent

        actus_output = payload.get("actusOutput", {})
        risk_data = payload.get("riskData", {})
        scenario = payload.get("scenario", "")

        mapped_risk = {
            "Risk Category": risk_data.get("risk_category", "UNKNOWN"),
            "Default Probability": str(risk_data.get("default_probability", 0)),
            "Expected Loss": str(risk_data.get("expected_loss", 0)),
            "Recommendation": risk_data.get("recommendation", "UNKNOWN")
        }

        agent = StressTestingAgent()

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tmp:
            json.dump(actus_output, tmp)
            tmp_path = tmp.name

        try:
            result = agent.run_scenario(tmp_path, mapped_risk, scenario)
            return {"success": True, "stress_test": result["data"]}
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        log.exception("Unexpected error in /stress-test")
        raise HTTPException(500, f"Stress test failed: {e}")
    finally:
        os.chdir(original_cwd)

@app.post("/blockchain-store")
async def blockchain_store_endpoint(payload: Dict[str, Any]):
    """
    Trigger the blockchain interaction script from the UI.
    """
    import subprocess
    from pathlib import Path as _Path
    import sys
    import json
    
    base_dir = _Path(__file__).resolve().parent.parent
    blockchain_dir = base_dir / "blockchain"
    
    if not blockchain_dir.exists():
        raise HTTPException(500, "Blockchain directory not found.")
    
    try:
        log.info("⛓️  Triggering blockchain interaction with data...")
        
        # Prepare the data string from frontend payload
        # This allows storing actual contract details rather than demo data
        data_str = json.dumps(payload)
        
        result = subprocess.run(
            [sys.executable, "interact.py", data_str],
            cwd=str(blockchain_dir),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            import re
            match = re.search(r"Transaction Hash:\s*(0x[0-9a-fA-F]+)", result.stdout)
            tx_hash = match.group(1) if match else "Unknown"
                
            return {
                "success": True, 
                "message": "Data successfully stored on Tenderly Testnet",
                "tx_hash": tx_hash,
                "output": result.stdout
            }
        else:
            return {
                "success": False,
                "error": result.stderr or result.stdout
            }
            
    except Exception as e:
        log.exception("Blockchain storage failed")
        raise HTTPException(500, f"Blockchain storage failed: {str(e)}")
