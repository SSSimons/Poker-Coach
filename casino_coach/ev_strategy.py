from __future__ import annotations

import random

from casino_coach.poker import PokerCard, compare, evaluate, fresh_deck
from casino_coach.ranges import compact_code, deal_ranged_hand


POSTFLOP_ORDER = {"SB": 0, "BB": 1, "UTG": 2, "HJ": 3, "CO": 4, "BTN": 5}


def acts_first_postflop(first_position: str, second_position: str) -> bool:
    """Return whether the first position acts before the second postflop."""
    return POSTFLOP_ORDER[first_position] < POSTFLOP_ORDER[second_position]


def estimate_equity_vs_range(
    hole: list[PokerCard],
    board: list[PokerCard],
    opponent_position: str,
    rng: random.Random,
    samples: int = 120,
) -> float:
    """Estimate showdown equity without looking at the opponent's actual cards.

    Opponent hands are sampled from the configured positional range and every
    unfinished board is independently run out. This is intentionally a small,
    local Monte Carlo calculation so EV Battle also works offline.
    """
    if samples <= 0:
        raise ValueError("samples must be positive")

    visible_codes = {compact_code(item) for item in hole + board}
    score = 0.0
    for _ in range(samples):
        opponent = deal_ranged_hand(opponent_position, rng, visible_codes)
        used = set(hole + board + opponent)
        deck = [item for item in fresh_deck(rng) if item not in used]
        runout = board + [deck.pop() for _ in range(5 - len(board))]
        result, _, _ = compare(hole, opponent, runout)
        score += 1.0 if result > 0 else 0.5 if result == 0 else 0.0
    return score / samples


def bot_open_decision(profile: str, made_category: int, equity: float) -> tuple[str, float]:
    """Choose CHECK or a pot-relative BET for a bot opening the action."""
    if profile == "philip":
        if made_category >= 2 and equity >= 0.66:
            return "bet", 0.65
        return "check", 0.0

    if profile == "timofey":
        if made_category >= 2 and equity >= 0.62:
            return "bet", 0.70
        if made_category >= 1 and equity >= 0.55:
            return "bet", 0.50
        return "check", 0.0

    if profile == "lena":
        if made_category >= 2 and equity >= 0.68:
            return "bet", 0.55
        return "check", 0.0

    raise ValueError(f"Unknown bot profile: {profile}")


def bot_facing_decision(
    profile: str,
    made_category: int,
    equity: float,
    amount_to_call: int,
    pot_after_bet: int,
    *,
    can_raise: bool,
) -> str:
    """Choose a legal response using pot odds and the profile's documented leak."""
    if amount_to_call <= 0:
        raise ValueError("amount_to_call must be positive")
    pot_odds = amount_to_call / max(1, pot_after_bet + amount_to_call)

    if profile == "philip":
        threshold = max(0.64 if made_category == 0 else 0.58, pot_odds + 0.22)
        raise_threshold = 0.84
    elif profile == "timofey":
        threshold = max(0.52 if made_category == 0 else 0.48, pot_odds + 0.12)
        raise_threshold = 0.80
    elif profile == "lena":
        threshold = max(0.38 if made_category == 0 else 0.34, pot_odds + 0.05)
        raise_threshold = 0.88
    else:
        raise ValueError(f"Unknown bot profile: {profile}")

    # Two pair or better should not be thrown away solely because a range
    # estimate landed just below a profile threshold.
    continues = made_category >= 2 or equity >= threshold
    if not continues:
        return "fold"
    if can_raise and made_category >= 2 and equity >= raise_threshold:
        return "raise"
    return "call"


def made_category(hole: list[PokerCard], board: list[PokerCard]) -> int:
    return evaluate(hole + board)[0][0]
