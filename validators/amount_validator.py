"""
Amount Validator (Layer 1)
===========================
Enforces financial rules from spec Section 9.
All checks are deterministic with exact reasoning.
"""

import re
from normalizer import NormalizedConversation


class AmountValidator:
    """Validate financial amount rules: POS/TOS relationships, settlement bounds,
    and amount consistency across turns."""

    # Regex to extract INR amounts from text (handles ₹1,23,456 / Rs. 123456 / etc.)
    AMOUNT_PATTERN = re.compile(
        r'(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)', re.IGNORECASE
    )

    def check(self, conv: NormalizedConversation) -> list[dict]:
        violations = []
        meta = conv.metadata

        pos = meta.get("pos")
        tos = meta.get("tos")
        settlement = meta.get("settlement_offered")

        violations.extend(self._check_pos_tos(conv, pos, tos))
        violations.extend(self._check_settlement_bounds(conv, pos, tos, settlement))
        violations.extend(self._check_suspicious_floor(conv, pos, settlement))
        violations.extend(self._check_amount_consistency(conv, tos))

        return violations

    def _check_pos_tos(
        self, conv: NormalizedConversation, pos, tos
    ) -> list[dict]:
        """Check 1: POS must be ≤ TOS (data integrity)."""
        violations = []
        if pos is not None and tos is not None and pos > tos:
            violations.append({
                "turn": 0,
                "rule": "Amount Rule A1 — POS ≤ TOS",
                "severity": 0.8,
                "category": "amounts",
                "explanation": (
                    f"POS ({pos:,}) > TOS ({tos:,}). This indicates corrupted data. "
                    f"POS (principal outstanding) should always be ≤ TOS "
                    f"(total outstanding = POS + penalties + interest)."
                ),
            })
        return violations

    def _check_settlement_bounds(
        self, conv: NormalizedConversation, pos, tos, settlement
    ) -> list[dict]:
        """Check 2: Settlement offered must be ≤ TOS."""
        violations = []
        if settlement is not None and tos is not None and settlement > tos:
            violations.append({
                "turn": 0,
                "rule": "Amount Rule A3 — Settlement ≤ TOS",
                "severity": 0.8,
                "category": "amounts",
                "explanation": (
                    f"Settlement offered ({settlement:,}) exceeds TOS ({tos:,}). "
                    f"Settlement amount must be between the floor and TOS inclusive."
                ),
            })
        return violations

    def _check_suspicious_floor(
        self, conv: NormalizedConversation, pos, settlement
    ) -> list[dict]:
        """Check 3: Heuristic floor check — settlement < 50% of POS is suspicious.
        (Settlement floor not available in data, so we use a proxy.)"""
        violations = []
        # Settlement floor assumed to be 70% of POS
        floor = 0.7 * pos if pos else None

        if (
            settlement is not None
            and floor is not None
            and pos > 0
            and settlement < floor
        ):
            ratio = settlement / pos
            violations.append({
                "turn": 0,
                "rule": "Amount Rule A4 — Below Settlement Floor",
                "severity": 0.6,
                "category": "amounts",
                "explanation": (
                    f"Settlement offered ({settlement:,}) is {ratio:.0%} of POS ({pos:,}), "
                    f"which is below the assumed settlement floor of 70% POS "
                    f"(floor = {floor:,.0f}). "
                    f"Agent should counter with floor amount or escalate for ZCM approval."
                ),
            })
        return violations

    def _check_amount_consistency(
        self, conv: NormalizedConversation, tos
    ) -> list[dict]:
        """Check 4: Amount consistency — once an amount is quoted, subsequent
        references should be consistent unless re-approved by ZCM."""
        violations = []

        # Extract all amounts mentioned in bot messages
        quoted_amounts = []
        for turn in conv.bot_turns:
            amounts = self._extract_amounts(turn.text)
            for amt in amounts:
                quoted_amounts.append({
                    "turn": turn.turn_number,
                    "amount": amt,
                    "text": turn.text,
                })

        if len(quoted_amounts) < 2:
            return violations

        # Check for inconsistencies: group amounts and see if they differ
        # Allow TOS and settlement to coexist (they're different things)
        # Flag if the SAME concept (settlement) is quoted differently
        settlement_amounts = []
        for qa in quoted_amounts:
            # Skip TOS/POS references (these are informational)
            if tos and abs(qa["amount"] - tos) < 100:
                continue
            settlement_amounts.append(qa)

        if len(settlement_amounts) >= 2:
            unique_amounts = set(qa["amount"] for qa in settlement_amounts)
            if len(unique_amounts) > 1:
                # Check if there's a ZCM re-approval between them
                has_zcm_reapproval = any(
                    t.action == "request_settlement_amount"
                    for t in conv.turns
                    if t.turn_number > settlement_amounts[0]["turn"]
                )

                if not has_zcm_reapproval:
                    amounts_str = ", ".join(
                        f"₹{qa['amount']:,.0f} (turn {qa['turn']})"
                        for qa in settlement_amounts
                    )
                    violations.append({
                        "turn": settlement_amounts[1]["turn"],
                        "rule": "Amount Rule A5 — Consistency",
                        "severity": 0.6,
                        "category": "amounts",
                        "explanation": (
                            f"Inconsistent settlement amounts quoted by bot: {amounts_str}. "
                            f"Once a settlement is quoted, it must remain consistent "
                            f"unless re-approved by ZCM."
                        ),
                    })

        return violations

    def _extract_amounts(self, text: str) -> list[float]:
        """Extract numeric amounts from text (INR format)."""
        amounts = []
        for match in self.AMOUNT_PATTERN.finditer(text):
            amount_str = match.group(1).replace(",", "")
            try:
                amounts.append(float(amount_str))
            except ValueError:
                continue
        return amounts
