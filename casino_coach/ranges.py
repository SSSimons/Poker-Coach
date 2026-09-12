from __future__ import annotations

import random

from casino_coach.poker import PokerCard, card


SUITS = "shdc"
SUIT_CODES = {"♠": "s", "♥": "h", "♦": "d", "♣": "c"}

# Compact six-max training ranges. They intentionally contain no trash hands:
# every dealt holding can reasonably appear in the stated position's range.
POSITION_RANGES = {
    "UTG": ("AA", "KK", "QQ", "JJ", "TT", "99", "AKs", "AQs", "AJs", "KQs", "AKo", "AQo"),
    "HJ": ("AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "AKs", "AQs", "AJs", "ATs", "KQs", "KJs", "QJs", "JTs", "AKo", "AQo", "AJo", "KQo"),
    "CO": ("AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "AKs", "AQs", "AJs", "ATs", "A9s", "KQs", "KJs", "KTs", "QJs", "QTs", "JTs", "T9s", "98s", "87s", "AKo", "AQo", "AJo", "ATo", "KQo", "KJo", "QJo"),
    "BTN": ("AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22", "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s", "KQs", "KJs", "KTs", "K9s", "QJs", "QTs", "Q9s", "JTs", "J9s", "T9s", "98s", "87s", "76s", "65s", "AKo", "AQo", "AJo", "ATo", "A9o", "KQo", "KJo", "KTo", "QJo", "QTo", "JTo"),
    "SB": ("AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "AKs", "AQs", "AJs", "ATs", "A9s", "A5s", "KQs", "KJs", "KTs", "QJs", "QTs", "JTs", "T9s", "98s", "87s", "AKo", "AQo", "AJo", "ATo", "KQo", "KJo", "QJo"),
    "BB": ("AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22", "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s", "KQs", "KJs", "KTs", "K9s", "QJs", "QTs", "Q9s", "JTs", "J9s", "T9s", "98s", "87s", "76s", "65s", "54s", "AKo", "AQo", "AJo", "ATo", "KQo", "KJo", "KTo", "QJo", "QTo", "JTo"),
}

MATCHUPS = (
    ("BTN", "BB"),
    ("CO", "BTN"),
    ("BB", "BTN"),
    ("SB", "BTN"),
    ("HJ", "CO"),
)


def combo_notation(cards: list[PokerCard]) -> str:
    first, second = cards
    first_rank = "T" if first.rank == "10" else first.rank
    second_rank = "T" if second.rank == "10" else second.rank
    if first_rank == second_rank:
        return first_rank * 2
    suffix = "s" if first.suit == second.suit else "o"
    return f"{first_rank}{second_rank}{suffix}"


def compact_code(value: PokerCard) -> str:
    rank = "T" if value.rank == "10" else value.rank
    return rank + SUIT_CODES[value.suit]


def _variants(notation: str) -> list[tuple[str, str]]:
    first, second = notation[0], notation[1]
    if first == second:
        return [(first + suit_a, second + suit_b) for index, suit_a in enumerate(SUITS) for suit_b in SUITS[index + 1 :]]
    if notation.endswith("s"):
        return [(first + suit, second + suit) for suit in SUITS]
    return [(first + suit_a, second + suit_b) for suit_a in SUITS for suit_b in SUITS if suit_a != suit_b]


def deal_ranged_hand(position: str, rng: random.Random, excluded: set[str] | None = None) -> list[PokerCard]:
    blocked = excluded or set()
    notations = list(POSITION_RANGES[position])
    rng.shuffle(notations)
    for notation in notations:
        variants = _variants(notation)
        rng.shuffle(variants)
        for first, second in variants:
            if first not in blocked and second not in blocked:
                return [card(first), card(second)]
    raise RuntimeError(f"No available hand for {position}")


def deal_matchup(rng: random.Random, matchup: tuple[str, str] | None = None):
    hero_position, villain_position = matchup or rng.choice(MATCHUPS)
    hero = deal_ranged_hand(hero_position, rng)
    used = {compact_code(item) for item in hero}
    villain = deal_ranged_hand(villain_position, rng, used)
    return hero_position, villain_position, hero, villain


def is_in_position_range(position: str, cards: list[PokerCard]) -> bool:
    return combo_notation(cards) in POSITION_RANGES[position]
