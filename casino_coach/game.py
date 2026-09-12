from __future__ import annotations

import random
from dataclasses import dataclass


SUITS = ("♠", "♥", "♦", "♣")
RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    @property
    def value(self) -> int:
        if self.rank == "A":
            return 11
        if self.rank in ("J", "Q", "K"):
            return 10
        return int(self.rank)

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


class Shoe:
    def __init__(self, decks: int = 6, rng: random.Random | None = None):
        self.decks = decks
        self.rng = rng or random.Random()
        self.cards: list[Card] = []
        self.reset()

    def reset(self):
        self.cards = [Card(rank, suit) for _ in range(self.decks) for suit in SUITS for rank in RANKS]
        self.rng.shuffle(self.cards)

    def draw(self) -> Card:
        if len(self.cards) < 52:
            self.reset()
        return self.cards.pop()


class Hand:
    def __init__(self, cards: list[Card] | None = None):
        self.cards = list(cards or [])

    def add(self, card: Card):
        self.cards.append(card)

    @property
    def total(self) -> int:
        total = sum(card.value for card in self.cards)
        aces = sum(card.rank == "A" for card in self.cards)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    @property
    def is_soft(self) -> bool:
        raw = sum(card.value for card in self.cards)
        aces = sum(card.rank == "A" for card in self.cards)
        reduced_aces = (raw - self.total) // 10
        return aces > reduced_aces

    @property
    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.total == 21

    @property
    def is_bust(self) -> bool:
        return self.total > 21


class BlackjackGame:
    def __init__(self, shoe: Shoe | None = None):
        self.shoe = shoe or Shoe()
        self.player = Hand()
        self.dealer = Hand()
        self.finished = True
        self.result = ""
        self.result_text = ""
        self.doubled = False

    def start_round(self):
        self.player = Hand([self.shoe.draw(), self.shoe.draw()])
        self.dealer = Hand([self.shoe.draw(), self.shoe.draw()])
        self.finished = False
        self.result = ""
        self.result_text = ""
        self.doubled = False
        if self.player.is_blackjack or self.dealer.is_blackjack:
            self._settle()

    @property
    def can_double(self) -> bool:
        return not self.finished and len(self.player.cards) == 2

    def hit(self):
        self._ensure_active()
        self.player.add(self.shoe.draw())
        if self.player.is_bust:
            self.finished = True
            self.result = "loss"
            self.result_text = "Перебор — раздача проиграна."
        elif self.player.total == 21:
            self.stand()

    def stand(self):
        self._ensure_active()
        while self.dealer.total < 17:
            self.dealer.add(self.shoe.draw())
        self._settle()

    def double(self):
        self._ensure_active()
        if not self.can_double:
            raise ValueError("Удвоение доступно только на первых двух картах")
        self.doubled = True
        self.player.add(self.shoe.draw())
        if self.player.is_bust:
            self.finished = True
            self.result = "loss"
            self.result_text = "После удвоения получен перебор."
        else:
            self.stand()

    def _settle(self):
        self.finished = True
        player_total = self.player.total
        dealer_total = self.dealer.total
        if self.player.is_blackjack and self.dealer.is_blackjack:
            self.result, self.result_text = "push", "Оба получили блэкджек — ничья."
        elif self.player.is_blackjack:
            self.result, self.result_text = "blackjack", "Блэкджек — победа!"
        elif self.dealer.is_blackjack:
            self.result, self.result_text = "loss", "У дилера блэкджек."
        elif self.player.is_bust:
            self.result, self.result_text = "loss", "Перебор — раздача проиграна."
        elif self.dealer.is_bust:
            self.result, self.result_text = "win", "У дилера перебор — победа!"
        elif player_total > dealer_total:
            self.result, self.result_text = "win", f"{player_total} против {dealer_total} — победа!"
        elif player_total < dealer_total:
            self.result, self.result_text = "loss", f"{player_total} против {dealer_total} — поражение."
        else:
            self.result, self.result_text = "push", f"По {player_total} — ничья."

    def player_text(self) -> str:
        # Suits do not affect blackjack strategy, and Kivy's bundled Android
        # font does not consistently contain the four suit glyphs.
        return "   ".join(card.rank for card in self.player.cards)

    def dealer_text(self, reveal: bool) -> str:
        if reveal:
            ranks = "   ".join(card.rank for card in self.dealer.cards)
            return ranks + f"   ({self.dealer.total})"
        return f"{self.dealer.cards[0].rank}   [?]"

    def snapshot(self) -> dict:
        return {
            "player_cards": [str(card) for card in self.player.cards],
            "player_total": self.player.total,
            "soft": self.player.is_soft,
            "dealer_upcard": str(self.dealer.cards[0]),
            "rules": "6 decks, dealer stands on soft 17, no split/surrender/insurance",
        }

    def _ensure_active(self):
        if self.finished:
            raise RuntimeError("Раздача уже завершена")
