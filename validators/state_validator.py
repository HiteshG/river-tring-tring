"""
State Transition Validator (Layer 1)
=====================================
Enforces the transition matrix from spec Section 4.
All checks are deterministic with exact violation reasoning.
"""

from normalizer import NormalizedConversation

# Progression states in order (index = order)
STATE_ORDER = {
    "new": 0,
    "message_received": 1,
    "verification": 2,
    "intent_asked": 3,
    "settlement_explained": 4,
    "amount_pending": 5,
    "amount_sent": 6,
    "date_amount_asked": 7,
    "payment_confirmed": 8,
}

EXIT_STATES = {"escalated", "dormant"}

# Allowed forward transitions (excluding self-transitions, escalation, dormancy)
ALLOWED_FORWARD = {
    "new":                  {"message_received"},
    "message_received":     {"verification"},
    "verification":         {"intent_asked"},
    "intent_asked":         {"settlement_explained"},
    "settlement_explained": {"amount_pending"},
    "amount_pending":       {"amount_sent"},
    "amount_sent":          {"date_amount_asked"},
    "date_amount_asked":    {"payment_confirmed"},
    "payment_confirmed":    set(),
}

# Allowed backward exception: settlement_explained/amount_pending → intent_asked
BACKWARD_EXCEPTION_FROM = {"settlement_explained", "amount_pending"}
BACKWARD_EXCEPTION_TO = "intent_asked"

# Action-to-valid-transition mapping
VALID_ACTION_TRANSITIONS = {
    "request_settlement_amount": {
        "from": "settlement_explained",
        "to": "amount_pending",
    },
    "send_settlement_amount": {
        "from": "amount_pending",
        "to": "amount_sent",
    },
    "confirm_payment": {
        "from": "date_amount_asked",
        "to": "payment_confirmed",
    },
    "escalate": {
        "from": None,  # any state
        "to": "escalated",
    },
    "zcm_timeout": {
        "from": "amount_pending",
        "to": "escalated",
    },
}

# Classifications that require escalation
ESCALATION_TRIGGER_CLASSIFICATIONS = {"disputes", "refuses", "hardship"}


class StateTransitionValidator:
    """Validate state transitions against the spec's transition matrix."""

    def check(self, conv: NormalizedConversation) -> list[dict]:
        violations = []
        transitions = conv.state_transitions

        # Build classification lookup
        cls_map = {}
        for turn in conv.turns:
            if turn.classification:
                cls_map[turn.turn_number] = {
                    "classification": turn.classification,
                    "confidence": turn.confidence,
                }

        # Build function call lookup
        action_map = {}
        for turn in conv.turns:
            if turn.action:
                action_map[turn.turn_number] = {
                    "action": turn.action,
                    "params": turn.action_params,
                }

        # Track if conversation has reached an exit state
        exit_state_turn = None
        exit_state_name = None

        # Track if escalation-triggering classifications have been followed by escalation
        escalation_triggers_seen = []  # list of (turn, classification)
        escalation_occurred = False

        for tr in transitions:
            turn = tr["turn"]
            from_state = tr["from_state"]
            to_state = tr["to_state"]

            # ---- Check 1: Exit state finality (I2) ----
            if exit_state_turn is not None and from_state in EXIT_STATES:
                # Any transition FROM an exit state is a violation
                violations.append({
                    "turn": turn,
                    "rule": "Invariant I2 — Exit States Are Final",
                    "severity": 1.0,
                    "category": "state_integrity",
                    "explanation": (
                        f"Transition from exit state '{from_state}' to '{to_state}' "
                        f"at turn {turn}. No transitions are allowed out of exit states "
                        f"(escalated/dormant). Exit occurred at turn {exit_state_turn}."
                    ),
                })
                continue

            # Record when we enter an exit state
            if to_state in EXIT_STATES:
                if exit_state_turn is None:
                    exit_state_turn = turn
                    exit_state_name = to_state
                if to_state == "escalated":
                    escalation_occurred = True
                continue  # Escalation/dormancy from any progression state is always valid

            # Self-transition (staying in same state) — always valid
            if from_state == to_state:
                continue

            # payment_received override: any state → payment_confirmed
            if to_state == "payment_confirmed" and from_state != "date_amount_asked":
                # This is the payment_received override — valid from any progression state
                continue

            # ---- Check 2: Illegal backward transition (I1) ----
            from_order = STATE_ORDER.get(from_state, -1)
            to_order = STATE_ORDER.get(to_state, -1)

            if to_order < from_order:
                # Check if this is the allowed backward exception
                if (
                    from_state in BACKWARD_EXCEPTION_FROM
                    and to_state == BACKWARD_EXCEPTION_TO
                ):
                    # Valid only if classification is unclear + low confidence
                    cls_info = cls_map.get(turn, {})
                    if (
                        cls_info.get("classification") == "unclear"
                        and cls_info.get("confidence") == "low"
                    ):
                        # Allowed exception
                        continue
                    else:
                        violations.append({
                            "turn": turn,
                            "rule": "Section 4.7 — Backward Exception Conditions",
                            "severity": 0.8,
                            "category": "state_integrity",
                            "explanation": (
                                f"Backward transition {from_state} → {to_state} at turn {turn}. "
                                f"This backward move is only allowed when classification='unclear' "
                                f"with confidence='low'. Got classification='{cls_info.get('classification')}' "
                                f"confidence='{cls_info.get('confidence')}'."
                            ),
                        })
                        continue
                else:
                    violations.append({
                        "turn": turn,
                        "rule": "Invariant I1 — No Going Backwards",
                        "severity": 0.8,
                        "category": "state_integrity",
                        "explanation": (
                            f"Illegal backward transition {from_state} → {to_state} at turn {turn}. "
                            f"Only settlement_explained/amount_pending → intent_asked is allowed "
                            f"(with classification=unclear+low). All other backward transitions "
                            f"are spec violations."
                        ),
                    })
                    continue

            # ---- Check 3: Illegal forward skip ----
            if to_state not in ALLOWED_FORWARD.get(from_state, set()):
                violations.append({
                    "turn": turn,
                    "rule": "Section 4 — Transition Matrix",
                    "severity": 0.8,
                    "category": "state_integrity",
                    "explanation": (
                        f"Illegal transition {from_state} → {to_state} at turn {turn}. "
                        f"Allowed targets from '{from_state}': "
                        f"{ALLOWED_FORWARD.get(from_state, set()) | {'escalated', 'dormant'}}."
                    ),
                })

        # ---- Check 4: Action-state mismatch (I4) ----
        for turn_num, action_info in action_map.items():
            action = action_info["action"]
            valid = VALID_ACTION_TRANSITIONS.get(action)

            if valid is None:
                continue  # Unknown action, skip

            # Find the transition at this turn
            turn_transitions = [
                t for t in transitions if t["turn"] == turn_num
            ]

            matched = False
            for tr in turn_transitions:
                from_ok = valid["from"] is None or tr["from_state"] == valid["from"]
                to_ok = tr["to_state"] == valid["to"]
                if from_ok and to_ok:
                    matched = True
                    break

            if not matched and turn_transitions:
                actual = [
                    f"{t['from_state']}→{t['to_state']}" for t in turn_transitions
                ]
                expected_from = valid["from"] or "any"
                violations.append({
                    "turn": turn_num,
                    "rule": "Invariant I4 — Actions Must Match States",
                    "severity": 0.8,
                    "category": "state_integrity",
                    "explanation": (
                        f"Action '{action}' called at turn {turn_num} during transition(s) "
                        f"{actual}. Expected transition: {expected_from} → {valid['to']}."
                    ),
                })

        # ---- Check 5: Missing escalation on trigger classifications ----
        for turn in conv.turns:
            if turn.classification in ESCALATION_TRIGGER_CLASSIFICATIONS:
                escalation_triggers_seen.append(
                    (turn.turn_number, turn.classification)
                )

        if escalation_triggers_seen and not escalation_occurred:
            # Consolidate: report the first missed trigger
            first_trigger = escalation_triggers_seen[0]
            all_triggers = ", ".join(
                f"turn {t}: {c}" for t, c in escalation_triggers_seen
            )
            violations.append({
                "turn": first_trigger[0],
                "rule": "Section 4.3 — Escalation Requirements",
                "severity": 0.8,
                "category": "state_integrity",
                "explanation": (
                    f"Escalation-triggering classifications detected but conversation "
                    f"was not escalated. Triggers: [{all_triggers}]. "
                    f"Spec requires escalation for disputes/refuses/hardship."
                ),
            })

        # ---- Check 6: Messages after exit state (I2 complement) ----
        if exit_state_turn is not None:
            for turn in conv.bot_turns:
                # Find the exit transition timestamp
                exit_ts = None
                for t in conv.turns:
                    if t.turn_number == exit_state_turn:
                        exit_ts = t.timestamp
                        break

                if exit_ts and turn.timestamp > exit_ts and turn.role == "bot":
                    violations.append({
                        "turn": turn.turn_number,
                        "rule": "Invariant I2 — Exit States Are Final",
                        "severity": 1.0,
                        "category": "state_integrity",
                        "explanation": (
                            f"Bot sent message at turn {turn.turn_number} "
                            f"(timestamp: {turn.timestamp.isoformat()}) after conversation "
                            f"entered exit state '{exit_state_name}' at turn {exit_state_turn}. "
                            f"No automated messages should be sent after exit."
                        ),
                    })

        return violations
