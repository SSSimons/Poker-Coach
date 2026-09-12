"""Small non-interactive UI smoke test for the prepared Kivy environment."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import BLITZ_TASKS, INTRO_CHAPTERS, CasinoCoachApp
from casino_coach.poker import card


app = CasinoCoachApp()
root = app.build()
assert root is not None
assert app.manager.current in ("intro", "home")

app.intro_chapter = 0
app.onboarding_complete = False
app.show_intro()
for chapter in range(5):
    assert app.intro_chapter == chapter
    questions = INTRO_CHAPTERS[chapter]["questions"]
    for question in questions:
        app._answer_intro(question[4])
        app._next_intro_question()
assert app.onboarding_complete

app.premium = True
app.show_home()

app.start_blitz()
assert app.manager.current == "blitz"
preflop_labels = [button.text for button in app.blitz_actions.children]
assert len(preflop_labels) == 3
assert set(preflop_labels) == {"CALL", "OPEN-RAISE", "FOLD"}
assert all("POT" not in text and "%" not in text and "BB" not in text for text in preflop_labels)
app.answer_blitz("big")
assert "Ваш выбор: OPEN-RAISE" in app.blitz_note.text
app.blitz_index = 2
app._load_blitz_task()
postflop_labels = [button.text for button in app.blitz_actions.children]
assert len(postflop_labels) == 4
assert any("33% POT" in text for text in postflop_labels)
app.blitz_index = 3
app._load_blitz_task()
facing_bet_labels = [button.text for button in app.blitz_actions.children]
assert len(facing_bet_labels) == 4
assert set(facing_bet_labels) == {"FOLD", "CALL", "SMALL RAISE", "BIG RAISE"}
app.answer_blitz("small")
assert "ЛУЧШИЙ ОТВЕТ" in app.blitz_verdict.text
assert "Ваш выбор: CALL" in app.blitz_note.text
for scenario in BLITZ_TASKS:
    app._configure_blitz_actions(scenario)
    available_actions = set(app.blitz_display_labels)
    assert scenario["best"] in available_actions
    assert scenario["normal"] is None or scenario["normal"] in available_actions

app.start_ev_battle()
assert app.manager.current == "ev_battle"
assert len({str(item) for item in app.ev_hero + app.ev_bot_cards}) == 4
assert len(app.ev_history) >= 2
position_order = {"UTG": 0, "HJ": 1, "CO": 2, "BTN": 3, "SB": 4, "BB": 5}
expected_opener = "YOU" if position_order[app.ev_hero_position] < position_order[app.ev_bot_position] else app.ev_bot_position
assert app.ev_history[0][1] == expected_opener
for bot_key in ("philip", "timofey", "lena"):
    app.start_ev_battle(bot_key)
    steps = 0
    while not app.ev_finished:
        assert app.ev_pot + app.ev_stack + app.ev_bot_stack == 1900
        if app.ev_facing_bet:
            assert app.ev_check.text.startswith("CALL ")
            assert not app.ev_fold.disabled
            app.ev_action("call")
        else:
            assert app.ev_check.text == "CHECK"
            assert app.ev_fold.disabled
            app.ev_action("check")
        steps += 1
        assert steps <= 8
    assert app.ev_board_count == 5 or any(event[2] == "FOLD" for event in app.ev_history)
    assert app.ev_pot + app.ev_stack + app.ev_bot_stack == 1900

# Force a strong in-position bot to verify BET -> RAISE -> CALL accounting.
app.start_ev_battle("timofey")
app.ev_hero_position, app.ev_bot_position = "HJ", "CO"
app.ev_hero = [card("Kc"), card("Qc")]
app.ev_bot_cards = [card("As"), card("Ah")]
app.ev_board_full = [card(code) for code in ("Ad", "7c", "2s", "3d", "4h")]
app.ev_board_count = 3
app.ev_pot, app.ev_stack, app.ev_bot_stack = 100, 900, 900
app._begin_ev_street("Forced state-machine check.")
app.ev_slider.value = 50
app.ev_action("bet")
assert app.ev_facing_bet == 50
assert app.ev_bet.text == "RE-RAISE"
assert app.ev_history[-1][2] == "RAISE TO"
assert app.ev_pot + app.ev_stack + app.ev_bot_stack == 1900
app.ev_action("call")
assert app.ev_board_count == 4
assert app.ev_pot + app.ev_stack + app.ev_bot_stack == 1900

app.show_fanchip_lobby()
assert app.manager.current == "fanchip_lobby"
app.start_fanchip_hand()
assert app.manager.current == "fanchip_table"
app.fanchip_action("check")

print("UI smoke test passed")
