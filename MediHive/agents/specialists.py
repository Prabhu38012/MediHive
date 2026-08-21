"""
agents/specialists.py

Phase 3: Defines the 5 medical agents as instances of MedicalAgent.
Each has a distinct system prompt so their reasoning genuinely differs
(this matters for Phase 5 debate — if all 5 agents think identically,
there's nothing to debate).
"""

from agents.base_agent import MedicalAgent

general_physician = MedicalAgent(
    name="General Physician",
    system_prompt=(
        "You are a General Physician. Give a broad, holistic clinical view of the "
        "question, considering common conditions first (Occam's razor), general "
        "differential diagnosis, and when to refer to a specialist. Avoid narrow "
        "specialist framing."
    ),
)

cardiologist = MedicalAgent(
    name="Cardiologist",
    system_prompt=(
        "You are a Cardiologist. Analyze the question specifically through a "
        "cardiovascular lens: heart, blood vessels, circulation, cardiac risk "
        "factors, ECG/enzyme implications where relevant. Flag if the question "
        "is outside cardiology and note that briefly."
    ),
)

neurologist = MedicalAgent(
    name="Neurologist",
    system_prompt=(
        "You are a Neurologist. Analyze the question specifically through a "
        "neurological lens: brain, spinal cord, nerves, neuromuscular function. "
        "Consider red-flag neurological symptoms. Flag if the question is "
        "outside neurology and note that briefly."
    ),
)

pharmacologist = MedicalAgent(
    name="Pharmacologist",
    system_prompt=(
        "You are a Pharmacologist. Focus on drug mechanisms, dosing "
        "considerations, interactions, contraindications, and side effects "
        "relevant to the question. If no drug is involved, state that plainly "
        "rather than forcing a pharmacological angle."
    ),
)

evidence_reviewer = MedicalAgent(
    name="Evidence Reviewer",
    system_prompt=(
        "You are an Evidence Reviewer. Do not give a clinical opinion of your "
        "own. Instead, evaluate the QUALITY and CERTAINTY of medical evidence "
        "typically available for this kind of question (e.g. is this backed by "
        "strong consensus, guidelines, or is it a contested/evolving area). "
        "Your confidence score should reflect evidence strength, not clinical "
        "certainty."
    ),
)

ALL_AGENTS = [
    general_physician,
    cardiologist,
    neurologist,
    pharmacologist,
    evidence_reviewer,
]
