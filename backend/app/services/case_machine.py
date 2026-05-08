"""Case status state machine.

Defines valid transitions between case statuses.
Prevents invalid jumps (e.g. from 'lead' directly to 'debt_discharged').
"""

from app.models.models import CaseStatus

# Valid transitions: from_status -> set of allowed to_statuses
TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.lead: {
        CaseStatus.qualification,
        CaseStatus.rejected,
        CaseStatus.cancelled,
    },
    CaseStatus.qualification: {
        CaseStatus.consultation,
        CaseStatus.rejected,
        CaseStatus.cancelled,
    },
    CaseStatus.consultation: {
        CaseStatus.contract_signing,
        CaseStatus.rejected,
        CaseStatus.cancelled,
    },
    CaseStatus.contract_signing: {
        CaseStatus.document_collection,
        CaseStatus.cancelled,
    },
    CaseStatus.document_collection: {
        CaseStatus.document_review,
        CaseStatus.on_hold,
        CaseStatus.cancelled,
    },
    CaseStatus.document_review: {
        CaseStatus.document_collection,  # back if issues found
        CaseStatus.application_preparation,
        CaseStatus.on_hold,
    },
    CaseStatus.application_preparation: {
        CaseStatus.document_review,  # back for corrections
        CaseStatus.application_filed,
        CaseStatus.on_hold,
    },
    CaseStatus.application_filed: {
        CaseStatus.court_accepted,
        CaseStatus.on_hold,
    },
    CaseStatus.court_accepted: {
        CaseStatus.hearing_scheduled,
    },
    CaseStatus.hearing_scheduled: {
        CaseStatus.procedure_started,
        CaseStatus.settlement,
        CaseStatus.on_hold,
    },
    CaseStatus.procedure_started: {
        CaseStatus.creditors_registry,
        CaseStatus.restructuring,
        CaseStatus.asset_realization,
        CaseStatus.settlement,
    },
    CaseStatus.creditors_registry: {
        CaseStatus.creditors_meeting,
    },
    CaseStatus.creditors_meeting: {
        CaseStatus.asset_realization,
        CaseStatus.restructuring,
        CaseStatus.settlement,
    },
    CaseStatus.asset_realization: {
        CaseStatus.fu_report,
    },
    CaseStatus.restructuring: {
        CaseStatus.fu_report,
        CaseStatus.asset_realization,  # if restructuring fails
    },
    CaseStatus.fu_report: {
        CaseStatus.completion,
    },
    CaseStatus.completion: {
        CaseStatus.debt_discharged,
    },
    CaseStatus.on_hold: {
        # Can resume to most active statuses
        CaseStatus.document_collection,
        CaseStatus.application_preparation,
        CaseStatus.application_filed,
        CaseStatus.hearing_scheduled,
        CaseStatus.cancelled,
    },
    # Terminal states — no transitions out
    CaseStatus.debt_discharged: set(),
    CaseStatus.rejected: set(),
    CaseStatus.cancelled: set(),
    CaseStatus.settlement: {
        CaseStatus.debt_discharged,  # settlement completes the process
    },
}


def is_valid_transition(from_status: CaseStatus, to_status: CaseStatus) -> bool:
    """Check if a status transition is allowed."""
    allowed = TRANSITIONS.get(from_status, set())
    return to_status in allowed


def get_available_transitions(current_status: CaseStatus) -> list[CaseStatus]:
    """Get list of statuses the case can transition to."""
    return sorted(TRANSITIONS.get(current_status, set()), key=lambda s: s.value)


def get_status_group(status: CaseStatus) -> str:
    """Return the pipeline group for a status."""
    groups = {
        "funnel": {CaseStatus.lead, CaseStatus.qualification, CaseStatus.consultation, CaseStatus.contract_signing},
        "preparation": {CaseStatus.document_collection, CaseStatus.document_review, CaseStatus.application_preparation},
        "court": {
            CaseStatus.application_filed, CaseStatus.court_accepted, CaseStatus.hearing_scheduled,
            CaseStatus.procedure_started, CaseStatus.creditors_registry, CaseStatus.creditors_meeting,
            CaseStatus.asset_realization, CaseStatus.restructuring,
        },
        "completion": {CaseStatus.fu_report, CaseStatus.completion, CaseStatus.debt_discharged},
        "special": {CaseStatus.on_hold, CaseStatus.rejected, CaseStatus.cancelled, CaseStatus.settlement},
    }
    for group_name, statuses in groups.items():
        if status in statuses:
            return group_name
    return "unknown"
