import unittest

from casino_coach.game import Card, Hand
from casino_coach.strategy import recommend


def hand(*ranks):
    return Hand([Card(rank, "♠") for rank in ranks])


def dealer(rank):
    return Card(rank, "♣")


class StrategyTests(unittest.TestCase):
    def test_hard_16_stands_against_six(self):
        self.assertEqual(recommend(hand("10", "6"), dealer("6")).action, "stand")

    def test_hard_16_hits_against_ten(self):
        self.assertEqual(recommend(hand("10", "6"), dealer("10")).action, "hit")

    def test_hard_11_doubles_against_ten(self):
        self.assertEqual(recommend(hand("6", "5"), dealer("10")).action, "double")

    def test_double_falls_back_to_hit(self):
        self.assertEqual(recommend(hand("6", "3", "2"), dealer("6"), can_double=False).action, "hit")

    def test_soft_18_doubles_against_six(self):
        self.assertEqual(recommend(hand("A", "7"), dealer("6")).action, "double")

    def test_soft_18_stands_against_eight(self):
        self.assertEqual(recommend(hand("A", "7"), dealer("8")).action, "stand")

    def test_soft_18_hits_against_ten(self):
        self.assertEqual(recommend(hand("A", "7"), dealer("10")).action, "hit")

    def test_multiple_aces_can_still_be_soft(self):
        cards = hand("A", "A", "6")
        self.assertEqual(cards.total, 18)
        self.assertTrue(cards.is_soft)


if __name__ == "__main__":
    unittest.main()
