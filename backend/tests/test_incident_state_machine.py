"""Unit tests for Stage IM1 Incident lifecycle state machine."""

import pytest

from app.models.incident import (
    IncidentStatus,
    InvalidIncidentTransitionError,
    VALID_INCIDENT_TRANSITIONS,
    can_transition,
    validate_transition,
)


def test_state_machine_valid_transitions() -> None:
    """Verify all officially permitted transitions in the incident lifecycle."""
    valid_pairs = [
        (IncidentStatus.NEW, IncidentStatus.ACKNOWLEDGED),
        (IncidentStatus.ACKNOWLEDGED, IncidentStatus.TRIAGED),
        (IncidentStatus.ACKNOWLEDGED, IncidentStatus.RESOLVED),
        (IncidentStatus.TRIAGED, IncidentStatus.ESCALATED),
        (IncidentStatus.TRIAGED, IncidentStatus.RESOLVED),
        (IncidentStatus.ESCALATED, IncidentStatus.TRIAGED),
        (IncidentStatus.ESCALATED, IncidentStatus.ACKNOWLEDGED),
        (IncidentStatus.RESOLVED, IncidentStatus.TRIAGED),
        (IncidentStatus.RESOLVED, IncidentStatus.CLOSED),
    ]

    for current, target in valid_pairs:
        assert can_transition(current, target) is True, f"Expected {current} -> {target} to be valid"
        # Should not raise
        validate_transition(current, target)


def test_state_machine_closed_is_terminal() -> None:
    """Verify that CLOSED status has zero outgoing transitions."""
    assert len(VALID_INCIDENT_TRANSITIONS[IncidentStatus.CLOSED]) == 0
    for target in IncidentStatus:
        assert can_transition(IncidentStatus.CLOSED, target) is False
        with pytest.raises(InvalidIncidentTransitionError):
            validate_transition(IncidentStatus.CLOSED, target)


def test_state_machine_self_transitions_forbidden() -> None:
    """Verify that attempting to transition from status S to status S is rejected."""
    for status in IncidentStatus:
        assert can_transition(status, status) is False
        with pytest.raises(InvalidIncidentTransitionError, match="Incident is already in this status"):
            validate_transition(status, status)


def test_state_machine_full_matrix_exhaustive() -> None:
    """Exhaustively verify the complete 6x6 transition matrix against the formal rule set."""
    expected_valid = {
        (IncidentStatus.NEW, IncidentStatus.ACKNOWLEDGED),
        (IncidentStatus.ACKNOWLEDGED, IncidentStatus.TRIAGED),
        (IncidentStatus.ACKNOWLEDGED, IncidentStatus.RESOLVED),
        (IncidentStatus.TRIAGED, IncidentStatus.ESCALATED),
        (IncidentStatus.TRIAGED, IncidentStatus.RESOLVED),
        (IncidentStatus.ESCALATED, IncidentStatus.TRIAGED),
        (IncidentStatus.ESCALATED, IncidentStatus.ACKNOWLEDGED),
        (IncidentStatus.RESOLVED, IncidentStatus.TRIAGED),
        (IncidentStatus.RESOLVED, IncidentStatus.CLOSED),
    }

    all_statuses = list(IncidentStatus)
    for s1 in all_statuses:
        for s2 in all_statuses:
            is_valid = (s1, s2) in expected_valid
            assert can_transition(s1, s2) is is_valid, f"Matrix mismatch for ({s1}, {s2})"
            if is_valid:
                validate_transition(s1, s2)
            else:
                with pytest.raises(InvalidIncidentTransitionError):
                    validate_transition(s1, s2)


def test_invalid_incident_transition_error_properties() -> None:
    """Verify exception attributes and diagnostic message structure."""
    err = InvalidIncidentTransitionError(
        IncidentStatus.NEW,
        IncidentStatus.CLOSED,
        "Illegal leap to closed",
    )
    assert err.current_status == IncidentStatus.NEW
    assert err.target_status == IncidentStatus.CLOSED
    assert "Cannot transition incident from NEW to CLOSED: Illegal leap to closed" in str(err)
