"""Conservative recommendations, never ticket mutations or calibrated predictions."""

import re

from resolveflow.workflows.contracts import PriorityRecommendation

LEVELS = ["low", "medium", "high", "urgent"]
RULES = [
    ("security_incident", "urgent", r"\b(?:data breach|account compromised|active attack)\b"),
    ("service_outage", "high", r"\b(?:service down|production outage|all users blocked)\b"),
    ("access_blocked", "high", r"\b(?:locked out|cannot log in|unable to sign in)\b"),
]


def recommend(title: str, description: str, existing: str) -> PriorityRecommendation:
    suggestion, reasons = existing, ["preserve_existing_priority"]
    for rule_id, priority, pattern in RULES:
        if re.search(pattern, title + "\n" + description, re.I):
            reasons.append(rule_id)
            if LEVELS.index(priority) > LEVELS.index(suggestion):
                suggestion = priority
    return PriorityRecommendation(suggested_priority=suggestion, rule_ids=reasons)
