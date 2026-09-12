import random
import unittest

from casino_coach.ranges import MATCHUPS, compact_code, deal_matchup, is_in_position_range


class RangeTests(unittest.TestCase):
    def test_matchups_deal_valid_non_overlapping_hands(self):
        rng = random.Random(42)
        for matchup in MATCHUPS:
            for _ in range(30):
                hero_position, villain_position, hero, villain = deal_matchup(rng, matchup)
                self.assertTrue(is_in_position_range(hero_position, hero))
                self.assertTrue(is_in_position_range(villain_position, villain))
                self.assertEqual(len({compact_code(item) for item in hero + villain}), 4)

    def test_trash_hands_are_not_dealt(self):
        rng = random.Random(7)
        dealt = []
        for _ in range(250):
            _, _, hero, villain = deal_matchup(rng)
            dealt.extend((hero, villain))
        notations = {"".join(item.rank for item in hand) for hand in dealt}
        self.assertNotIn("42", notations)
        self.assertNotIn("57", notations)


if __name__ == "__main__":
    unittest.main()
