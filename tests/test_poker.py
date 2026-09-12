import unittest

from casino_coach.poker import card, compare, evaluate


class PokerTests(unittest.TestCase):
    def test_straight_flush_beats_quads(self):
        straight_flush = [card(code) for code in ("9s", "Ts", "Js", "Qs", "Ks")]
        quads = [card(code) for code in ("Ah", "Ad", "Ac", "As", "2d")]
        self.assertGreater(evaluate(straight_flush)[0], evaluate(quads)[0])

    def test_wheel_is_a_straight(self):
        cards = [card(code) for code in ("As", "2h", "3d", "4c", "5s")]
        self.assertEqual(evaluate(cards)[1], "Стрит")

    def test_best_five_from_seven(self):
        cards = [card(code) for code in ("Ah", "Ad", "Ac", "Ks", "Kd", "2s", "3h")]
        self.assertEqual(evaluate(cards)[1], "Фулл-хаус")

    def test_compare_uses_board(self):
        hero = [card("As"), card("Ah")]
        villain = [card("Ks"), card("Kh")]
        board = [card(code) for code in ("2c", "7d", "9h", "Js", "3c")]
        result, _, _ = compare(hero, villain, board)
        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
