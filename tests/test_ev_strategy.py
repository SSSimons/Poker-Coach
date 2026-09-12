import random
import unittest

from casino_coach.ev_strategy import (
    acts_first_postflop,
    bot_facing_decision,
    bot_open_decision,
    estimate_equity_vs_range,
)
from casino_coach.poker import card


class EvStrategyTests(unittest.TestCase):
    def test_postflop_order_uses_position_not_deal_order(self):
        self.assertTrue(acts_first_postflop("BB", "BTN"))
        self.assertTrue(acts_first_postflop("HJ", "CO"))
        self.assertFalse(acts_first_postflop("BTN", "BB"))

    def test_equity_is_range_based_and_deterministic(self):
        hole = [card("As"), card("Ah")]
        board = [card("Ad"), card("7c"), card("2s")]
        first = estimate_equity_vs_range(hole, board, "BTN", random.Random(19), samples=80)
        second = estimate_equity_vs_range(hole, board, "BTN", random.Random(19), samples=80)
        self.assertEqual(first, second)
        self.assertGreater(first, 0.85)

    def test_opening_actions_match_named_leaks(self):
        self.assertEqual(bot_open_decision("philip", 0, 0.72)[0], "check")
        self.assertEqual(bot_open_decision("timofey", 1, 0.60)[0], "bet")
        self.assertEqual(bot_open_decision("lena", 1, 0.60)[0], "check")

    def test_facing_bet_uses_equity_and_pot_odds(self):
        self.assertEqual(bot_facing_decision("philip", 1, 0.55, 50, 150, can_raise=True), "fold")
        self.assertEqual(bot_facing_decision("timofey", 1, 0.56, 50, 150, can_raise=True), "call")
        self.assertEqual(bot_facing_decision("lena", 0, 0.45, 30, 130, can_raise=True), "call")
        self.assertEqual(bot_facing_decision("timofey", 0, 0.45, 50, 150, can_raise=True), "fold")

    def test_only_strong_value_can_raise(self):
        self.assertEqual(bot_facing_decision("timofey", 2, 0.85, 50, 150, can_raise=True), "raise")
        self.assertEqual(bot_facing_decision("timofey", 2, 0.85, 50, 150, can_raise=False), "call")

    def test_all_responses_are_legal(self):
        for profile in ("philip", "timofey", "lena"):
            for category in range(9):
                for equity in (0.05, 0.35, 0.55, 0.75, 0.95):
                    response = bot_facing_decision(profile, category, equity, 40, 140, can_raise=True)
                    self.assertIn(response, {"fold", "call", "raise"})


if __name__ == "__main__":
    unittest.main()
