"""
Event Normalizer
=================
Extracts structured per-turn records from raw conversation JSON.
Merges messages, classifications, state transitions, and function calls
into a unified timeline.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class NormalizedTurn:
    turn_number: int
    role: str                                # "bot" or "borrower"
    text: str
    timestamp: datetime
    state_before: Optional[str] = None       # state at start of this turn
    state_after: Optional[str] = None        # state after this turn
    classification: Optional[str] = None     # bot's classification of borrower msg
    confidence: Optional[str] = None         # high/medium/low
    action: Optional[str] = None             # function_call name if any
    action_params: Optional[dict] = None     # function_call params
    time_since_last_msg: float = 0.0         # minutes since previous message (any role)
    is_outbound: bool = False                # True if bot message not replying to recent borrower msg

    def to_dict(self) -> dict:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


@dataclass
class NormalizedConversation:
    conversation_id: str
    turns: list[NormalizedTurn] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    state_transitions: list[dict] = field(default_factory=list)
    final_state: Optional[str] = None

    # Convenience lookups
    bot_turns: list[NormalizedTurn] = field(default_factory=list)
    borrower_turns: list[NormalizedTurn] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "turns": [t.to_dict() for t in self.turns],
            "metadata": self.metadata,
            "final_state": self.final_state,
        }


class EventNormalizer:
    """Normalize raw conversation JSON into structured per-turn records."""

    def normalize(self, conversation: dict) -> NormalizedConversation:
        conv_id = conversation["conversation_id"]
        messages = conversation.get("messages", [])
        classifications = conversation.get("bot_classifications", [])
        transitions = conversation.get("state_transitions", [])
        function_calls = conversation.get("function_calls", [])
        metadata = conversation.get("metadata", {})

        # Build lookup maps keyed by turn number
        classification_map = {}
        for c in classifications:
            classification_map[c["turn"]] = c

        # Multiple transitions can occur on the same turn
        transition_map: dict[int, list[dict]] = {}
        for t in transitions:
            transition_map.setdefault(t["turn"], []).append(t)

        function_map: dict[int, list[dict]] = {}
        for f in function_calls:
            function_map.setdefault(f["turn"], []).append(f)

        # Track current state
        current_state = "new"
        prev_timestamp = None

        normalized_turns = []
        bot_turns = []
        borrower_turns = []

        for msg in messages:
            ts = self._parse_timestamp(msg["timestamp"])
            turn_num = msg["turn"]
            role = msg["role"]

            # Compute time gap
            time_gap = 0.0
            if prev_timestamp is not None:
                delta = (ts - prev_timestamp).total_seconds() / 60.0
                time_gap = max(0.0, delta)

            # State before this turn
            state_before = current_state

            # Apply transitions for this turn
            turn_transitions = transition_map.get(turn_num, [])
            state_after = current_state
            for tr in turn_transitions:
                if tr["from_state"] == state_after or tr["from_state"] == current_state:
                    state_after = tr["to_state"]
            current_state = state_after

            # Classification (only for borrower messages)
            cls_info = classification_map.get(turn_num)
            classification = cls_info["classification"] if cls_info else None
            confidence = cls_info["confidence"] if cls_info else None

            # Function call
            turn_functions = function_map.get(turn_num, [])
            action = turn_functions[0]["function"] if turn_functions else None
            action_params = turn_functions[0].get("params") if turn_functions else None

            # Determine if outbound (bot message without recent borrower reply)
            is_outbound = False
            if role == "bot":
                # Check if there's a borrower message in the last 30 minutes
                recent_borrower = self._find_recent_borrower_msg(
                    messages, msg, minutes=30
                )
                is_outbound = recent_borrower is None

            nt = NormalizedTurn(
                turn_number=turn_num,
                role=role,
                text=msg["text"],
                timestamp=ts,
                state_before=state_before,
                state_after=state_after,
                classification=classification,
                confidence=confidence,
                action=action,
                action_params=action_params,
                time_since_last_msg=time_gap,
                is_outbound=is_outbound,
            )
            normalized_turns.append(nt)

            if role == "bot":
                bot_turns.append(nt)
            else:
                borrower_turns.append(nt)

            prev_timestamp = ts

        result = NormalizedConversation(
            conversation_id=conv_id,
            turns=normalized_turns,
            metadata=metadata,
            state_transitions=transitions,
            final_state=current_state,
            bot_turns=bot_turns,
            borrower_turns=borrower_turns,
        )
        return result

    def _parse_timestamp(self, ts_str: str) -> datetime:
        """Parse ISO timestamp string."""
        # Handle various formats
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S%z",
        ]:
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        # Fallback: try fromisoformat
        return datetime.fromisoformat(ts_str)

    def _find_recent_borrower_msg(
        self, messages: list, current_msg: dict, minutes: int = 30
    ) -> Optional[dict]:
        """Find the most recent borrower message within `minutes` before current_msg."""
        current_ts = self._parse_timestamp(current_msg["timestamp"])
        best = None
        for msg in messages:
            if msg is current_msg:
                break
            if msg["role"] == "borrower":
                msg_ts = self._parse_timestamp(msg["timestamp"])
                gap = (current_ts - msg_ts).total_seconds() / 60.0
                if 0 <= gap <= minutes:
                    best = msg
        return best
