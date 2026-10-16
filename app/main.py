
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import Base, engine, get_db
from app.database_models import User
from app.llm import call_llm
from app.models import TriageRequest, TriageResponse
from app.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserResponse,
)

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "prompts" / "triage-v1.md"
LOG_DIR = BASE_DIR / "logs"

QUARANTINE_PATH = LOG_DIR / "quarantine.jsonl"
USAGE_PATH = LOG_DIR / "usage.jsonl"

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SupportPilot API",
    description=(
        "Customer support API with authentication, "
        "AI ticket triage, and knowledge-base answers."
    ),
    version="1.2.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


# -------------------- LLM helpers --------------------

def clean_llm_output(raw: Any) -> str:
    """Extract clean text from the LLM response."""
    if isinstance(raw, dict):
        raw = raw.get("content", raw)

    text = str(raw or "").strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*```$", "", text)

    return text.strip()


def parse_and_validate(raw: Any) -> TriageResponse:
    cleaned = clean_llm_output(raw)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "The model did not return valid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError(
            "The model response must be a JSON object."
        )

    return TriageResponse.model_validate(payload)


def build_repair_message(raw: Any) -> str:
    return (
        "Your previous response did not match the required schema. "
        "Return ONLY a valid JSON object with these fields: "
        "category, urgency, suggested_team, confidence, reason. "
        "Do not include Markdown or extra text.\n\n"
        "Allowed category values: billing, technical, account, "
        "delivery, refund, other.\n"
        "Allowed urgency values: low, medium, high.\n"
        "Allowed suggested_team values: billing, technical-support, "
        "account-support, delivery, general-support.\n"
        "Confidence must be a number from 0 to 1.\n\n"
        f"Previous response:\n{clean_llm_output(raw)}"
    )


def append_jsonl(
    path: Path,
    payload: dict[str, Any],
) -> None:
    try:
        with path.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(payload, ensure_ascii=False) + "\n"
            )
    except OSError:
        logger.exception("Could not write log file: %s", path)


def quarantine(raw: Any, reason: str) -> None:
    append_jsonl(
        QUARANTINE_PATH,
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "raw_response": clean_llm_output(raw),
        },
    )


def log_usage(**details: Any) -> None:
    append_jsonl(
        USAGE_PATH,
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **details,
        },
    )


def extract_llm_content(result: Any) -> Any:
    """Support the dictionary response used by this project."""
    if isinstance(result, dict):
        return result.get("content", result)

    content = getattr(result, "content", None)
    return result if content is None else content


# -------------------- Health check --------------------

@app.get("/health")
def health():
    return {
        "message": "SupportPilot API is running.",
        "status": "ok",
    }


# -------------------- Registration --------------------

@app.post("/auth/register", response_model=UserResponse)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    normalized_email = str(data.email).strip().lower()

    existing_user = (
        db.query(User)
        .filter(User.email == normalized_email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    user = User(
        name=data.name.strip(),
        email=normalized_email,
        password_hash=hash_password(data.password),
        role="customer",
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except Exception as exc:
        db.rollback()
        logger.exception("Account registration failed.")
        raise HTTPException(
            status_code=500,
            detail="Could not create the account. Please try again.",
        ) from exc

    return user


# -------------------- Login --------------------

@app.post("/auth/login", response_model=LoginResponse)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    normalized_email = str(data.email).strip().lower()

    user = (
        db.query(User)
        .filter(User.email == normalized_email)
        .first()
    )

    if (
        user is None
        or not verify_password(
            data.password,
            user.password_hash,
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    if user.role != "customer":
        raise HTTPException(
            status_code=403,
            detail="This account is not enabled for customer access.",
        )

    token = create_access_token(
        user_id=user.id,
        role=user.role,
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
    )


# -------------------- Current customer --------------------

@app.get("/auth/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "customer":
        raise HTTPException(
            status_code=403,
            detail="This account is not enabled for customer access.",
        )

    return current_user


# -------------------- AI triage --------------------

@app.post("/triage", response_model=TriageResponse)
def triage(data: TriageRequest):
    stub_enabled = os.getenv(
        "LLM_STUB", ""
    ).strip().lower() in {"1", "true", "yes"}

    if stub_enabled:
        logger.warning(
            "LLM_STUB is enabled; returning a test response."
        )

        return TriageResponse(
            category="other",
            urgency="low",
            suggested_team="general-support",
            confidence=0.85,
            reason="Stub response for local testing.",
        )

    llm_enabled = os.getenv(
        "LLM_ENABLED", "true"
    ).strip().lower() not in {"0", "false", "no"}

    if not llm_enabled:
        raise HTTPException(
            status_code=503,
            detail="AI triage is currently disabled.",
        )

    if not PROMPT_PATH.is_file():
        logger.error("Triage prompt not found: %s", PROMPT_PATH)
        raise HTTPException(
            status_code=500,
            detail="The triage prompt file could not be found.",
        )

    try:
        prompt_template = PROMPT_PATH.read_text(
            encoding="utf-8"
        )
    except OSError as exc:
        logger.exception("Could not read triage prompt.")
        raise HTTPException(
            status_code=500,
            detail="Could not read the triage prompt file.",
        ) from exc

    raw_response = None

    try:
        # call_llm expects system_prompt and user_message.
        result = call_llm(
            prompt_template,
            data.text,
        )
        raw_response = extract_llm_content(result)
        log_usage(operation="triage", attempt=1)

        try:
            parsed = parse_and_validate(raw_response)
            logger.info(
                "Triage successful: category=%s urgency=%s "
                "confidence=%s",
                parsed.category.value,
                parsed.urgency.value,
                parsed.confidence,
            )
            return parsed

        except (ValueError, TypeError) as first_error:
            logger.warning(
                "Triage validation failed; trying repair."
            )

            repair_prompt = build_repair_message(raw_response)
            repair_result = call_llm(
                prompt_template,
                repair_prompt,
            )
            raw_response = extract_llm_content(repair_result)
            log_usage(operation="triage_repair", attempt=2)

            try:
                parsed = parse_and_validate(raw_response)
                logger.info(
                    "Triage repair successful: category=%s "
                    "confidence=%s",
                    parsed.category.value,
                    parsed.confidence,
                )
                return parsed

            except (ValueError, TypeError) as second_error:
                quarantine(
                    raw_response,
                    (
                        f"Initial validation: {first_error}; "
                        f"repair validation: {second_error}"
                    ),
                )
                raise HTTPException(
                    status_code=502,
                    detail="AI returned an invalid triage response.",
                ) from second_error

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("AI triage failed.")
        quarantine(raw_response, str(exc))
        raise HTTPException(
            status_code=502,
            detail="AI triage failed. Please try again.",
        ) from exc


# Import after defining triage because support_router calls it.
from app.support_router import router as support_router

app.include_router(support_router)
