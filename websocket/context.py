import re
from typing import Optional

# exmple of what some docts could look like (thanks chat)
POLICY_DOCS = [
    {
        "id": "pol_001",
        "title": "Data Retention Policy",
        "content": "All user data must be retained for a minimum of 90 days and a maximum of 7 years. "
                   "Personal data must be encrypted at rest using AES-256. "
                   "Data deletion requests must be fulfilled within 30 days of receipt."
    },
    {
        "id": "pol_002",
        "title": "Access Control Policy",
        "content": "All internal systems require multi-factor authentication. "
                   "Access to production systems is restricted to senior engineers and above. "
                   "API keys must be rotated every 90 days. Service accounts must follow least-privilege principles."
    },
    {
        "id": "pol_003",
        "title": "Incident Response Policy",
        "content": "Security incidents must be reported within 1 hour of detection. "
                   "A post-mortem must be completed within 5 business days of resolution. "
                   "All incidents are classified as P0 (critical), P1 (high), P2 (medium), or P3 (low)."
    },
    {
        "id": "pol_004",
        "title": "Remote Work Policy",
        "content": "Employees may work remotely up to 3 days per week. "
                   "A VPN must be used when accessing internal systems from outside the office. "
                   "Home office equipment stipend is $500 per year."
    },
    {
        "id": "pol_005",
        "title": "AI Usage Policy",
        "content": "Employees may use approved AI tools for productivity. "
                   "Confidential data must not be entered into external AI systems. "
                   "All AI-generated content must be reviewed before publication or client delivery."
    },
    {
        "id": "pol_006",
        "title": "Password Policy",
        "content": "Passwords must be at least 12 characters long and include uppercase, lowercase, numbers, and symbols. "
                   "Passwords must not be reused within the last 10 cycles. "
                   "Password managers are required for all staff."
    },
    {
        "id": "pol_007",
        "title": "Leave and Time Off Policy",
        "content": "Full-time employees receive 15 days of paid time off per year. "
                   "Unused PTO rolls over up to a maximum of 10 days. "
                   "Sick leave is separate from PTO and is not capped."
    },
    {
        "id": "pol_008",
        "title": "Third Party Vendor Policy",
        "content": "All third-party vendors must complete a security review before onboarding. "
                   "Vendors with access to customer data must sign a data processing agreement. "
                   "Vendor contracts must be reviewed annually."
    }
]

def _tokenize(text: str) -> set:
    """Lowercase and split text into a set of words, stripping punctuation."""
    return set(re.findall(r'\b\w+\b', text.lower()))

def _score(query_tokens: set, doc: dict) -> int:
    """Count how many query tokens appear in the document title + content."""
    doc_tokens = _tokenize(doc["title"] + " " + doc["content"])
    return len(query_tokens & doc_tokens)


def retrieve(message: dict, top_k: int = 2) -> list[dict]:
    """
    Search the policy store for documents relevant to the message text.
    Returns the top_k most relevant policy chunks.
    Returns empty list if no relevant docs found (score == 0).
    """
    query = message.get("text", "")
    if not query.strip():
        return []

    query_tokens = _tokenize(query)

    # Score all docs
    scored = [(doc, _score(query_tokens, doc)) for doc in POLICY_DOCS]

    # Filter out zero-score docs and sort by score descending
    relevant = sorted(
        [(doc, score) for doc, score in scored if score > 0],
        key=lambda x: x[1],
        reverse=True
    )

    return [doc for doc, _ in relevant[:top_k]]

def augment(message: dict) -> dict:
    """
    Retrieve relevant policy context and inject it into the message.
    Adds a 'context' field to the message dict with retrieved chunks.
    Original message is not modified — returns a new dict.
    """
    relevant_docs = retrieve(message)

    if not relevant_docs:
        return {**message, "context": None, "context_ids": []}

    # Format context as a readable string for the orchestrator prompt
    context_text = "\n\n".join(
        f"[{doc['title']}]: {doc['content']}"
        for doc in relevant_docs
    )

    return {
        **message,
        "context": context_text,
        "context_ids": [doc["id"] for doc in relevant_docs]
    }