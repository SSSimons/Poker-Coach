from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from itertools import combinations


SUITS = ("♠", "♥", "♦", "♣")
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
RANK_VALUE = {rank: value for value, rank in enumerate(RANKS, start=2)}
HAND_NAMES = (
    "Старшая карта",
    "Пара",
    "Две пары",
    "Тройка",
    "Стрит",
    "Флеш",
    "Фулл-хаус",
    "Каре",
    "Стрит-флеш",
)


@dataclass(frozen=True)
class PokerCard:
    rank: str
    suit: str

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


def card(code: str) -> PokerCard:
    """Parse compact cards such as As, Th, 7d or Qc."""
    suit_map = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
    rank = code[:-1].upper().replace("T", "10")
    return PokerCard(rank, suit_map[code[-1].lower()])


def fresh_deck(rng: random.Random | None = None) -> list[PokerCard]:
    deck = [PokerCard(rank, suit) for suit in SUITS for rank in RANKS]
    (rng or random).shuffle(deck)
    return deck


def evaluate(cards: list[PokerCard]) -> tuple[tuple[int, ...], str]:
    if len(cards) < 5:
        return _partial_score(cards)
    score = max(_score_five(list(group)) for group in combinations(cards, 5))
    return score, HAND_NAMES[score[0]]


def _score_five(cards: list[PokerCard]) -> tuple[int, ...]:
    values = sorted((RANK_VALUE[item.rank] for item in cards), reverse=True)
    counts = Counter(values)
    grouped = sorted(((count, value) for value, count in counts.items()), reverse=True)
    flush = len({item.suit for item in cards}) == 1
    unique = sorted(set(values), reverse=True)
    if 14 in unique:
        unique.append(1)
    straight_high = 0
    for index in range(len(unique) - 4):
        window = unique[index:index + 5]
        if window[0] - window[4] == 4:
            straight_high = window[0]
            break

    if flush and straight_high:
        return (8, straight_high)
    if grouped[0][0] == 4:
        quad = grouped[0][1]
        kicker = max(value for value in values if value != quad)
        return (7, quad, kicker)
    trips = sorted((value for value, count in counts.items() if count == 3), reverse=True)
    pairs = sorted((value for value, count in counts.items() if count >= 2), reverse=True)
    if trips:
        pair_candidates = [value for value in pairs if value != trips[0]]
        if len(trips) > 1:
            pair_candidates.append(trips[1])
        if pair_candidates:
            return (6, trips[0], max(pair_candidates))
    if flush:
        return (5, *values)
    if straight_high:
        return (4, straight_high)
    if trips:
        kickers = [value for value in values if value != trips[0]][:2]
        return (3, trips[0], *kickers)
    pair_values = sorted((value for value, count in counts.items() if count == 2), reverse=True)
    if len(pair_values) >= 2:
        high, low = pair_values[:2]
        kicker = max(value for value in values if value not in (high, low))
        return (2, high, low, kicker)
    if pair_values:
        pair = pair_values[0]
        kickers = [value for value in values if value != pair][:3]
        return (1, pair, *kickers)
    return (0, *values)


def _partial_score(cards: list[PokerCard]) -> tuple[tuple[int, ...], str]:
    values = sorted((RANK_VALUE[item.rank] for item in cards), reverse=True)
    counts = Counter(values)
    grouped = sorted(((count, value) for value, count in counts.items()), reverse=True)
    if grouped and grouped[0][0] >= 4:
        return (7, grouped[0][1]), "Каре"
    if grouped and grouped[0][0] == 3:
        return (3, grouped[0][1]), "Тройка"
    pairs = sorted((value for value, count in counts.items() if count == 2), reverse=True)
    if len(pairs) >= 2:
        return (2, pairs[0], pairs[1]), "Две пары"
    if pairs:
        return (1, pairs[0]), "Пара"
    return (0, *values), "Пока без готовой комбинации"


def compare(hero: list[PokerCard], villain: list[PokerCard], board: list[PokerCard]) -> tuple[int, str, str]:
    hero_score, hero_name = evaluate(hero + board)
    villain_score, villain_name = evaluate(villain + board)
    return (1 if hero_score > villain_score else -1 if hero_score < villain_score else 0), hero_name, villain_name
