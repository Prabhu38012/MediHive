
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
        """Run this agent on a question. `context` is passed when
        RAG retrieved document chunks are available.
        """
        user_prompt = question
        if context:
            user_prompt = f"Relevant Medical Context:\n{context}\n\nClinical Case / Question:\n{question}"

        result = call_llm(self.system_prompt, user_prompt)

        def _to_text(value):
            if isinstance(value, list):
                return " ".join(str(item) for item in value)
            return str(value).strip() if value is not None else ""

        raw_answer = _to_text(result.get("answer", ""))
        raw_reasoning = _to_text(result.get("reasoning", ""))

        try:
            conf = float(result.get("confidence", 0.75))
            conf = min(max(conf, 0.0), 1.0)
        except (ValueError, TypeError):
            conf = 0.75

        return AgentResponse(
            agent=self.name,
            question=question,
            answer=raw_answer,
            reasoning=raw_reasoning,
            confidence=conf,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )