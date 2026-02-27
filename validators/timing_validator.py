"""
Timing Validator (Layer 1)
===========================
Enforces timing rules from spec Section 6.
All checks are pure timestamp math — deterministic with exact reasoning.
"""

from datetime import timedelta
from normalizer import NormalizedConversation


# IST offset: UTC+5:30
IST_OFFSET = timedelta(hours=5, minutes=30)

# Quiet hours: 7 PM (19:00) to 8 AM (08:00) IST
QUIET_START_HOUR = 19
QUIET_END_HOUR = 8

# Follow-up spacing: 4 hours minimum
FOLLOWUP_MIN_MINUTES = 240  # 4 hours

# Dormancy timeout: 7 days
DORMANCY_MINUTES = 10080  # 7 days = 10,080 minutes

# Grace period for reply detection (bot replying to borrower during quiet hours)
REPLY_GRACE_MINUTES = 30


class TimingValidator:
    """Validate timing rules: quiet hours, follow-up spacing, dormancy."""

    def check(self, conv: NormalizedConversation) -> list[dict]:
        violations = []
        violations.extend(self._check_quiet_hours(conv))
        violations.extend(self._check_followup_spacing(conv))
        violations.extend(self._check_dormancy(conv))
        return violations

    def _get_ist_hour(self, ts) -> int:
        """Get the hour in IST. Timestamps are assumed IST if naive."""
        # If timestamp is naive, assume IST
        if ts.tzinfo is None:
            return ts.hour
        # If timezone-aware, convert
        ist_time = ts + IST_OFFSET - ts.utcoffset()
        return ist_time.hour

    def _is_quiet_hours(self, ts) -> bool:
        """Check if timestamp falls in quiet hours (7PM-8AM IST)."""
        hour = self._get_ist_hour(ts)
        return hour >= QUIET_START_HOUR or hour < QUIET_END_HOUR

    def _check_quiet_hours(self, conv: NormalizedConversation) -> list[dict]:
        """Check 1: No outbound bot messages during quiet hours (7PM-8AM IST).
        Exception: bot may reply if borrower messaged recently."""
        violations = []

        for bot_turn in conv.bot_turns:
            if not self._is_quiet_hours(bot_turn.timestamp):
                continue

            # Check if this is a reply to a recent borrower message
            is_reply = False
            for borrower_turn in conv.borrower_turns:
                gap = (bot_turn.timestamp - borrower_turn.timestamp).total_seconds() / 60.0
                if 0 < gap <= REPLY_GRACE_MINUTES:
                    is_reply = True
                    break

            if not is_reply:
                hour = self._get_ist_hour(bot_turn.timestamp)
                violations.append({
                    "turn": bot_turn.turn_number,
                    "rule": "Section 6.1 — Quiet Hours",
                    "severity": 0.6,
                    "category": "timing",
                    "explanation": (
                        f"Bot sent outbound message at {bot_turn.timestamp.isoformat()} IST "
                        f"(hour: {hour}:00, quiet hours: 7PM-8AM). No recent borrower message "
                        f"found within {REPLY_GRACE_MINUTES} minutes to justify this as a reply."
                    ),
                })

        return violations

    def _check_followup_spacing(self, conv: NormalizedConversation) -> list[dict]:
        """Check 2: At least 4 hours between consecutive unanswered bot messages."""
        violations = []

        # Find consecutive bot messages with no borrower reply between them
        all_turns = sorted(conv.turns, key=lambda t: t.timestamp)

        prev_bot_turn = None
        borrower_replied_since = True

        for turn in all_turns:
            if turn.role == "borrower":
                borrower_replied_since = True
                prev_bot_turn = None  # Reset
                continue

            if turn.role == "bot":
                if prev_bot_turn is not None and not borrower_replied_since:
                    # Consecutive bot messages without borrower reply
                    gap_minutes = (
                        turn.timestamp - prev_bot_turn.timestamp
                    ).total_seconds() / 60.0

                    if gap_minutes < FOLLOWUP_MIN_MINUTES:
                        violations.append({
                            "turn": turn.turn_number,
                            "rule": "Section 6.2 — Follow-Up Spacing",
                            "severity": 0.5,
                            "category": "timing",
                            "explanation": (
                                f"Bot sent follow-up at turn {turn.turn_number} only "
                                f"{gap_minutes:.0f} minutes after unanswered message at "
                                f"turn {prev_bot_turn.turn_number}. "
                                f"Minimum spacing: {FOLLOWUP_MIN_MINUTES} minutes (4 hours)."
                            ),
                        })

                prev_bot_turn = turn
                borrower_replied_since = False

        return violations

    def _check_dormancy(self, conv: NormalizedConversation) -> list[dict]:
        """Check 3: Conversation should be marked dormant if borrower hasn't
        responded for 7 days (10,080 minutes)."""
        violations = []

        if not conv.borrower_turns:
            return violations

        # Find the last borrower message
        last_borrower = max(conv.borrower_turns, key=lambda t: t.timestamp)

        # Find the latest event in the conversation
        last_event = max(conv.turns, key=lambda t: t.timestamp)

        gap_minutes = (
            last_event.timestamp - last_borrower.timestamp
        ).total_seconds() / 60.0

        terminal_states = {"dormant", "escalated", "payment_confirmed"}

        if gap_minutes > DORMANCY_MINUTES and conv.final_state not in terminal_states:
            gap_days = gap_minutes / 1440
            violations.append({
                "turn": last_event.turn_number,
                "rule": "Section 6.3 — Dormancy Timeout",
                "severity": 0.7,
                "category": "timing",
                "explanation": (
                    f"Borrower last responded at turn {last_borrower.turn_number} "
                    f"({last_borrower.timestamp.isoformat()}). Last conversation event "
                    f"was {gap_days:.1f} days later. Conversation should have been "
                    f"marked dormant after 7 days. Final state: '{conv.final_state}'."
                ),
            })

        return violations
