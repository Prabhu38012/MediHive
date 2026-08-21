
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from utils.llm_client import call_llm


class AgentResponse(BaseModel):
    agent: str
    question: str
    answer: str
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: str


class MedicalAgent:
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt

    def run(self, question: str, context: str | None = None) -> AgentResponse:
        """Run this agent on a question. `context` is reserved for the
        RAG phase (retrieved document chunks) — currently unused (None)
        since the 40% build has no retrieval yet.
        """
        user_prompt = question
        if context:
            user_prompt = f"Relevant context:\n{context}\n\nQuestion:\n{question}"

        result = call_llm(self.system_prompt, user_prompt)

        # Some local models (e.g. Llama via Ollama) sometimes return
        # reasoning/answer as a list of strings instead of one string.
        # Normalize both fields to plain strings before validation.
        def _to_text(value):
            if isinstance(value, list):
                return " ".join(str(item) for item in value)
            return str(value) if value is not None else ""

        return AgentResponse(
            agent=self.name,
            question=question,
            answer=_to_text(result.get("answer", "")),
            reasoning=_to_text(result.get("reasoning", "")),
            confidence=float(result.get("confidence", 0.5)),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )