from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.llm_providers import LLMProvider, get_llm_provider
from app.services.retrieval_service import RetrievalHit


GROUNDED_SYSTEM = """You are a careful assistant for contract and document review.
Rules:
- Answer ONLY using the evidence blocks labeled [CHUNK_...] below. Do not invent facts.
- If the evidence is insufficient, say so plainly and do not guess.
- If evidence conflicts, mention the disagreement briefly and avoid picking a single claim without support.
- Keep answers concise and professional."""


@dataclass(frozen=True)
class AnswerResult:
    text: str
    answerability: Literal["grounded", "insufficient_evidence"]
    llm_model: str
    llm_debug: dict[str, object]


def _format_context_blocks(hits: list[RetrievalHit]) -> str:
    parts: list[str] = []
    for h in hits:
        doc = h.chunk.document_version.document
        page = h.chunk.page.page_number if h.chunk.page else (h.chunk.metadata_json or {}).get("page_number", "?")
        parts.append(
            f"[CHUNK_{h.chunk.id} | document={doc.filename} | page={page} | score={h.score:.4f}]\n"
            f"{h.chunk.text.strip()}"
        )
    return "\n\n---\n\n".join(parts)


async def generate_answer(
    *,
    question: str,
    context_hits: list[RetrievalHit],
    insufficient_evidence: bool,
    llm: LLMProvider | None = None,
) -> AnswerResult:
    llm = llm or get_llm_provider()
    if insufficient_evidence or not context_hits:
        return AnswerResult(
            text=(
                "There is insufficient evidence in the indexed document context to answer this "
                "question with confidence."
            ),
            answerability="insufficient_evidence",
            llm_model=llm.model_name,
            llm_debug={"path": "template_insufficient"},
        )

    ctx = _format_context_blocks(context_hits)
    user = (
        f"QUESTION:\n{question.strip()}\n\n"
        f"EVIDENCE:\n{ctx}\n\n"
        "Answer using only the evidence above. Reference chunk ids when helpful."
    )
    text = await llm.complete(system=GROUNDED_SYSTEM, user=user)
    return AnswerResult(
        text=text.strip(),
        answerability="grounded",
        llm_model=llm.model_name,
        llm_debug={"path": "llm", "context_chunks": len(context_hits)},
    )
