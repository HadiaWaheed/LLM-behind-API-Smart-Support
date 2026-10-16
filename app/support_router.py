
from pathlib import Path
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import require_role
from app.database import get_db
from app.database_models import SupportMessage, SupportTicket, User
from app.llm import call_llm
from app.models import TriageRequest


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support", tags=["Support"])

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_PATH = BASE_DIR / "knowledge_base" / "support_faq.md"


# -------------------- Request schemas --------------------

class TicketCreate(BaseModel):
    subject: str | None = Field(default=None, min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)


class MessageCreate(BaseModel):
    message: str | None = Field(default=None, max_length=4000)
    content: str | None = Field(default=None, max_length=4000)


class StatusUpdate(BaseModel):
    status: str


# -------------------- Serialization --------------------

def ticket_to_dict(ticket: SupportTicket) -> dict:
    return {
        "id": ticket.id,
        "ticket_id": ticket.id,
        "subject": ticket.subject,
        "title": ticket.subject,
        "message": getattr(ticket, "message", None),
        "status": ticket.status,
        "category": ticket.category,
        "urgency": ticket.urgency,
        "priority": ticket.urgency,
        "suggested_team": ticket.suggested_team,
        "confidence": ticket.confidence,
        "escalated": ticket.escalated,
        "created_at": (
            ticket.created_at.isoformat()
            if ticket.created_at else None
        ),
    }


def message_to_dict(message: SupportMessage) -> dict:
    return {
        "id": message.id,
        "sender_role": message.sender_role,
        "role": message.sender_role,
        "sender": message.sender_role,
        "content": message.content,
        "message": message.content,
        "created_at": (
            message.created_at.isoformat()
            if message.created_at else None
        ),
    }


def get_ticket_or_404(
    ticket_id: int,
    db: Session,
) -> SupportTicket:
    ticket = (
        db.query(SupportTicket)
        .filter(SupportTicket.id == ticket_id)
        .first()
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found.",
        )

    return ticket


def ensure_customer_owns_ticket(
    ticket: SupportTicket,
    user: User,
) -> None:
    if ticket.customer_id != user.id:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found.",
        )


def get_ticket_messages(
    ticket_id: int,
    db: Session,
) -> list[SupportMessage]:
    return (
        db.query(SupportMessage)
        .filter(SupportMessage.ticket_id == ticket_id)
        .order_by(SupportMessage.created_at.asc())
        .all()
    )


# -------------------- Lightweight RAG --------------------

STOP_WORDS = {
    "a", "an", "the", "is", "are", "am", "was", "were",
    "do", "does", "did", "i", "we", "you", "they", "it",
    "to", "for", "of", "in", "on", "at", "and", "or",
    "can", "could", "how", "what", "when", "where", "my",
    "me", "our", "your", "please", "tell", "about",
    "customer", "customers", "would", "like", "want",
    "have", "has", "had", "this", "that", "with", "from",
    "be", "been", "being", "will", "should", "using",
    "help", "need", "know", "get", "there", "their",
}


def load_knowledge_base() -> str:
    try:
        knowledge = KNOWLEDGE_PATH.read_text(encoding="utf-8-sig")

        if not knowledge.strip():
            logger.warning("Knowledge base file is empty: %s", KNOWLEDGE_PATH)
            return ""

        logger.info(
            "Knowledge base loaded: path=%s chars=%s",
            KNOWLEDGE_PATH,
            len(knowledge),
        )
        return knowledge

    except OSError:
        logger.exception(
            "Could not load knowledge base: %s",
            KNOWLEDGE_PATH,
        )
        return ""


def normalize_headings(knowledge: str) -> str:
    # Convert **## Heading** to ## Heading.
    return re.sub(
        r"(?m)^\s*\*\*(#{1,3}\s+.*?)\*\*\s*$",
        r"\1",
        knowledge,
    )


def split_knowledge_into_chunks(knowledge: str) -> list[str]:
    normalized = normalize_headings(knowledge)

    sections = re.split(
        r"(?m)(?=^\s*#{1,3}\s+)",
        normalized,
    )

    chunks = [
        section.strip()
        for section in sections
        if section.strip()
    ]

    return chunks or (
        [normalized.strip()] if normalized.strip() else []
    )


def tokenize(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]+", text.lower())
        if word not in STOP_WORDS and len(word) > 1
    }


def retrieve_relevant_chunks(
    question: str,
    top_k: int = 3,
) -> list[str]:
    knowledge = load_knowledge_base()

    if not knowledge.strip():
        logger.warning("RAG: knowledge base is empty.")
        return []

    query_terms = tokenize(question)

    if not query_terms:
        logger.warning("RAG: no query keywords found.")
        return []

    chunks = split_knowledge_into_chunks(knowledge)
    scored_chunks: list[tuple[float, str]] = []

    logger.info(
        "RAG search: terms=%s chunks=%s",
        sorted(query_terms),
        len(chunks),
    )

    for chunk in chunks:
        chunk_terms = tokenize(chunk)

        if not chunk_terms:
            continue

        overlap = query_terms.intersection(chunk_terms)

        if not overlap:
            continue

        coverage = len(overlap) / max(len(query_terms), 1)
        specificity = len(overlap) / max(len(chunk_terms), 1)
        score = 0.85 * coverage + 0.15 * specificity

        heading_match = re.search(
            r"(?m)^\s*#{1,3}\s+(.+)$",
            chunk,
        )

        if heading_match:
            heading_terms = tokenize(heading_match.group(1))
            heading_overlap = query_terms.intersection(heading_terms)

            if heading_overlap:
                score += 0.15 * (
                    len(heading_overlap) / max(len(query_terms), 1)
                )

        scored_chunks.append((score, chunk))

    scored_chunks.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    relevant = [
        chunk
        for score, chunk in scored_chunks
        if score >= 0.12
    ][:max(1, min(top_k, 5))]

    logger.info(
        "RAG retrieved %s chunks; top scores=%s",
        len(relevant),
        [round(score, 3) for score, _ in scored_chunks[:5]],
    )

    return relevant


# -------------------- Customer-facing AI answer --------------------

def generate_customer_answer(
    message: str,
    triage,
) -> tuple[str, bool]:
    # Retrieve relevant FAQ content using RAG.
    chunks = retrieve_relevant_chunks(message)

    category_value = getattr(triage, "category", "other")
    category = str(
        getattr(category_value, "value", category_value)
    ).lower()

    needs_agent = any(
        term in category
        for term in ("refund", "exchange", "billing", "account")
    )

    # Do not invent an answer if RAG found no relevant information.
    if not chunks:
        logger.warning(
            "No relevant FAQ context found for question: %s",
            message,
        )
        return (
            "I couldn't find enough confirmed information in our "
            "support knowledge base to answer that accurately. "
            "Our support team can review your question and help "
            "with the next steps.",
            True,
        )

    context = "\n\n---\n\n".join(chunks)

    system_prompt = """
You are SupportPilot, a helpful customer-support assistant.

Answer the customer's actual question in natural, empathetic English.

Rules:
- Use the supplied knowledge-base context as the source of truth.
- Use relevant FAQ information and suggested responses to answer.
- Rewrite the information naturally; do not mechanically copy it.
- Do not invent store policies, refund approvals, replacements,
  delivery dates, tracking information, or completed actions.
- If the context does not contain enough information, explain that
  the support team needs to review the question.
- Never ask for passwords or one-time verification codes.
- Never reveal internal categories, urgency, confidence, or routing.
- Keep the answer concise, usually two to four sentences.
- Return only the customer-facing answer, not JSON or headings.
""".strip()

    user_prompt = f"""
Knowledge-base context retrieved from support_faq.md:

{context}

Customer question:
{message}

Write a helpful answer using the retrieved context.
Do not invent information that is not supported by the context.
""".strip()

    try:
        result = call_llm(system_prompt, user_prompt)

        if isinstance(result, dict):
            answer = str(result.get("content") or "").strip()
        elif isinstance(result, str):
            answer = result.strip()
        else:
            answer = str(
                getattr(result, "content", "") or ""
            ).strip()

        if not answer:
            raise ValueError("The LLM returned an empty answer.")

        uncertainty_phrases = (
            "i don't know",
            "i do not know",
            "i can't confirm",
            "i cannot confirm",
            "i couldn't find",
            "i could not find",
            "i'm not sure",
            "i am not sure",
            "needs to be confirmed",
            "needs to review",
        )

        if any(
            phrase in answer.lower()
            for phrase in uncertainty_phrases
        ):
            needs_agent = True

        logger.info("Customer-facing LLM answer generated successfully.")

        return answer, needs_agent

    except Exception:
        logger.exception("Customer-answer LLM call failed.")

        return (
            "I'm unable to prepare a reliable answer right now. "
            "Our support team can review your question and help "
            "with the next steps.",
            True,
        )


# -------------------- Customer ticket endpoints --------------------

@router.post("/tickets", status_code=201)
def create_ticket(
    data: TicketCreate,
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    customer_message = data.message.strip()

    if not customer_message:
        raise HTTPException(
            status_code=422,
            detail="Message cannot be empty.",
        )

    subject = (
        data.subject.strip()
        if data.subject and data.subject.strip()
        else customer_message[:100]
    )

    ticket = SupportTicket(
        customer_id=current_user.id,
        subject=subject,
        status="open",
        category="other",
        urgency="medium",
        suggested_team="general-support",
        escalated=False,
    )

    try:
        db.add(ticket)
        db.flush()

        db.add(
            SupportMessage(
                ticket_id=ticket.id,
                sender_id=current_user.id,
                sender_role="customer",
                content=customer_message,
            )
        )

        triage_result = None

        try:
            # Reuse the existing triage logic from app.main.
            from app.main import triage as run_triage

            triage_result = run_triage(
                TriageRequest(text=customer_message)
            )

        except Exception:
            logger.exception("Triage failed for new ticket.")

        needs_agent = triage_result is None

        if triage_result is not None:
            category = getattr(triage_result, "category", "other")
            urgency = getattr(triage_result, "urgency", "medium")
            team = getattr(
                triage_result,
                "suggested_team",
                "general-support",
            )

            ticket.category = str(
                getattr(category, "value", category)
            )
            ticket.urgency = str(
                getattr(urgency, "value", urgency)
            )
            ticket.suggested_team = str(
                getattr(team, "value", team)
            )

            confidence = getattr(
                triage_result,
                "confidence",
                None,
            )

            ticket.confidence = (
                float(confidence)
                if confidence is not None
                else None
            )

            try:
                needs_agent = (
                    confidence is None
                    or float(confidence) < 0.65
                    or ticket.urgency.lower() == "high"
                )
            except (TypeError, ValueError):
                needs_agent = True

            answer, answer_needs_agent = generate_customer_answer(
                customer_message,
                triage_result,
            )

            needs_agent = needs_agent or answer_needs_agent

        else:
            answer = (
                "Your request has been received, but I couldn't "
                "classify it reliably. Our support team will review "
                "your question and help with the next steps."
            )

        ticket.escalated = needs_agent

        if needs_agent:
            ticket.status = "pending_agent"

        db.add(
            SupportMessage(
                ticket_id=ticket.id,
                sender_id=None,
                sender_role="ai",
                content=answer,
            )
        )

        db.commit()
        db.refresh(ticket)

        messages = get_ticket_messages(ticket.id, db)

        return {
            "ticket": ticket_to_dict(ticket),
            "messages": [
                message_to_dict(message)
                for message in messages
            ],
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()
        logger.exception("Could not create support ticket.")

        raise HTTPException(
            status_code=500,
            detail="Could not create the support ticket.",
        ) from exc


@router.get("/tickets")
def list_customer_tickets(
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    tickets = (
        db.query(SupportTicket)
        .filter(SupportTicket.customer_id == current_user.id)
        .order_by(SupportTicket.created_at.desc())
        .all()
    )

    return {
        "tickets": [ticket_to_dict(ticket) for ticket in tickets]
    }


@router.get("/tickets/{ticket_id}")
def get_customer_ticket(
    ticket_id: int,
    current_user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    ticket = get_ticket_or_404(ticket_id, db)
    ensure_customer_owns_ticket(ticket, current_user)

    messages = get_ticket_messages(ticket.id, db)

    return {
        "ticket": ticket_to_dict(ticket),
        "messages": [
            message_to_dict(message)
            for message in messages
        ],
    }


# -------------------- Agent endpoints --------------------

@router.get("/agent/tickets")
def list_agent_tickets(
    status_filter: str | None = Query(
        default=None,
        alias="status",
    ),
    current_user: User = Depends(require_role("agent")),
    db: Session = Depends(get_db),
):
    query = db.query(SupportTicket)

    allowed_statuses = {
        "open",
        "pending_agent",
        "in_progress",
        "resolved",
        "closed",
    }

    if status_filter:
        if status_filter not in allowed_statuses:
            raise HTTPException(
                status_code=422,
                detail="Invalid status filter.",
            )

        query = query.filter(
            SupportTicket.status == status_filter
        )

    tickets = query.order_by(
        SupportTicket.escalated.desc(),
        SupportTicket.created_at.asc(),
    ).all()

    return {
        "tickets": [ticket_to_dict(ticket) for ticket in tickets]
    }


@router.get("/agent/tickets/{ticket_id}")
def get_agent_ticket(
    ticket_id: int,
    current_user: User = Depends(require_role("agent")),
    db: Session = Depends(get_db),
):
    ticket = get_ticket_or_404(ticket_id, db)
    messages = get_ticket_messages(ticket.id, db)

    customer = (
        db.query(User)
        .filter(User.id == ticket.customer_id)
        .first()
    )

    return {
        "ticket": ticket_to_dict(ticket),
        "customer": {
            "name": customer.name if customer else "Unknown customer",
            "email": customer.email if customer else None,
        },
        "messages": [
            message_to_dict(message)
            for message in messages
        ],
    }


@router.post("/agent/tickets/{ticket_id}/reply")
def agent_reply(
    ticket_id: int,
    data: MessageCreate,
    current_user: User = Depends(require_role("agent")),
    db: Session = Depends(get_db),
):
    content = (data.message or data.content or "").strip()

    if not content:
        raise HTTPException(
            status_code=422,
            detail="Reply cannot be empty.",
        )

    ticket = get_ticket_or_404(ticket_id, db)

    if ticket.status == "closed":
        raise HTTPException(
            status_code=409,
            detail="This ticket is closed and cannot receive replies.",
        )

    try:
        db.add(
            SupportMessage(
                ticket_id=ticket.id,
                sender_id=current_user.id,
                sender_role="agent",
                content=content,
            )
        )

        ticket.assigned_agent_id = current_user.id
        ticket.status = "in_progress"
        ticket.escalated = False

        db.commit()
        db.refresh(ticket)

        return {
            "message": "Reply sent.",
            "ticket": ticket_to_dict(ticket),
        }

    except Exception as exc:
        db.rollback()
        logger.exception("Could not save agent reply.")

        raise HTTPException(
            status_code=500,
            detail="Could not save agent reply.",
        ) from exc


@router.patch("/agent/tickets/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    data: StatusUpdate,
    current_user: User = Depends(require_role("agent")),
    db: Session = Depends(get_db),
):
    allowed_statuses = {
        "open",
        "pending_agent",
        "in_progress",
        "resolved",
        "closed",
    }

    if data.status not in allowed_statuses:
        raise HTTPException(
            status_code=422,
            detail="Invalid status filter.",
        )

    ticket = get_ticket_or_404(ticket_id, db)

    try:
        ticket.status = data.status

        if data.status in {"resolved", "closed"}:
            ticket.escalated = False

        db.commit()
        db.refresh(ticket)

        return {"ticket": ticket_to_dict(ticket)}

    except Exception as exc:
        db.rollback()
        logger.exception("Could not update ticket status.")

        raise HTTPException(
            status_code=500,
            detail="Could not update ticket status.",
        ) from exc
