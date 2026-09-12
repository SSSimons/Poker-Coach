import unittest

from casino_coach.game import BlackjackGame, Card


class FixedShoe:
    def __init__(self, draw_order):
        self.cards = list(reversed(draw_order))

    def draw(self):
        return self.cards.pop()


def card(rank):
    return Card(rank, "♠")


class GameTests(unittest.TestCase):
    def test_player_busts_on_hit(self):
        shoe = FixedShoe([card("10"), card("6"), card("9"), card("7"), card("K")])
        game = BlackjackGame(shoe)
        game.start_round()
        game.hit()
        self.assertTrue(game.finished)
        self.assertEqual(game.result, "loss")

    def test_dealer_draws_and_busts(self):
        shoe = FixedShoe([card("10"), card("8"), card("6"), card("10"), card("K")])
        game = BlackjackGame(shoe)
        game.start_round()
        game.stand()
        self.assertEqual(game.result, "win")

    def test_blackjack_is_resolved_immediately(self):
        shoe = FixedShoe([card("A"), card("K"), card("9"), card("7")])
        game = BlackjackGame(shoe)
        game.start_round()
        self.assertTrue(game.finished)
        self.assertEqual(game.result, "blackjack")

    def test_double_draws_one_card(self):
        shoe = FixedShoe([card("6"), card("5"), card("9"), card("7"), card("10"), card("8")])
        game = BlackjackGame(shoe)
        game.start_round()
        game.double()
        self.assertTrue(game.finished)
        self.assertTrue(game.doubled)
        self.assertEqual(len(game.player.cards), 3)


if __name__ == "__main__":
    unittest.main()
