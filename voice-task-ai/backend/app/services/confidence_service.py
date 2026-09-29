"""
Phase 7 — AI Review: confidence-based routing.

Decides what should happen to an extraction result before anything gets
saved as a real Task/Order/Payment, per the project spec's thresholds:
    >= 0.85            -> auto_create   (safe to save immediately)
    0.60 - 0.84         -> confirm_review (show the user, let them confirm/edit)
    <  0.60             -> manual_review  (needs real human attention)
needs_clarification always forces manual_review regardless of confidence,
since a missing critical field (e.g. a meeting with no time) means the
extraction is incomplete no matter how confident the model is about the
part it did fill in.
"""
from app.schemas.extraction import ExtractionResult

AUTO_CREATE_THRESHOLD = 0.85
CONFIRM_REVIEW_THRESHOLD = 0.60

RecommendedAction = str  # "auto_create" | "confirm_review" | "manual_review"


def determine_action(extraction: ExtractionResult) -> RecommendedAction:
    if extraction.needs_clarification:
        return "manual_review"
    if extraction.confidence >= AUTO_CREATE_THRESHOLD:
        return "auto_create"
    if extraction.confidence >= CONFIRM_REVIEW_THRESHOLD:
        return "confirm_review"
    return "manual_review"
