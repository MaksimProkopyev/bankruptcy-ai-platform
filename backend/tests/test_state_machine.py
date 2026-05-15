"""Tests for case status state machine."""

from app.models.models import CaseStatus
from app.services.case_machine import (
    get_available_transitions,
    get_status_group,
    is_valid_transition,
)


class TestCaseStateMachine:
    def test_valid_lead_transitions(self):
        assert is_valid_transition(CaseStatus.lead, CaseStatus.qualification)
        assert is_valid_transition(CaseStatus.lead, CaseStatus.rejected)
        assert is_valid_transition(CaseStatus.lead, CaseStatus.cancelled)

    def test_invalid_lead_to_court(self):
        """Can't jump from lead directly to court."""
        assert not is_valid_transition(CaseStatus.lead, CaseStatus.application_filed)
        assert not is_valid_transition(CaseStatus.lead, CaseStatus.debt_discharged)
        assert not is_valid_transition(CaseStatus.lead, CaseStatus.procedure_started)

    def test_valid_happy_path(self):
        """Test the typical successful case flow."""
        path = [
            CaseStatus.lead,
            CaseStatus.qualification,
            CaseStatus.consultation,
            CaseStatus.contract_signing,
            CaseStatus.document_collection,
            CaseStatus.document_review,
            CaseStatus.application_preparation,
            CaseStatus.application_filed,
            CaseStatus.court_accepted,
            CaseStatus.hearing_scheduled,
            CaseStatus.procedure_started,
            CaseStatus.asset_realization,
            CaseStatus.fu_report,
            CaseStatus.completion,
            CaseStatus.debt_discharged,
        ]

        for i in range(len(path) - 1):
            assert is_valid_transition(path[i], path[i + 1]), (
                f"Transition {path[i].value} → {path[i + 1].value} should be valid"
            )

    def test_terminal_states_no_exit(self):
        """Terminal states have no outgoing transitions."""
        assert get_available_transitions(CaseStatus.debt_discharged) == []
        assert get_available_transitions(CaseStatus.rejected) == []
        assert get_available_transitions(CaseStatus.cancelled) == []

    def test_document_review_can_go_back(self):
        """Document review can go back to collection if issues found."""
        assert is_valid_transition(CaseStatus.document_review, CaseStatus.document_collection)

    def test_on_hold_can_resume(self):
        """On hold status can resume to active states."""
        assert is_valid_transition(CaseStatus.on_hold, CaseStatus.document_collection)
        assert is_valid_transition(CaseStatus.on_hold, CaseStatus.cancelled)

    def test_restructuring_can_fail_to_realization(self):
        """If restructuring fails, case goes to asset realization."""
        assert is_valid_transition(CaseStatus.restructuring, CaseStatus.asset_realization)

    def test_status_groups(self):
        assert get_status_group(CaseStatus.lead) == "funnel"
        assert get_status_group(CaseStatus.document_collection) == "preparation"
        assert get_status_group(CaseStatus.asset_realization) == "court"
        assert get_status_group(CaseStatus.debt_discharged) == "completion"
        assert get_status_group(CaseStatus.cancelled) == "special"

    def test_get_available_transitions_returns_sorted(self):
        available = get_available_transitions(CaseStatus.lead)
        assert len(available) == 3
        values = [s.value for s in available]
        assert "qualification" in values
        assert "rejected" in values
        assert "cancelled" in values
