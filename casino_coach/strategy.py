from __future__ import annotations

from dataclasses import dataclass

from .game import Card, Hand


@dataclass(frozen=True)
class Advice:
    action: str
    explanation: str


def _dealer_value(card: Card) -> int:
    return 11 if card.rank == "A" else min(card.value, 10)


def recommend(hand: Hand, dealer_upcard: Card, can_double: bool = True) -> Advice:
    """Basic strategy for a simplified multi-deck S17 game without splits."""
    total = hand.total
    dealer = _dealer_value(dealer_upcard)

    if hand.is_soft and total <= 21:
        if total <= 14:
            return _double_or_hit(can_double, dealer in (5, 6), "Мягкие 13–14 удваивают против слабых 5–6, иначе добирают.")
        if total in (15, 16):
            return _double_or_hit(can_double, dealer in (4, 5, 6), "Мягкие 15–16 удваивают против 4–6, иначе добирают.")
        if total == 17:
            return _double_or_hit(can_double, dealer in (3, 4, 5, 6), "Мягкие 17 удваивают против 3–6, иначе добирают.")
        if total == 18:
            if can_double and dealer in (3, 4, 5, 6):
                return Advice("double", "Мягкие 18 выгодно удвоить против слабых 3–6.")
            if dealer in (2, 3, 4, 5, 6, 7, 8):
                return Advice("stand", "Мягкие 18 достаточно сильны против этой открытой карты дилера.")
            return Advice("hit", "Против 9, 10 или туза мягкие 18 слишком слабы — нужен добор.")
        return Advice("stand", "Мягкие 19 и выше — сильная рука, добор не нужен.")

    if total <= 8:
        return Advice("hit", "С 8 или меньше перебор невозможен — следует добирать.")
    if total == 9:
        return _double_or_hit(can_double, dealer in (3, 4, 5, 6), "Девятку удваивают против слабых 3–6, иначе добирают.")
    if total == 10:
        return _double_or_hit(can_double, 2 <= dealer <= 9, "Десятку удваивают против 2–9, но не против 10 или туза.")
    if total == 11:
        return _double_or_hit(can_double, 2 <= dealer <= 10, "Одиннадцать удваивают против 2–10; против туза безопаснее добрать.")
    if total == 12:
        if dealer in (4, 5, 6):
            return Advice("stand", "Против 4–6 у дилера высок риск перебора, поэтому на 12 стоят.")
        return Advice("hit", "Против сильной или нейтральной карты дилера 12 требует добора.")
    if 13 <= total <= 16:
        if 2 <= dealer <= 6:
            return Advice("stand", "Против 2–6 дилер часто перебирает, поэтому сохраняем готовую руку.")
        return Advice("hit", "Против 7–туза сумма 13–16 обычно проигрывает без добора.")
    return Advice("stand", "С 17 и выше по базовой стратегии следует остановиться.")


def _double_or_hit(can_double: bool, should_double: bool, explanation: str) -> Advice:
    if should_double and can_double:
        return Advice("double", explanation)
    return Advice("hit", explanation if should_double else explanation)
