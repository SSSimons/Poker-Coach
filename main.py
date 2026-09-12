from __future__ import annotations

import random
import threading
from os.path import dirname, join

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import ListProperty
from kivy.storage.jsonstore import JsonStore
from kivy.utils import platform
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.textinput import TextInput

from casino_coach.ai import AIExplainer
from casino_coach.ev_strategy import (
    acts_first_postflop,
    bot_facing_decision,
    bot_open_decision,
    estimate_equity_vs_range,
    made_category,
)
from casino_coach.poker import PokerCard, card, compare, evaluate, fresh_deck
from casino_coach.ranges import compact_code, deal_matchup


BG = (0.025, 0.055, 0.065, 1)
PANEL = (0.055, 0.13, 0.15, 1)
PANEL_LIGHT = (0.08, 0.19, 0.20, 1)
FELT = (0.02, 0.23, 0.15, 1)
GREEN = (0.12, 0.88, 0.55, 1)
YELLOW = (1.0, 0.72, 0.18, 1)
RED = (1.0, 0.31, 0.31, 1)
MUTED = (0.63, 0.73, 0.73, 1)
WHITE = (0.96, 0.98, 0.97, 1)
CARD_RED = (0.82, 0.12, 0.15, 1)
CARD_BLACK = (0.06, 0.08, 0.10, 1)
CARD_FONT = join(dirname(__file__), "assets", "DejaVuSans.ttf")

ACTION_LABELS = {
    "check_fold": "CHECK / FOLD",
    "small": "BET 33%",
    "big": "BET 75%",
    "check": "CHECK",
    "bet_small": "BET 33%",
    "bet_big": "BET 75%",
    "overbet": "OVERBET 125%",
    "fold": "FOLD",
    "call": "CALL",
    "raise": "RAISE",
    "raise_small": "SMALL RAISE",
    "raise_big": "BIG RAISE",
    "overraise": "OVER-RAISE",
}

STREET_LABELS = {"ПРЕФЛОП": "PREFLOP", "ФЛОП": "FLOP", "ТЁРН": "TURN", "РИВЕР": "RIVER"}
HAND_NAME_EN = {
    "Старшая карта": "High Card",
    "Пара": "One Pair",
    "Две пары": "Two Pair",
    "Тройка": "Three of a Kind",
    "Стрит": "Straight",
    "Флеш": "Flush",
    "Фулл-хаус": "Full House",
    "Каре": "Four of a Kind",
    "Стрит-флеш": "Straight Flush",
}


def english_hand_name(value):
    return HAND_NAME_EN.get(value, value)


INTRO_CHAPTERS = (
    {
        "title": "1.1  FIND THE NUTS",
        "lesson": "Пять общих карт уже лежат на столе. Выбери самую сильную готовую комбинацию на board.",
        "questions": (
            (("As", "Ac", "Ad", "Ah", "Kd"), (), "Что уже собрано на board?", ("Full House", "Four of a Kind", "Flush", "Straight"), "Four of a Kind", "Четыре туза — Four of a Kind. Сильнее только Straight Flush."),
            (("Kh", "Kd", "Kc", "2s", "2d"), (), "Назови лучшую комбинацию.", ("Three of a Kind", "Two Pair", "Full House", "Four of a Kind"), "Full House", "Тройка королей + пара двоек = Full House."),
            (("Ah", "Jh", "8h", "4h", "2h"), (), "Какая комбинация здесь готова?", ("Straight", "Flush", "Full House", "Two Pair"), "Flush", "Пять червей без порядка — Flush."),
            (("9s", "8d", "7c", "6h", "5s"), (), "Что дают пять рангов подряд?", ("Straight", "Flush", "Two Pair", "Full House"), "Straight", "9‑8‑7‑6‑5 подряд — Straight."),
            (("Qs", "Qd", "7c", "7d", "2h"), (), "На board две пары. Как это называется?", ("One Pair", "Two Pair", "Trips", "Full House"), "Two Pair", "QQ + 77 — Two Pair; двойка только kicker."),
        ),
    },
    {
        "title": "1.2  POSITION",
        "lesson": "Позиция определяет порядок действий. UTG открывает preflop, BTN чаще играет последним postflop, SB почти всегда без позиции.",
        "questions": (
            ((), (), "Кто говорит первым preflop за 6-max столом?", ("UTG", "HJ", "BTN", "BB"), "UTG", "UTG первым принимает добровольное preflop-решение."),
            ((), (), "Кто первым действует postflop, если оба blind в раздаче?", ("BTN", "CO", "BB", "SB"), "SB", "SB находится слева от dealer и действует первым postflop."),
            ((), (), "Какая позиция обычно самая выигрышная?", ("UTG", "SB", "BTN", "BB"), "BTN", "BTN чаще видит чужое действие до своего — это огромное преимущество."),
            ((), (), "Какая позиция требует больше всего осторожности postflop?", ("BTN", "CO", "HJ", "SB"), "SB", "SB чаще играет без позиции, поэтому диапазон и pot нужно контролировать тщательнее."),
        ),
    },
    {
        "title": "1.3  OPEN-RAISE",
        "lesson": "Open-raise — первый добровольный raise preflop. Базовый sizing для тренажёра: 2.5 BB. Чем позже позиция, тем шире range.",
        "questions": (
            ((), (), "Что значит open-raise?", ("Первый raise preflop", "Любой call", "Bet на river", "Второй raise"), "Первый raise preflop", "Open-raise — первый raise после blind, когда до вас никто не вошёл в pot."),
            ((), (), "Какой базовый open sizing используем?", ("1 BB", "2.5 BB", "6 BB", "All-in"), "2.5 BB", "2.5 BB создаёт давление, но не рискует слишком многим со всем range."),
            ((), ("7h", "6h"), "Где 7♥6♥ нормально открывать в базовой стратегии?", ("UTG", "BTN", "Любая", "Нигде"), "BTN", "BTN даёт позицию и больше fold equity для suited connector."),
            ((), ("7h", "6h"), "Где новичку лучше не open-raise 7♥6♥?", ("BTN", "CO", "UTG", "BB vs limp"), "UTG", "UTG range сильнее: 7♥6♥ здесь чаще лишняя головная боль."),
        ),
    },
    {
        "title": "1.4  NO LIMPING",
        "lesson": "OPEN-LIMP В БАЗОВОЙ ПРОГРАММЕ НЕ ИСПОЛЬЗУЕМ. Он оставляет инициативу другим. Dead money — фишки в pot, которые можно забрать isolation raise. Формула: 2.5 BB + 1 BB за каждого limper.",
        "questions": (
            ((), (), "Перед вами все fold. С играемой рукой начинаем как?", ("Open-limp", "Open-raise", "Check", "Fold always"), "Open-raise", "Raise забирает инициативу; open-limp её добровольно отдаёт."),
            ((), (), "Что такое dead money?", ("Чужие фишки уже в pot", "Фишки из кассы", "Только rake", "Выигрыш на river"), "Чужие фишки уже в pot", "Blind и limp уже лежат в pot и делают isolation raise выгоднее."),
            ((), ("As", "Qd"), "Вы BTN, перед вами 4 limper. Какой raise по формуле 2.5 + 1 за limper?", ("2.5 BB", "4 BB", "6.5 BB", "12 BB"), "6.5 BB", "2.5 + 4 × 1 = 6.5 BB. Наказываем limper и собираем dead money."),
        ),
    },
    {
        "title": "1.5  POSTFLOP ACTIONS",
        "lesson": "Postflop базовые действия — CHECK, BET, CALL, RAISE и FOLD. Смотрим на силу руки, board, range и sizing, а не на красоту кнопки.",
        "questions": (
            ((), (), "До вас check, у вас сильная рука и много хуже могут заплатить.", ("BET", "CHECK", "FOLD", "CALL"), "BET", "BET строит pot и добирает value."),
            ((), (), "До вас check, у вас слабое showdown value и нет причины раздувать pot.", ("CHECK", "BET", "RAISE", "CALL"), "CHECK", "CHECK берёт бесплатную карту или дешёвый showdown."),
            ((), (), "Против вас huge BET, рука слабая, outs почти нет.", ("FOLD", "CALL", "RAISE", "BET"), "FOLD", "FOLD — не слабость, а отказ платить плохую цену."),
            ((), (), "Оппонент ставит мало, у вас очень сильная рука и нужно строить pot.", ("RAISE", "FOLD", "CHECK", "CALL only"), "RAISE", "RAISE добирает value и не даёт слишком дешёво увидеть следующую карту."),
            ((), (), "Вам дают хорошую цену, у руки много outs, но raise выбьет всё хуже.", ("CALL", "FOLD", "OVERBET", "CHECK"), "CALL", "CALL оставляет в pot худшие руки и покупает ваши outs по хорошей цене."),
        ),
    },
)


def task(street, position, hero, board, history, pot, stack, best, normal, note):
    return {
        "street": street,
        "position": position,
        "hero": tuple(hero),
        "board": tuple(board),
        "history": tuple(history),
        "pot": pot,
        "stack": stack,
        "best": best,
        "normal": normal,
        "note": note,
    }


BLITZ_TASKS = (
    task("ПРЕФЛОП", "BTN", ("As", "Kd"), (), ("UTG fold", "CO fold"), 1.5, 100, "raise", None, "На BTN AKo после fold — OPEN-RAISE. CALL здесь был бы запрещённым open-limp, а FOLD слишком тайтовый. Один sizing выбирают для всего range, а не отдельно под конкретную руку."),
    task("ПРЕФЛОП", "BB", ("7s", "6s"), (), ("BTN raise 2.5 BB", "SB fold"), 4, 100, "call", "raise", "Suited connector хорошо защищает BB против широкого BTN range. CALL — базовая линия, а 3-BET иногда может играться как полублеф."),
    task("ФЛОП", "CO", ("Ah", "Qh"), ("Ad", "7c", "2s"), ("Вы рейз 2.5 BB", "BB колл", "BB чек"), 6, 97, "bet_small", "bet_big", "Топ-пара на сухом борде не нуждается в защите крупным сайзингом. Малый BET получает оплату от худших тузов и карманных пар."),
    task("ФЛОП", "BB", ("9h", "8h"), ("Jh", "7c", "2h"), ("CO рейз", "Вы колл", "Вы чек", "CO бет 33%"), 9, 96, "call", "raise_small", "Гатшот плюс flush draw хорошо реализует equity через CALL. RAISE остаётся агрессивной альтернативой, но раздувать pot здесь необязательно."),
    task("ФЛОП", "BTN", ("Ks", "Qc"), ("8h", "7h", "6d"), ("Вы рейз", "BB колл", "BB чек"), 6, 98, "check", "bet_small", "Доска лучше попадает в диапазон большого блайнда. CHECK — лучший контроль банка; маленький BET допустим только как частый диапазонный бет."),
    task("ТЁРН", "SB", ("Ac", "Jc"), ("As", "8d", "4c", "2c"), ("BTN рейз", "Вы колл", "Флоп чек-чек"), 7, 94, "bet_big", "bet_small", "Топ-пара плюс натсовое flush draw может ставить крупно на value и защиту. Малый BET не ошибка, но оставляет сопернику слишком выгодную цену."),
    task("ТЁРН", "BTN", ("Td", "9d"), ("Kd", "Qd", "3s", "2c"), ("Вы рейз", "BB колл", "Флоп: бет 33%, колл", "BB чек"), 15, 90, "check", "bet_small", "У дро примерно треть equity против диапазона продолжения, но это само по себе не оправдывает BET 75%. CHECK бесплатно реализует equity. Малый BET — допустимый semi-bluff только при read, что BB умеет выбрасывать пары."),
    task("ТЁРН", "BB", ("Qh", "Jh"), ("Qc", "9s", "5d", "9c"), ("BTN рейз", "Вы колл", "Флоп чек-чек"), 6, 97, "bet_small", "check", "После CHECK на flop у соперника много слабых рук. Небольшой BET добирает с карманных пар и защищает даму."),
    task("РИВЕР", "CO", ("As", "Ts"), ("Ks", "8s", "3c", "2d", "5s"), ("Вы рейз", "BB колл", "Флоп бет-колл", "Тёрн чек-чек", "BB чек"), 22, 82, "overbet", "bet_big", "Натсовый flush хочет максимум value. OVERBET хорошо поляризует range и наказывает flush хуже; большой BET тоже прибыльный."),
    task("РИВЕР", "BB", ("8c", "7c"), ("Ah", "Kd", "6s", "4d", "2c"), ("BTN рейз", "Вы колл", "Флоп чек-чек", "Тёрн чек-чек", "Вы чек", "BTN бет 75%"), 7, 96, "fold", "call", "У руки почти нет showdown value и мало подходящих блокеров. FOLD дисциплинированнее дорогого hero-call или случайного bluff-raise."),
    task("ПРЕФЛОП", "SB", ("Qs", "Qd"), (), ("CO raise 2.5 BB", "BTN fold"), 4, 100, "raise", "call", "QQ — premium hand вне позиции. 3-BET добирает value и ухудшает цену CALL; CALL допустим, но оставляет вас без инициативы."),
    task("ПРЕФЛОП", "CO", ("5h", "5c"), (), ("UTG raise 3 BB", "HJ call"), 7.5, 100, "fold", "raise", "Мелкая пара против сильного UTG range и CALL плохо реализует equity. FOLD — база; squeeze RAISE допустим редко."),
    task("ФЛОП", "BTN", ("Jc", "Tc"), ("Ac", "Kc", "4d"), ("CO рейз", "Вы колл", "CO чек"), 6, 97, "bet_big", "bet_small", "Натсовое комбо-дро может ставить крупно: есть fold equity, straight и flush outs. Малый BET тоже сохраняет инициативу."),
    task("ФЛОП", "UTG", ("Kh", "Ks"), ("Qh", "Jh", "9h"), ("Вы рейз", "BTN колл"), 7, 96, "check", "bet_small", "Монотонный связанный board опасен даже для overpair. CHECK контролирует pot; малый BET допустим с королём червей как blocker."),
    task("ФЛОП", "BB", ("6s", "6d"), ("6h", "Kc", "2d"), ("BTN рейз", "Вы колл", "Вы чек", "BTN бет 33%"), 9, 96, "raise_big", "call", "Set на сухом board хочет строить pot. BIG RAISE добирает с королей; CALL тоже сохраняет худшие руки в раздаче."),
    task("ТЁРН", "CO", ("Ah", "Kd"), ("Ac", "Qd", "7s", "Qs"), ("Вы рейз", "BB колл", "Флоп бет-колл", "BB чек"), 18, 88, "bet_small", "check", "Две пары на спаренном board остаются сильными, но крупный sizing выбивает хуже. Малый BET тонко добирает с тузов."),
    task("ТЁРН", "BTN", ("8s", "7s"), ("9c", "6d", "2h", "Kh"), ("CO рейз", "Вы колл", "CO бет 50%", "Вы колл", "CO чек"), 19, 86, "overbet", "bet_big", "Open-ended draw без showdown value хорошо превращается в полярный bluff. OVERBET давит на средние пары, большой BET тоже рабочий."),
    task("РИВЕР", "BTN", ("Qc", "Qd"), ("Qh", "Js", "7c", "3d", "2s"), ("Вы рейз", "BB колл", "Два барреля и два колла", "BB чек"), 42, 73, "overbet", "bet_big", "Top set почти всегда впереди calling range. OVERBET максимизирует value против двух пар и set хуже."),
    task("РИВЕР", "SB", ("Ah", "4h"), ("Kh", "9h", "3c", "7d", "2s"), ("BB чек", "Вы бет флоп", "BB колл", "Тёрн чек-чек", "BB чек"), 14, 90, "bet_big", "bet_small", "Промахнувшееся nut flush draw блокирует сильные flush и подходит для bluff. Большой BET лучше выбивает девятки и слабых королей."),
    task("РИВЕР", "BB", ("Kc", "Jc"), ("Ks", "Td", "8h", "4c", "Ac"), ("BTN рейз", "Вы колл", "Флоп чек-чек", "Тёрн бет-колл", "Вы чек", "BTN овербет"), 36, 76, "fold", "call", "После туза на river в полярном range соперника много сильных рук. Одна пара без ключевых blockers — спокойный FOLD; CALL допустим только с сильным read."),
)

BOT_PROFILES = {
    "philip": {
        "name": "Фолдёр Филипп",
        "tag": "OVERFOLD: пасует слишком часто",
        "intro": "Мой leak прямо в имени: давление терплю плохо.",
        "algorithm": "Сравнивает equity с pot odds, но требует большой запас и поэтому overfold. Сам ставит только две пары+ с уверенным value.",
        "color": (0.10, 0.48, 0.34, 1),
    },
    "timofey": {
        "name": "Тайтовый Тимофей",
        "tag": "Уважает сильные диапазоны",
        "intro": "Без руки я банк не подарю. С рукой — проверю тебя.",
        "algorithm": "Считает equity против range позиции. С парой продолжает только при достаточной цене, без made hand требует сильное draw.",
        "color": (0.20, 0.32, 0.55, 1),
    },
    "lena": {
        "name": "Лимпующая Лена",
        "tag": "Любит посмотреть следующую карту",
        "intro": "Я пришла за флопом. Попробуй теперь меня прогнать.",
        "algorithm": "Тоже учитывает pot odds, но задаёт слишком низкий порог CALL. Сама редко ставит и повышает только очень сильный value.",
        "color": (0.58, 0.27, 0.48, 1),
    },
}


class RoundedBox(BoxLayout):
    bg_color = ListProperty(PANEL)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._color = Color(rgba=self.bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])
        self.bind(pos=self._sync, size=self._sync, bg_color=self._sync_color)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _sync_color(self, *_):
        self._color.rgba = self.bg_color


class PlayingCard(BoxLayout):
    def __init__(self, value: PokerCard | None = None, hidden=False, small=False, **kwargs):
        width, height = ((dp(38), dp(54)) if small else (dp(46), dp(66)))
        super().__init__(orientation="vertical", size_hint=(None, None), size=(width, height), padding=dp(2), spacing=-dp(2), **kwargs)
        fill = (0.06, 0.34, 0.29, 1) if hidden else (0.97, 0.97, 0.94, 1)
        border = GREEN if hidden else (0.70, 0.73, 0.71, 1)
        with self.canvas.before:
            self._card_color = Color(rgba=fill)
            self._card_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(6)])
        with self.canvas.after:
            self._border_color = Color(rgba=border)
            self._border = Line(rounded_rectangle=(*self.pos, *self.size, dp(6)), width=1.0)
        self.bind(pos=self._sync_card, size=self._sync_card)
        if hidden:
            self.add_widget(Label(text="?", font_name=CARD_FONT, font_size=dp(23 if small else 28), color=WHITE))
        elif value:
            ink = CARD_RED if value.suit in ("♥", "♦") else CARD_BLACK
            self.add_widget(Label(text=value.rank, font_name=CARD_FONT, bold=True, font_size=dp(15 if small else 19), color=ink))
            self.add_widget(Label(text=value.suit, font_name=CARD_FONT, font_size=dp(17 if small else 21), color=ink))

    def _sync_card(self, *_):
        self._card_rect.pos = self.pos
        self._card_rect.size = self.size
        self._border.rounded_rectangle = (*self.pos, *self.size, dp(6))


def label(text="", size=15, color=WHITE, **kwargs):
    return Label(
        text=text,
        font_size=dp(size),
        color=color,
        halign=kwargs.pop("halign", "left"),
        valign=kwargs.pop("valign", "middle"),
        **kwargs,
    )


class CasinoCoachApp(App):
    title = "Casino Coach Poker"

    def build(self):
        Window.clearcolor = BG
        self.ai = AIExplainer()
        self.rng = random.Random()
        self.store = JsonStore(join(self.user_data_dir, "poker_progress.json"))
        self._load_progress()
        self._base_padding = dp(10)
        self._tts = None
        self.root_layout = BoxLayout(orientation="vertical", padding=[self._base_padding] * 4)
        self.manager = ScreenManager(transition=SlideTransition(duration=0.18))
        self.root_layout.add_widget(self.manager)
        if self.onboarding_complete:
            self.show_home(initial=True)
        else:
            self.show_intro(initial=True)
        Clock.schedule_once(self._read_android_insets, 0.3)
        Clock.schedule_once(self._read_android_insets, 1.0)
        Window.bind(size=lambda *_: Clock.schedule_once(self._read_android_insets, 0.1))
        return self.root_layout

    def _load_progress(self):
        if not self.store.exists("progress"):
            self.store.put(
                "progress",
                fanchips=0,
                free_runs=0,
                ai_uses=0,
                premium=False,
                onboarding_complete=False,
                intro_chapter=0,
                intro_rewarded=False,
            )
        data = self.store.get("progress")
        self.fanchips = int(data.get("fanchips", 1000))
        self.free_runs = int(data.get("free_runs", 0))
        self.ai_uses = int(data.get("ai_uses", 0))
        self.premium = bool(data.get("premium", False))
        self.onboarding_complete = bool(data.get("onboarding_complete", False))
        self.intro_chapter = min(4, int(data.get("intro_chapter", 0)))
        self.intro_rewarded = bool(data.get("intro_rewarded", False))

    def _save_progress(self):
        self.store.put(
            "progress",
            fanchips=self.fanchips,
            free_runs=self.free_runs,
            ai_uses=self.ai_uses,
            premium=self.premium,
            onboarding_complete=self.onboarding_complete,
            intro_chapter=self.intro_chapter,
            intro_rewarded=self.intro_rewarded,
        )

    def _set_screen(self, name, content, direction="left"):
        self.manager.transition.direction = direction
        if self.manager.has_screen(name):
            self.manager.remove_widget(self.manager.get_screen(name))
        screen = Screen(name=name)
        screen.add_widget(content)
        self.manager.add_widget(screen)
        self.manager.current = name

    def _page(self, title, back_callback=None):
        root = BoxLayout(orientation="vertical", spacing=dp(8))
        header = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(7))
        if back_callback:
            back = Button(text="НАЗАД", size_hint_x=None, width=dp(78), font_size=dp(12))
            back.bind(on_release=lambda *_: back_callback())
            header.add_widget(back)
        title_label = label(title, 19, GREEN, halign="center")
        title_label.bind(size=lambda widget, value: setattr(widget, "text_size", value))
        header.add_widget(title_label)
        wallet = label(f"ФАНТИКИ\n{self.fanchips}", 11, YELLOW, halign="center", size_hint_x=None, width=dp(82))
        header.add_widget(wallet)
        root.add_widget(header)
        body = BoxLayout(orientation="vertical", spacing=dp(8))
        root.add_widget(body)
        return root, body

    def show_home(self, initial=False):
        root = BoxLayout(orientation="vertical", spacing=dp(9))
        header = BoxLayout(size_hint_y=None, height=dp(68), spacing=dp(8))
        title_box = BoxLayout(orientation="vertical")
        title_box.add_widget(label("CASINO COACH", 22, GREEN))
        title_box.add_widget(label("Покерный тренажёр решений", 12, MUTED))
        header.add_widget(title_box)
        ai_button = Button(text="ИИ", size_hint_x=None, width=dp(58))
        ai_button.bind(on_release=self.open_ai_settings)
        guide_button = Button(text="СПРАВОЧНИК", size_hint_x=None, width=dp(104), font_size=dp(11))
        guide_button.bind(on_release=self.open_guide)
        header.add_widget(ai_button)
        header.add_widget(guide_button)
        root.add_widget(header)

        status = RoundedBox(size_hint_y=None, height=dp(52), padding=(dp(12), dp(5)), spacing=dp(8), bg_color=(0.05, 0.25, 0.18, 1))
        wallet = label(f"ФАНТИКИ  {self.fanchips}", 14, YELLOW)
        plan = Button(text="PREMIUM" if self.premium else "FREE-ПЛАН", size_hint_x=None, width=dp(104), font_size=dp(11))
        plan.bind(on_release=lambda *_: self.open_subscription())
        status.add_widget(wallet)
        status.add_widget(plan)
        root.add_widget(status)

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        modes = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=(0, dp(2)))
        modes.bind(minimum_height=modes.setter("height"))
        modes.add_widget(self._mode_card(
            "БЛИЦ-ЗАДАЧИ",
            "10 решений за ран • префлоп, флоп, тёрн и ривер\n2 бесплатных рана • идеальный ран даёт бонус",
            "ИГРАТЬ",
            GREEN,
            self.start_blitz,
        ))
        modes.add_widget(self._mode_card(
            "EV-БАТТЛ СОЛО",
            "Случайный соперник с видимым leak\nРеалистичные position ranges и action replay",
            "PLAY RANDOM HAND",
            YELLOW,
            self.start_ev_battle,
        ))
        modes.add_widget(self._mode_card(
            "ИГРА НА ФАНТИКИ",
            "Открытая Hold'em-песочница без Premium-локов\nПока локальный стол; online потребует backend",
            "JOIN SANDBOX",
            (0.40, 0.72, 1.0, 1),
            self.show_fanchip_lobby,
        ))
        scroll.add_widget(modes)
        root.add_widget(scroll)

        footer = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(7))
        ig = Button(text="ПОДПИШИСЬ IG", font_size=dp(11))
        yt = Button(text="ПОДПИШИСЬ YT", font_size=dp(11))
        ig.bind(on_release=lambda *_: self._open_social("Instagram"))
        yt.bind(on_release=lambda *_: self._open_social("YouTube"))
        footer.add_widget(ig)
        footer.add_widget(yt)
        root.add_widget(footer)
        self._set_screen("home", root, "right" if not initial else "left")

    def _mode_card(self, title, description, button_text, accent, callback):
        box = RoundedBox(orientation="vertical", size_hint_y=None, height=dp(145), padding=dp(13), spacing=dp(6))
        title_label = label(title, 18, accent, halign="center", size_hint_y=None, height=dp(28))
        title_label.bind(size=lambda widget, value: setattr(widget, "text_size", value))
        desc = label(description, 12, MUTED, halign="center", valign="middle")
        desc.bind(size=lambda widget, value: setattr(widget, "text_size", value))
        button = Button(text=button_text, size_hint_y=None, height=dp(40), background_color=accent)
        button.bind(on_release=lambda *_: callback())
        box.add_widget(title_label)
        box.add_widget(desc)
        box.add_widget(button)
        return box

    # ---------- First-launch intro ----------
    def show_intro(self, initial=False):
        self.intro_question_index = 0
        self.intro_correct = 0
        root = BoxLayout(orientation="vertical", spacing=dp(8))
        header = BoxLayout(size_hint_y=None, height=dp(64), spacing=dp(8))
        title_box = BoxLayout(orientation="vertical")
        title_box.add_widget(label("WELCOME TO THE TABLE", 20, GREEN))
        title_box.add_widget(label("Интро перед первой игрой", 11, MUTED))
        header.add_widget(title_box)
        self.intro_counter = label("", 11, YELLOW, halign="center", size_hint_x=None, width=dp(82))
        header.add_widget(self.intro_counter)
        root.add_widget(header)

        self.intro_chapter_title = label("", 18, GREEN, halign="center", size_hint_y=None, height=dp(34))
        root.add_widget(self.intro_chapter_title)
        lesson_box = RoundedBox(size_hint_y=None, height=dp(92), padding=dp(10))
        self.intro_lesson = label("", 11, WHITE, valign="middle")
        self.intro_lesson.bind(size=lambda widget, value: setattr(widget, "text_size", value))
        lesson_box.add_widget(self.intro_lesson)
        root.add_widget(lesson_box)

        visual_box = RoundedBox(orientation="vertical", size_hint_y=None, height=dp(190), padding=dp(8), spacing=dp(3), bg_color=FELT)
        self.intro_question = label("", 12, WHITE, halign="center", valign="middle", size_hint_y=None, height=dp(52))
        self.intro_question.bind(size=lambda widget, value: setattr(widget, "text_size", value))
        visual_box.add_widget(self.intro_question)
        self.intro_visual = BoxLayout(orientation="vertical", spacing=dp(4))
        visual_box.add_widget(self.intro_visual)
        root.add_widget(visual_box)

        self.intro_options = GridLayout(cols=2, size_hint_y=None, height=dp(126), spacing=dp(6))
        root.add_widget(self.intro_options)
        feedback_box = RoundedBox(size_hint_y=None, height=dp(78), padding=dp(9))
        self.intro_feedback = label("Выбери ответ — я сразу объясню логику.", 11, MUTED, valign="middle")
        self.intro_feedback.bind(size=lambda widget, value: setattr(widget, "text_size", value))
        feedback_box.add_widget(self.intro_feedback)
        root.add_widget(feedback_box)
        self.intro_next = Button(text="NEXT", size_hint_y=None, height=dp(46), disabled=True, background_color=(0.07, 0.46, 0.29, 1))
        self.intro_next.bind(on_release=lambda *_: self._next_intro_question())
        root.add_widget(self.intro_next)
        self._set_screen("intro", root, "left" if initial else "right")
        self._load_intro_question()

    def _load_intro_question(self):
        chapter = INTRO_CHAPTERS[self.intro_chapter]
        question = chapter["questions"][self.intro_question_index]
        board_codes, hero_codes, prompt, options, _correct, _feedback = question
        total = len(chapter["questions"])
        self.intro_chapter_title.text = chapter["title"]
        self.intro_lesson.text = chapter["lesson"]
        self.intro_question.text = prompt
        self.intro_counter.text = f"ГЛАВА {self.intro_chapter + 1}/5\n{self.intro_question_index + 1}/{total}"
        self.intro_feedback.text = "Выбери ответ — я сразу объясню логику."
        self.intro_feedback.color = MUTED
        self.intro_next.disabled = True
        self.intro_next.text = "FINISH INTRO" if self.intro_chapter == 4 and self.intro_question_index == total - 1 else "NEXT"

        self.intro_visual.clear_widgets()
        if board_codes or hero_codes:
            if board_codes:
                self.intro_visual.add_widget(label("BOARD", 9, MUTED, halign="center", size_hint_y=None, height=dp(16)))
                board_row = self._card_row(height=58, small=True)
                self.intro_visual.add_widget(board_row[0])
                self._render_cards(board_row[1], [card(code) for code in board_codes], small=True)
            if hero_codes:
                self.intro_visual.add_widget(label("YOUR HAND", 9, MUTED, halign="center", size_hint_y=None, height=dp(16)))
                hero_row = self._card_row(height=58, small=True)
                self.intro_visual.add_widget(hero_row[0])
                self._render_cards(hero_row[1], [card(code) for code in hero_codes], small=True)
        else:
            tokens = ("UTG", "HJ", "CO", "BTN", "SB", "BB") if self.intro_chapter == 1 else ("CHECK", "BET", "CALL", "RAISE", "FOLD")
            token_grid = GridLayout(cols=3 if len(tokens) == 6 else 5, spacing=dp(4), padding=(dp(2), dp(18)), size_hint_y=None, height=dp(96))
            for token in tokens:
                token_box = RoundedBox(padding=dp(3), bg_color=PANEL_LIGHT)
                token_box.add_widget(label(token, 10, GREEN if token in ("BTN", "BET", "RAISE") else WHITE, halign="center"))
                token_grid.add_widget(token_box)
            self.intro_visual.add_widget(token_grid)

        self.intro_options.clear_widgets()
        self.intro_option_buttons = []
        for option in options:
            button = Button(text=option, font_size=dp(10), halign="center", valign="middle")
            button.bind(size=lambda widget, value: setattr(widget, "text_size", (value[0] - dp(8), value[1] - dp(6))))
            button.bind(on_release=lambda _button, value=option: self._answer_intro(value))
            self.intro_option_buttons.append(button)
            self.intro_options.add_widget(button)

    def _answer_intro(self, selected):
        question = INTRO_CHAPTERS[self.intro_chapter]["questions"][self.intro_question_index]
        correct, feedback = question[4], question[5]
        is_correct = selected == correct
        if is_correct:
            self.intro_correct += 1
        for button in self.intro_option_buttons:
            button.disabled = True
            if button.text == correct:
                button.background_color = (0.08, 0.58, 0.32, 1)
            elif button.text == selected:
                button.background_color = (0.66, 0.14, 0.14, 1)
        self.intro_feedback.text = ("RIGHT. " if is_correct else f"NOT QUITE. Верно: {correct}. ") + feedback
        self.intro_feedback.color = GREEN if is_correct else YELLOW
        self.intro_next.disabled = False

    def _next_intro_question(self):
        questions = INTRO_CHAPTERS[self.intro_chapter]["questions"]
        if self.intro_question_index < len(questions) - 1:
            self.intro_question_index += 1
            self._load_intro_question()
            return
        if self.intro_chapter < len(INTRO_CHAPTERS) - 1:
            self.intro_chapter += 1
            self.intro_question_index = 0
            self._save_progress()
            self._load_intro_question()
            return
        self.onboarding_complete = True
        if not self.intro_rewarded:
            self.fanchips += 1000
            self.intro_rewarded = True
        self._save_progress()
        popup = self._message_popup(
            "WELCOME BONUS",
            "Интро пройдено. На баланс добавлено 1000 приветственных фантиков. Теперь можно за стол.",
            auto_open=False,
        )
        popup.bind(on_dismiss=lambda *_: self.show_home())
        popup.open()

    # ---------- Blitz ----------
    def start_blitz(self):
        if not self.premium and self.free_runs >= 2:
            self.open_subscription("Два бесплатных рана уже сыграны. Безлимитные раны входят в Premium.")
            return
        self.blitz_run_index = self.free_runs
        start = (self.blitz_run_index * 10) % len(BLITZ_TASKS)
        self.blitz_tasks = [BLITZ_TASKS[(start + index) % len(BLITZ_TASKS)] for index in range(10)]
        self.blitz_index = 0
        self.blitz_ideal = 0
        self.blitz_normal = 0
        self.blitz_errors = 0
        self.blitz_reward = 0
        self._build_blitz_screen()
        self._load_blitz_task()

    def _build_blitz_screen(self):
        root, body = self._page("БЛИЦ • РАН ИЗ 10", self.show_home)
        self.blitz_progress = label("", 12, MUTED, halign="center", size_hint_y=None, height=dp(24))
        body.add_widget(self.blitz_progress)
        table = RoundedBox(orientation="vertical", padding=dp(10), spacing=dp(4), bg_color=FELT)
        self.blitz_meta = label("", 13, GREEN, halign="center", size_hint_y=None, height=dp(26))
        self.blitz_history = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(4))
        self.blitz_board = self._card_row(height=60, small=True)
        self.blitz_hero = self._card_row(height=60, small=True)
        self.blitz_hand_name = label("", 12, WHITE, halign="center", size_hint_y=None, height=dp(24))
        table.add_widget(self.blitz_meta)
        table.add_widget(label("ACTION LINE", 9, MUTED, halign="center", size_hint_y=None, height=dp(15)))
        table.add_widget(self.blitz_history)
        table.add_widget(label("BOARD", 10, MUTED, halign="center", size_hint_y=None, height=dp(16)))
        table.add_widget(self.blitz_board[0])
        table.add_widget(label("YOUR HAND", 10, MUTED, halign="center", size_hint_y=None, height=dp(16)))
        table.add_widget(self.blitz_hero[0])
        table.add_widget(self.blitz_hand_name)
        body.add_widget(table)

        self.blitz_feedback = RoundedBox(orientation="vertical", size_hint_y=None, height=dp(112), padding=dp(9), spacing=dp(4))
        self.blitz_verdict = label("ВЫБЕРИТЕ ЛИНИЮ", 13, GREEN, halign="center", size_hint_y=None, height=dp(24))
        self.blitz_note = label("Один ответ лучший, один нормальный, два ошибочных.", 11, MUTED, valign="top")
        self.blitz_note.bind(size=lambda widget, value: setattr(widget, "text_size", value))
        self.blitz_feedback.add_widget(self.blitz_verdict)
        self.blitz_feedback.add_widget(self.blitz_note)
        body.add_widget(self.blitz_feedback)

        self.blitz_actions = GridLayout(cols=2, size_hint_y=None, height=dp(112), spacing=dp(6))
        self.blitz_buttons = {}
        action_text = {
            "check_fold": "FOLD",
            "small": "CALL",
            "big": "RAISE",
            "overbet": "OVER-RAISE",
        }
        for action, text_value in action_text.items():
            button = Button(text=text_value, font_size=dp(12))
            button.bind(on_release=lambda _button, value=action: self.answer_blitz(value))
            self.blitz_buttons[action] = button
            self.blitz_actions.add_widget(button)
        body.add_widget(self.blitz_actions)
        nav = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        self.blitz_ai = Button(text="ИИ-РАЗБОР", size_hint_x=0.40, disabled=True, font_size=dp(11))
        self.blitz_ai.bind(on_release=lambda *_: self.request_blitz_ai())
        self.blitz_next = Button(text="СЛЕДУЮЩАЯ ЗАДАЧА", disabled=True, font_size=dp(11))
        self.blitz_next.bind(on_release=lambda *_: self.next_blitz_task())
        nav.add_widget(self.blitz_ai)
        nav.add_widget(self.blitz_next)
        body.add_widget(nav)
        self._set_screen("blitz", root)

    def _load_blitz_task(self):
        current = self.blitz_tasks[self.blitz_index]
        self.current_blitz = current
        self.blitz_progress.text = (
            f"ЗАДАЧА {self.blitz_index + 1}/10   •   ИДЕАЛ {self.blitz_ideal}   НОРМА {self.blitz_normal}   ОШИБКИ {self.blitz_errors}"
        )
        street = STREET_LABELS[current["street"]]
        self.blitz_meta.text = f"{street}  •  {current['position']}  •  POT {current['pot']} BB  •  STACK {current['stack']} BB"
        self._render_action_history(self.blitz_history, current["history"])
        hero = [card(code) for code in current["hero"]]
        board = [card(code) for code in current["board"]]
        self._render_cards(self.blitz_hero[1], hero, small=True)
        if board:
            self._render_cards(self.blitz_board[1], board, small=True)
            self.blitz_hand_name.text = english_hand_name(evaluate(hero + board)[1])
        else:
            self._render_cards(self.blitz_board[1], [], small=True, hidden_count=5)
            self.blitz_hand_name.text = "BOARD NOT DEALT"
        self._configure_blitz_actions(current)
        self.blitz_verdict.text = "ВАШЕ РЕШЕНИЕ"
        self.blitz_verdict.color = GREEN
        self.blitz_note.text = "Выберите линию. После ответа тренер покажет качество решения и логику сайзинга."
        self.blitz_next.disabled = True
        remaining = "∞" if self.premium else str(max(0, 2 - self.ai_uses))
        self.blitz_ai.text = f"ИИ-РАЗБОР • {remaining}"
        self.blitz_ai.disabled = True
        for button in self.blitz_buttons.values():
            button.disabled = False

    def _configure_blitz_actions(self, current):
        if current["street"] == "ПРЕФЛОП":
            self.blitz_action_alias = {
                "check_fold": "fold",
                "small": "call",
                "big": "raise",
            }
            facing_raise = any("raise" in event.lower() or "рейз" in event.lower() for event in current["history"])
            texts = {
                "small": "CALL",
                "big": "RAISE / 3-BET" if facing_raise else "OPEN-RAISE",
                "check_fold": "FOLD",
            }
            visible_keys = ("small", "big", "check_fold")
        else:
            if self._blitz_facing_bet(current):
                self.blitz_action_alias = {
                    "check_fold": "fold",
                    "small": "call",
                    "big": "raise_small",
                    "overbet": "raise_big",
                }
                texts = {
                    "check_fold": "FOLD",
                    "small": "CALL",
                    "big": "SMALL RAISE",
                    "overbet": "BIG RAISE",
                }
            else:
                self.blitz_action_alias = {
                    "check_fold": "check",
                    "small": "bet_small",
                    "big": "bet_big",
                    "overbet": "overbet",
                }
                texts = {
                    "check_fold": "CHECK",
                    "small": "BET\n33% POT",
                    "big": "BET\n75% POT",
                    "overbet": "OVERBET\n125% POT",
                }
            visible_keys = ("check_fold", "small", "big", "overbet")

        self.blitz_actions.clear_widgets()
        self.blitz_actions.cols = len(visible_keys) if current["street"] == "ПРЕФЛОП" else 2
        for key in visible_keys:
            button = self.blitz_buttons[key]
            button.text = texts[key]
            self.blitz_actions.add_widget(button)
        self.blitz_display_labels = {
            self.blitz_action_alias[key]: texts[key].replace("\n", " ") for key in visible_keys
        }

    @staticmethod
    def _blitz_facing_bet(current):
        """True when the last postflop action is an opponent's bet."""
        if not current["history"]:
            return False
        last_action = current["history"][-1].strip().lower()
        actor_is_hero = last_action.startswith(("вы ", "you "))
        contains_bet = any(marker in last_action for marker in (" бет", " bet", "овербет", "overbet"))
        return contains_bet and not actor_is_hero

    def _blitz_action_label(self, action):
        """Return the label actually shown for the current street and sizing."""
        return self.blitz_display_labels.get(action, ACTION_LABELS.get(action, action.upper()))

    @staticmethod
    def _compact_action(event):
        value = event.upper()
        replacements = {
            "ВЫ": "YOU",
            "РЕЙЗ": "RAISE",
            "ФОЛД": "FOLD",
            "КОЛЛ": "CALL",
            "ЧЕК": "CHECK",
            "БЕТ": "BET",
            "ТЁРН": "TURN",
            "ФЛОП": "FLOP",
            "ДВА БАРРЕЛЯ И ДВА CALLА": "2 BARRELS / 2 CALLS",
        }
        for source, target in replacements.items():
            value = value.replace(source, target)
        parts = value.split(" ", 1)
        return parts[0] + ("\n" + parts[1] if len(parts) > 1 else "")

    def _render_action_history(self, container, history):
        container.clear_widgets()
        for index, event in enumerate(history):
            chip = RoundedBox(orientation="vertical", padding=dp(3), bg_color=PANEL_LIGHT)
            text_widget = label(self._compact_action(event), 8, WHITE, halign="center", valign="middle")
            text_widget.bind(size=lambda widget, value: setattr(widget, "text_size", value))
            chip.add_widget(text_widget)
            container.add_widget(chip)
            if index < len(history) - 1:
                container.add_widget(label(">", 12, GREEN, halign="center", size_hint_x=None, width=dp(12)))

    def answer_blitz(self, action):
        current = self.current_blitz
        action = self.blitz_action_alias[action]
        for button in self.blitz_buttons.values():
            button.disabled = True
        if action == current["best"]:
            quality, color_value, reward = "ЛУЧШИЙ ОТВЕТ", GREEN, 20
            self.blitz_ideal += 1
        elif action == current["normal"]:
            quality, color_value, reward = "НОРМАЛЬНАЯ ЛИНИЯ", YELLOW, 5
            self.blitz_normal += 1
        else:
            quality, color_value, reward = "ОШИБКА", RED, 0
            self.blitz_errors += 1
        self.blitz_reward += reward
        self.blitz_verdict.text = f"{quality}  •  +{reward} ФАНТИКОВ"
        self.blitz_verdict.color = color_value
        self.blitz_note.text = (
            f"Ваш выбор: {self._blitz_action_label(action)}. "
            f"Лучший: {self._blitz_action_label(current['best'])}.\n{current['note']}"
        )
        self.last_blitz_action = action
        self.blitz_next.text = "ЗАВЕРШИТЬ РАН" if self.blitz_index == 9 else "СЛЕДУЮЩАЯ ЗАДАЧА"
        self.blitz_next.disabled = False
        self.blitz_ai.disabled = not (self.premium or self.ai_uses < 2)

    def next_blitz_task(self):
        if self.blitz_index >= 9:
            self._finish_blitz_run()
            return
        self.blitz_index += 1
        self._load_blitz_task()

    def request_blitz_ai(self):
        if not self.ai.enabled:
            self.open_ai_settings()
            return
        if not self.premium and self.ai_uses >= 2:
            self.open_subscription("Два бесплатных ИИ-разбора уже использованы.")
            return
        self.ai_uses += 1
        self._save_progress()
        self.blitz_ai.disabled = True
        self.blitz_ai.text = "ИИ ДУМАЕТ…"
        current = self.current_blitz
        waiting = self._message_popup("ИИ-ТРЕНЕР", "Разбираю диапазоны и сайзинг…", auto_open=False)
        waiting.open()

        def worker():
            try:
                answer = self.ai.explain_poker(
                    {
                        "street": current["street"],
                        "position": current["position"],
                        "hero": current["hero"],
                        "board": current["board"],
                        "history": current["history"],
                        "pot_bb": current["pot"],
                        "stack_bb": current["stack"],
                    },
                    self._blitz_action_label(self.last_blitz_action),
                    current["note"],
                )
            except Exception as exc:
                answer = f"ИИ сейчас недоступен: {exc}"
            Clock.schedule_once(lambda *_: self._replace_popup(waiting, "РАЗБОР ИИ", answer), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_blitz_run(self):
        if not self.premium:
            self.free_runs += 1
        bonus = 500 if self.blitz_ideal == 10 else 0
        self.fanchips += self.blitz_reward + bonus
        self._save_progress()
        bonus_text = "\nИДЕАЛЬНЫЙ РАН: бонус +500 фантиков!" if bonus else "\nИдеальный ран — 10/10 лучших ответов — даст бонус +500."
        popup = self._message_popup(
            "РАН ЗАВЕРШЁН",
            f"Лучших: {self.blitz_ideal}\nНормальных: {self.blitz_normal}\nОшибок: {self.blitz_errors}\nНаграда: +{self.blitz_reward + bonus} фантиков{bonus_text}",
            auto_open=False,
        )
        popup.bind(on_dismiss=lambda *_: self.show_home())
        popup.open()

    # ---------- EV battle ----------
    def show_ev_select(self):
        self.start_ev_battle()

    def start_ev_battle(self, bot_key=None):
        keys = list(BOT_PROFILES)
        if bot_key is None:
            previous = getattr(self, "ev_bot_key", None)
            bot_key = self.rng.choice([key for key in keys if key != previous] or keys)
        self.ev_bot_key = bot_key
        self.ev_profile = BOT_PROFILES[bot_key]
        self.ev_hero_position, self.ev_bot_position, self.ev_hero, self.ev_bot_cards = deal_matchup(self.rng)
        used = set(self.ev_hero + self.ev_bot_cards)
        deck = [item for item in fresh_deck(self.rng) if item not in used]
        self.ev_board_full = [deck.pop() for _ in range(5)]
        self.ev_board_count = self.rng.choice((3, 4))
        self.ev_pot = 100
        self.ev_stack = 900
        self.ev_bot_stack = 900
        self.ev_facing_bet = 0
        self.ev_hero_commit = 0
        self.ev_bot_commit = 0
        self.ev_raise_count = 0
        self.ev_bot_checked = False
        self.ev_finished = False
        self.ev_history = []
        position_order = {"UTG": 0, "HJ": 1, "CO": 2, "BTN": 3, "SB": 4, "BB": 5}
        if position_order[self.ev_hero_position] < position_order[self.ev_bot_position]:
            self._add_ev_event("YOU", "OPEN 2.5", street="PREFLOP", render=False)
            self._add_ev_event(self.ev_bot_position, "CALL", street="PREFLOP", render=False)
        else:
            self._add_ev_event(self.ev_bot_position, "OPEN 2.5", street="PREFLOP", render=False)
            self._add_ev_event("YOU", "CALL", street="PREFLOP", render=False)
        if self.ev_board_count == 4:
            first = self.ev_bot_position if self._ev_bot_acts_first() else "YOU"
            second = "YOU" if first == self.ev_bot_position else self.ev_bot_position
            self._add_ev_event(first, "CHECK", street="FLOP", render=False)
            self._add_ev_event(second, "CHECK", street="FLOP", render=False)
        self._build_ev_screen()
        self._begin_ev_street(self.ev_profile["intro"])

    def _build_ev_screen(self):
        root, body = self._page(f"EV BATTLE • {self.ev_profile['name']}", self.show_home)
        table = RoundedBox(orientation="vertical", padding=dp(9), spacing=dp(3), bg_color=FELT)
        self.ev_status = label("", 12, GREEN, halign="center", size_hint_y=None, height=dp(25))
        self.ev_bot_zone = self._card_row(height=58, small=True)
        self.ev_board_zone = self._card_row(height=58, small=True)
        self.ev_hero_zone = self._card_row(height=58, small=True)
        self.ev_combo = label("", 11, WHITE, halign="center", size_hint_y=None, height=dp(22))
        table.add_widget(self.ev_status)
        table.add_widget(label(f"{self.ev_profile['tag']} • {self.ev_bot_position}", 10, MUTED, halign="center", size_hint_y=None, height=dp(17)))
        table.add_widget(self.ev_bot_zone[0])
        table.add_widget(label("BOARD", 10, MUTED, halign="center", size_hint_y=None, height=dp(16)))
        table.add_widget(self.ev_board_zone[0])
        table.add_widget(label(f"YOUR HAND • {self.ev_hero_position}", 10, MUTED, halign="center", size_hint_y=None, height=dp(16)))
        table.add_widget(self.ev_hero_zone[0])
        table.add_widget(self.ev_combo)
        body.add_widget(table)

        history_box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(72), spacing=dp(2))
        history_header = BoxLayout(size_hint_y=None, height=dp(24))
        history_header.add_widget(label("ACTION REPLAY", 9, MUTED))
        self.ev_replay = Button(text="REPLAY", font_size=dp(9), size_hint_x=None, width=dp(74))
        self.ev_replay.bind(on_release=lambda *_: self.replay_ev_history())
        history_header.add_widget(self.ev_replay)
        history_box.add_widget(history_header)
        history_scroll = ScrollView(do_scroll_x=True, do_scroll_y=False, bar_width=dp(2))
        self.ev_history_row = BoxLayout(orientation="horizontal", size_hint_x=None, spacing=dp(4), height=dp(44))
        history_scroll.add_widget(self.ev_history_row)
        history_box.add_widget(history_scroll)
        body.add_widget(history_box)

        self.ev_speech = RoundedBox(orientation="vertical", size_hint_y=None, height=dp(72), padding=dp(8))
        self.ev_speech_label = label("", 10, WHITE, valign="top")
        self.ev_speech_label.bind(size=lambda widget, value: setattr(widget, "text_size", value))
        self.ev_speech.add_widget(self.ev_speech_label)
        body.add_widget(self.ev_speech)

        slider_box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(72), spacing=dp(2))
        self.ev_bet_label = label("", 12, YELLOW, halign="center", size_hint_y=None, height=dp(24))
        self.ev_slider = Slider(min=10, max=200, value=50, step=10)
        self.ev_slider.bind(value=lambda *_: self._update_ev_bet_label())
        slider_box.add_widget(self.ev_bet_label)
        slider_box.add_widget(self.ev_slider)
        body.add_widget(slider_box)

        controls = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6))
        self.ev_check = Button(text="CHECK")
        self.ev_bet = Button(text="BET")
        self.ev_fold = Button(text="FOLD")
        self.ev_check.bind(on_release=lambda *_: self.ev_action("call" if self.ev_facing_bet else "check"))
        self.ev_bet.bind(on_release=lambda *_: self.ev_action("raise" if self.ev_facing_bet else "bet"))
        self.ev_fold.bind(on_release=lambda *_: self.ev_action("fold"))
        controls.add_widget(self.ev_check)
        controls.add_widget(self.ev_bet)
        controls.add_widget(self.ev_fold)
        body.add_widget(controls)
        self.ev_again = Button(text="NEXT RANDOM HAND", size_hint_y=None, height=dp(44), disabled=True)
        self.ev_again.bind(on_release=lambda *_: self.start_ev_battle())
        body.add_widget(self.ev_again)
        self._set_screen("ev_battle", root)
        self._render_ev_history()

    def _update_ev_screen(self, speech=None):
        board = self.ev_board_full[:self.ev_board_count]
        street = "FLOP" if self.ev_board_count == 3 else "TURN" if self.ev_board_count == 4 else "RIVER"
        self.ev_status.text = f"{street}  •  POT {self.ev_pot}  •  YOU {self.ev_stack}  •  BOT {self.ev_bot_stack}"
        self._render_cards(self.ev_hero_zone[1], self.ev_hero, small=True)
        self._render_cards(self.ev_board_zone[1], board, small=True)
        if self.ev_finished:
            self._render_cards(self.ev_bot_zone[1], self.ev_bot_cards, small=True)
        else:
            self._render_cards(self.ev_bot_zone[1], [], small=True, hidden_count=2)
        self.ev_combo.text = f"MADE HAND: {english_hand_name(evaluate(self.ev_hero + board)[1])}"
        if speech is not None:
            self.ev_speech_label.text = f"{self.ev_profile['name']}:\n{speech}"
        if self.ev_finished:
            self.ev_facing_bet = 0
            self.ev_bet_label.text = "HAND COMPLETE  •  CARDS REVEALED"
            self.ev_check.text = "CHECK"
            self.ev_bet.text = "BET"
            self.ev_check.disabled = True
            self.ev_bet.disabled = True
            self.ev_fold.disabled = True
            self.ev_slider.disabled = True
            return
        self.ev_facing_bet = self._ev_amount_to_call()
        if self.ev_facing_bet:
            max_target = self.ev_hero_commit + self.ev_stack
            minimum_target = self.ev_bot_commit + max(10, self.ev_bot_commit - self.ev_hero_commit)
            slider_min = min(max_target, minimum_target)
            self.ev_slider.min = slider_min
            self.ev_slider.max = max(slider_min, max_target)
            self.ev_slider.value = slider_min
            self.ev_check.text = f"CALL {min(self.ev_stack, self.ev_facing_bet)}"
            self.ev_bet.text = "RE-RAISE" if self.ev_raise_count else "RAISE"
        else:
            max_bet = min(self.ev_stack, max(20, self.ev_pot * 2))
            slider_min = min(10, max_bet)
            self.ev_slider.min = slider_min
            self.ev_slider.max = max(slider_min, max_bet)
            self.ev_slider.value = min(max_bet, max(slider_min, self.ev_pot // 2))
            self.ev_check.text = "CHECK"
            self.ev_bet.text = "BET"
        can_raise = self.ev_hero_commit + self.ev_stack > self.ev_bot_commit
        self.ev_check.disabled = self.ev_finished or self.ev_stack <= 0
        self.ev_bet.disabled = self.ev_finished or self.ev_stack <= 0 or (self.ev_facing_bet > 0 and not can_raise)
        self.ev_fold.disabled = self.ev_finished or self.ev_facing_bet == 0
        self.ev_slider.disabled = self.ev_bet.disabled
        self._update_ev_bet_label()

    def _update_ev_bet_label(self):
        if hasattr(self, "ev_bet_label"):
            amount = int(self.ev_slider.value)
            if self.ev_facing_bet:
                added = max(0, amount - self.ev_hero_commit)
                self.ev_bet_label.text = f"RAISE TO: {amount}  •  ADD {added} CHIPS"
            else:
                ratio = int(amount / max(1, self.ev_pot) * 100)
                self.ev_bet_label.text = f"BET SIZE: {amount} CHIPS  •  {ratio}% POT"

    def _add_ev_event(self, actor, action, amount=0, street=None, render=True):
        current_street = street or ("FLOP" if self.ev_board_count == 3 else "TURN" if self.ev_board_count == 4 else "RIVER")
        self.ev_history.append((current_street, actor, action, amount))
        if render and hasattr(self, "ev_history_row"):
            self._render_ev_history()

    def _render_ev_history(self, count=None):
        events = self.ev_history if count is None else self.ev_history[:count]
        self.ev_history_row.clear_widgets()
        for street, actor, action, amount in events:
            chip = RoundedBox(orientation="vertical", size_hint_x=None, width=dp(82), padding=dp(3), bg_color=PANEL_LIGHT)
            chip.add_widget(label(f"{street} • {actor}", 7, MUTED, halign="center", size_hint_y=None, height=dp(15)))
            suffix = f" {amount}" if amount else ""
            chip.add_widget(label(f"{action}{suffix}", 9, GREEN if actor == "YOU" else YELLOW, halign="center"))
            self.ev_history_row.add_widget(chip)
        self.ev_history_row.width = max(dp(82), len(events) * dp(86))

    def replay_ev_history(self):
        if not self.ev_history:
            return
        self.ev_replay.disabled = True
        self.ev_replay_index = 0
        self._render_ev_history(0)
        Clock.schedule_interval(self._replay_ev_step, 0.45)

    def _replay_ev_step(self, _dt):
        self.ev_replay_index += 1
        self._render_ev_history(self.ev_replay_index)
        if self.ev_replay_index >= len(self.ev_history):
            self.ev_replay.disabled = False
            return False
        return True

    def ev_action(self, action):
        if self.ev_finished:
            return
        facing = self._ev_amount_to_call()
        if action == "fold":
            if not facing:
                return
            self._add_ev_event("YOU", "FOLD")
            self._finish_ev(-1, "FOLD сохраняет остаток stack. Эту раздачу забирает соперник.")
            return
        if action == "call" and facing:
            amount = self._commit_ev("hero", facing)
            self._add_ev_event("YOU", "CALL", amount)
            self._advance_ev("CALL закрывает торговлю. Переходим дальше без лишних действий.")
            return
        if action == "check" and not facing:
            self._add_ev_event("YOU", "CHECK")
            if self.ev_bot_checked:
                self._advance_ev("CHECK back: улица закрыта без ставки.")
            else:
                self._bot_open_action(after_hero_check=True)
            return
        if action not in ("bet", "raise"):
            return

        if facing:
            target = min(self.ev_hero_commit + self.ev_stack, int(self.ev_slider.value))
            if target <= self.ev_bot_commit:
                return
            self._commit_ev("hero", target - self.ev_hero_commit)
            self.ev_raise_count += 1
            self._add_ev_event("YOU", "RAISE TO", self.ev_hero_commit)
            self._bot_respond_to_wager(can_raise=False)
        else:
            amount = self._commit_ev("hero", int(self.ev_slider.value))
            if amount <= 0:
                return
            self._add_ev_event("YOU", "BET", amount)
            self._bot_respond_to_wager(can_raise=True)

    def _ev_bot_acts_first(self):
        return acts_first_postflop(self.ev_bot_position, self.ev_hero_position)

    def _ev_amount_to_call(self):
        return max(0, self.ev_bot_commit - self.ev_hero_commit)

    def _commit_ev(self, actor, amount):
        amount = max(0, int(amount))
        if actor == "hero":
            paid = min(self.ev_stack, amount)
            self.ev_stack -= paid
            self.ev_hero_commit += paid
        else:
            paid = min(self.ev_bot_stack, amount)
            self.ev_bot_stack -= paid
            self.ev_bot_commit += paid
        self.ev_pot += paid
        self.ev_facing_bet = self._ev_amount_to_call()
        return paid

    def _ev_bot_read(self):
        board = self.ev_board_full[:self.ev_board_count]
        seed_text = "".join(compact_code(item) for item in self.ev_bot_cards + board)
        seed_text += self.ev_bot_key + self.ev_hero_position
        seed = sum((index + 1) * ord(character) for index, character in enumerate(seed_text))
        equity = estimate_equity_vs_range(
            self.ev_bot_cards,
            board,
            self.ev_hero_position,
            random.Random(seed),
        )
        return made_category(self.ev_bot_cards, board), equity

    def _begin_ev_street(self, lead_phrase):
        self.ev_hero_commit = 0
        self.ev_bot_commit = 0
        self.ev_raise_count = 0
        self.ev_facing_bet = 0
        self.ev_bot_checked = False
        if self._ev_bot_acts_first():
            self._bot_open_action(lead_phrase=lead_phrase)
        else:
            prompt = f"{lead_phrase}\nВы действуете первым: CHECK или выберите BET вручную."
            self._update_ev_screen(prompt)
            self._speak(lead_phrase)

    def _bot_open_action(self, after_hero_check=False, lead_phrase=None):
        category, equity = self._ev_bot_read()
        response, fraction = bot_open_decision(self.ev_bot_key, category, equity)
        prefix = f"{lead_phrase}\n" if lead_phrase else ""
        if response == "check":
            self.ev_bot_checked = True
            self._add_ev_event(self.ev_bot_position, "CHECK")
            phrase = prefix + ("После вашего CHECK я тоже не раздуваю pot." if after_hero_check else "Я CHECK. Решение за вами.")
            if after_hero_check:
                self._advance_ev(phrase)
            else:
                self._update_ev_screen(phrase)
                self._speak(phrase)
            return

        amount = min(self.ev_bot_stack, max(10, int(round(self.ev_pot * fraction / 10.0) * 10)))
        amount = self._commit_ev("bot", amount)
        self._add_ev_event(self.ev_bot_position, "BET", amount)
        phrase = prefix + f"Ставлю {amount}: моя made hand прошла value-порог, sizing связан с pot."
        self._update_ev_screen(phrase)
        self._speak(phrase)

    def _bot_respond_to_wager(self, can_raise):
        amount_to_call = max(0, self.ev_hero_commit - self.ev_bot_commit)
        if amount_to_call <= 0:
            self._advance_ev("Ставки уравнены.")
            return
        category, equity = self._ev_bot_read()
        response = bot_facing_decision(
            self.ev_bot_key,
            category,
            equity,
            amount_to_call,
            self.ev_pot,
            can_raise=can_raise and self.ev_raise_count == 0 and self.ev_bot_stack > amount_to_call,
        )
        if response == "fold":
            self._add_ev_event(self.ev_bot_position, "FOLD")
            self._finish_ev(1, "Моих equity и pot odds недостаточно для этого sizing. FOLD.")
            return
        if response == "raise":
            minimum_target = self.ev_hero_commit + max(10, self.ev_hero_commit - self.ev_bot_commit)
            target = min(self.ev_bot_commit + self.ev_bot_stack, minimum_target)
            self._commit_ev("bot", target - self.ev_bot_commit)
            self.ev_raise_count += 1
            self._add_ev_event(self.ev_bot_position, "RAISE TO", self.ev_bot_commit)
            phrase = f"Сильный value: RAISE TO {self.ev_bot_commit}. Теперь можно CALL, RE-RAISE или FOLD."
            self._update_ev_screen(phrase)
            self._speak(phrase)
            return

        paid = self._commit_ev("bot", amount_to_call)
        self._add_ev_event(self.ev_bot_position, "CALL", paid)
        self._advance_ev("Pot odds и сила диапазона позволяют CALL. Торговля закрыта.")

    def _advance_ev(self, phrase):
        self._speak(phrase)
        if self.ev_board_count >= 5 or self.ev_stack == 0 or self.ev_bot_stack == 0:
            while self.ev_board_count < 5:
                self.ev_board_count += 1
                self._add_ev_event("TABLE", f"DEAL {compact_code(self.ev_board_full[self.ev_board_count - 1])}")
            self._showdown_ev(phrase)
            return
        self.ev_board_count += 1
        self._add_ev_event("TABLE", f"DEAL {compact_code(self.ev_board_full[self.ev_board_count - 1])}")
        self._begin_ev_street(phrase)

    def _showdown_ev(self, phrase):
        result, hero_name, bot_name = compare(self.ev_hero, self.ev_bot_cards, self.ev_board_full)
        self._add_ev_event("TABLE", "SHOWDOWN")
        text = f"Showdown: YOU {english_hand_name(hero_name)}, BOT {english_hand_name(bot_name)}."
        self._finish_ev(result, f"{phrase}\n{text}")

    def _finish_ev(self, result, phrase):
        self.ev_finished = True
        self.ev_facing_bet = 0
        outcome = "ВЫ ЗАБРАЛИ БАНК" if result > 0 else "БАНК У СОПЕРНИКА" if result < 0 else "БАНК ПОДЕЛЁН"
        premium_text = (
            f"\n\nАЛГОРИТМ БОТА:\n{self.ev_profile['algorithm']}"
            if self.premium
            else "\n\nПодробный разбор алгоритма этой руки доступен в Premium."
        )
        self._update_ev_screen(f"{outcome}\n{phrase}{premium_text}")
        self.ev_check.disabled = True
        self.ev_bet.disabled = True
        self.ev_fold.disabled = True
        self.ev_slider.disabled = True
        self.ev_again.disabled = False
        self._speak(outcome)

    # ---------- Fanchips ----------
    def show_fanchip_lobby(self):
        root, body = self._page("COMMUNITY SANDBOX", self.show_home)
        note = label("Один открытый Hold'em-стол без Premium-локов. Сейчас он работает локально с ботом; живые community rooms подключаются через backend.", 11, MUTED, halign="center", size_hint_y=None, height=dp(78))
        note.bind(size=lambda widget, value: setattr(widget, "text_size", value))
        body.add_widget(note)
        table_preview = RoundedBox(orientation="vertical", padding=dp(14), spacing=dp(10), bg_color=FELT)
        table_preview.add_widget(label("OPEN TABLE • 6-MAX HOLD'EM", 19, GREEN, halign="center"))
        seats = GridLayout(cols=3, spacing=dp(8), size_hint_y=None, height=dp(120))
        for seat in ("SEAT 1", "SEAT 2", "BOT", "YOU", "SEAT 5", "SEAT 6"):
            seat_box = RoundedBox(padding=dp(4), bg_color=PANEL_LIGHT)
            seat_box.add_widget(label(seat, 11, YELLOW if seat == "YOU" else WHITE, halign="center"))
            seats.add_widget(seat_box)
        table_preview.add_widget(seats)
        table_preview.add_widget(label("Без buy-in и блокировок • фантики не имеют денежной ценности", 11, MUTED, halign="center"))
        join_button = Button(text="JOIN OPEN TABLE", size_hint_y=None, height=dp(48), background_color=(0.08, 0.50, 0.32, 1))
        join_button.bind(on_release=lambda *_: self.start_fanchip_hand())
        table_preview.add_widget(join_button)
        body.add_widget(table_preview)
        reward_note = label("Награда или потеря за раздачу: 10 учебных фантиков. Даже с нулевым балансом игра не блокируется.", 10, MUTED, halign="center", size_hint_y=None, height=dp(58))
        reward_note.bind(size=lambda widget, value: setattr(widget, "text_size", value))
        body.add_widget(reward_note)
        self._set_screen("fanchip_lobby", root)

    def start_fanchip_hand(self, *_):
        self.fan_limit = 10
        self.fan_hero_position, self.fan_bot_position, self.fan_hero, self.fan_bot = deal_matchup(self.rng, ("BTN", "BB"))
        used = set(self.fan_hero + self.fan_bot)
        deck = [item for item in fresh_deck(self.rng) if item not in used]
        self.fan_board = [deck.pop() for _ in range(5)]
        self.fan_board_count = 3
        self.fan_pot = 20
        self.fan_facing_bet = 0
        self.fan_finished = False
        self._build_fanchip_table()

    def _build_fanchip_table(self):
        root, body = self._page("OPEN HOLD'EM TABLE", self.show_fanchip_lobby)
        table = RoundedBox(orientation="vertical", padding=dp(10), spacing=dp(5), bg_color=FELT)
        self.fan_status = label("FLOP • POT 20 • ACTION ON YOU", 13, GREEN, halign="center", size_hint_y=None, height=dp(28))
        self.fan_bot_zone = self._card_row(height=66)
        self.fan_board_zone = self._card_row(height=60, small=True)
        self.fan_hero_zone = self._card_row(height=66)
        self.fan_result = label("", 12, WHITE, halign="center", valign="middle", size_hint_y=None, height=dp(70))
        self.fan_result.bind(size=lambda widget, value: setattr(widget, "text_size", value))
        table.add_widget(self.fan_status)
        table.add_widget(label("COMMUNITY BOT • BB", 10, MUTED, halign="center", size_hint_y=None, height=dp(17)))
        table.add_widget(self.fan_bot_zone[0])
        table.add_widget(label("BOARD", 10, MUTED, halign="center", size_hint_y=None, height=dp(17)))
        table.add_widget(self.fan_board_zone[0])
        table.add_widget(label("YOUR HAND • BTN", 10, MUTED, halign="center", size_hint_y=None, height=dp(17)))
        table.add_widget(self.fan_hero_zone[0])
        table.add_widget(self.fan_result)
        body.add_widget(table)
        self._render_cards(self.fan_bot_zone[1], [], hidden_count=2)
        self._render_cards(self.fan_board_zone[1], self.fan_board[:self.fan_board_count], small=True)
        self._render_cards(self.fan_hero_zone[1], self.fan_hero)
        self.fan_result.text = f"MADE HAND: {english_hand_name(evaluate(self.fan_hero + self.fan_board[:3])[1])}\nИгра идёт по улицам до showdown."
        controls = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(7))
        self.fan_check = Button(text="CHECK")
        self.fan_bet = Button(text="BET 50%")
        self.fan_fold = Button(text="FOLD")
        self.fan_check.bind(on_release=lambda *_: self.fanchip_action("call" if self.fan_facing_bet else "check"))
        self.fan_bet.bind(on_release=lambda *_: self.fanchip_action("raise" if self.fan_facing_bet else "bet"))
        self.fan_fold.bind(on_release=lambda *_: self.fanchip_action("fold"))
        controls.add_widget(self.fan_check)
        controls.add_widget(self.fan_bet)
        controls.add_widget(self.fan_fold)
        body.add_widget(controls)
        self.fan_again = Button(text="NEXT HAND", size_hint_y=None, height=dp(46), disabled=True)
        self.fan_again.bind(on_release=lambda *_: self.start_fanchip_hand())
        body.add_widget(self.fan_again)
        self._set_screen("fanchip_table", root)

    def fanchip_action(self, action):
        if self.fan_finished:
            return
        if action == "fold":
            self._finish_fanchip(-1, "YOU FOLD • банк забирает соперник")
            return
        if action == "call":
            self.fan_pot += self.fan_facing_bet
            self.fan_facing_bet = 0
            self._advance_fanchip("YOU CALL • открываем следующую карту")
            return
        board = self.fan_board[:self.fan_board_count]
        bot_category = evaluate(self.fan_bot + board)[0][0]
        if action == "check":
            if bot_category >= 2:
                amount = max(5, self.fan_pot // 2)
                self.fan_pot += amount
                self.fan_facing_bet = amount
                self.fan_result.text = f"BOT BET {amount}\nРешай: CALL, RAISE или FOLD."
                self.fan_check.text = f"CALL {amount}"
                self.fan_bet.text = "RAISE"
                self._update_fanchip_status()
            else:
                self._advance_fanchip("YOU CHECK • BOT CHECK")
            return
        amount = max(5, self.fan_pot // 2)
        self.fan_pot += amount
        if bot_category == 0:
            self._finish_fanchip(1, f"YOU {'RAISE' if action == 'raise' else 'BET'} {amount} • BOT FOLD")
        else:
            self.fan_pot += amount
            self.fan_facing_bet = 0
            self._advance_fanchip(f"YOU {'RAISE' if action == 'raise' else 'BET'} {amount} • BOT CALL")

    def _advance_fanchip(self, action_line):
        if self.fan_board_count >= 5:
            result, hero_name, bot_name = compare(self.fan_hero, self.fan_bot, self.fan_board)
            self._finish_fanchip(result, f"{action_line}\nSHOWDOWN • {english_hand_name(hero_name)} vs {english_hand_name(bot_name)}")
            return
        self.fan_board_count += 1
        self._render_cards(self.fan_board_zone[1], self.fan_board[:self.fan_board_count], small=True)
        self.fan_result.text = f"{action_line}\nMADE HAND: {english_hand_name(evaluate(self.fan_hero + self.fan_board[:self.fan_board_count])[1])}"
        self.fan_check.text = "CHECK"
        self.fan_bet.text = "BET 50%"
        self._update_fanchip_status()

    def _update_fanchip_status(self):
        street = "FLOP" if self.fan_board_count == 3 else "TURN" if self.fan_board_count == 4 else "RIVER"
        facing = f" • TO CALL {self.fan_facing_bet}" if self.fan_facing_bet else ""
        self.fan_status.text = f"{street} • POT {self.fan_pot}{facing}"

    def _finish_fanchip(self, result, detail):
        if self.fan_finished:
            return
        self.fan_finished = True
        if result > 0:
            self.fanchips += 10
            outcome = "WIN • +10"
            color_value = GREEN
        elif result == 0:
            outcome = "SPLIT POT • 0"
            color_value = YELLOW
        else:
            self.fanchips = max(0, self.fanchips - 10)
            outcome = "LOSS • -10"
            color_value = RED
        self._save_progress()
        self._render_cards(self.fan_bot_zone[1], self.fan_bot)
        self._render_cards(self.fan_board_zone[1], self.fan_board, small=True)
        self.fan_status.text = outcome
        self.fan_status.color = color_value
        self.fan_result.text = f"{detail}\nBALANCE: {self.fanchips}"
        self.fan_check.disabled = True
        self.fan_bet.disabled = True
        self.fan_fold.disabled = True
        self.fan_again.disabled = False

    # ---------- Shared UI ----------
    @staticmethod
    def _card_row(height=66, small=False):
        anchor = AnchorLayout(anchor_x="center", anchor_y="center", size_hint_y=None, height=dp(height))
        row = BoxLayout(orientation="horizontal", spacing=dp(5), size_hint=(None, None), height=dp(54 if small else 66))
        anchor.add_widget(row)
        return anchor, row

    @staticmethod
    def _render_cards(container, cards, small=False, hidden_count=0, empty_text=""):
        container.clear_widgets()
        if not cards and not hidden_count and empty_text:
            placeholder = Label(
                text=empty_text,
                font_size=dp(11),
                color=MUTED,
                halign="center",
                valign="middle",
                size_hint=(None, None),
                size=(dp(260), dp(42)),
                text_size=(dp(260), dp(42)),
            )
            container.add_widget(placeholder)
            container.width = dp(260)
            return
        for item in cards:
            container.add_widget(PlayingCard(item, small=small))
        for _ in range(hidden_count):
            container.add_widget(PlayingCard(hidden=True, small=small))
        width = dp(38 if small else 46)
        count = len(cards) + hidden_count
        container.width = count * width + max(0, count - 1) * dp(5)

    def open_subscription(self, message=None):
        body = message or (
            "FREE: обязательное интро, 2 блиц-рана, 2 ИИ-разбора и открытая Hold'em-песочница.\n\n"
            "PREMIUM: безлимитные раны, больше ИИ-разборов и раскрытие алгоритмов EV-ботов. Песочница не блокируется подпиской.\n\n"
            "Оплата пока не подключена — это рабочий экран будущей подписки."
        )
        self._message_popup("ПОДПИСКА", body)

    def _open_social(self, network):
        self._message_popup(network.upper(), f"Кнопка готова. Добавьте будущую ссылку {network} в настройки релизной версии.")

    def open_ai_settings(self, *_):
        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        info = label("Ключ хранится только до закрытия приложения. В публичном релизе нужен сервер-посредник.", 12, MUTED, size_hint_y=None, height=dp(60))
        info.bind(size=lambda widget, value: setattr(widget, "text_size", value))
        key_input = TextInput(hint_text="OpenAI API key", password=True, multiline=False, text=self.ai.api_key, size_hint_y=None, height=dp(46))
        model_input = TextInput(hint_text="Модель", multiline=False, text=self.ai.model, size_hint_y=None, height=dp(46))
        remaining = "безлимитно" if self.premium else str(max(0, 2 - self.ai_uses))
        status = label(f"Бесплатных ИИ-разборов осталось: {remaining}", 12, GREEN, size_hint_y=None, height=dp(34))
        buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(7))
        save = Button(text="ПОДКЛЮЧИТЬ")
        disable = Button(text="ОТКЛЮЧИТЬ")
        buttons.add_widget(save)
        buttons.add_widget(disable)
        content.add_widget(info)
        content.add_widget(key_input)
        content.add_widget(model_input)
        content.add_widget(status)
        content.add_widget(buttons)
        popup = Popup(title="ИИ-РАЗБОР", content=content, size_hint=(0.92, 0.67))

        def connect(*_):
            self.ai.configure(key_input.text.strip(), model_input.text.strip())
            popup.dismiss()
            self._message_popup("ИИ ПОДКЛЮЧЁН", "В результатах блиц-задач можно запросить дополнительный разбор.")

        def disconnect(*_):
            self.ai.configure("", model_input.text.strip())
            popup.dismiss()

        save.bind(on_release=connect)
        disable.bind(on_release=disconnect)
        popup.open()

    def open_guide(self, *_):
        tabs = TabbedPanel(do_default_tab=False, tab_height=dp(44), tab_width=dp(100))
        sections = (
            ("База", self._guide_basics()),
            ("Блиц", self._guide_blitz()),
            ("Сленг", self._guide_terms()),
        )
        for title, body in sections:
            tab = TabbedPanelItem(text=title)
            tab.add_widget(self._scroll_text(body))
            tabs.add_widget(tab)
        tabs.switch_to(tabs.tab_list[-1])
        content = BoxLayout(orientation="vertical", spacing=dp(7))
        content.add_widget(tabs)
        back = Button(text="НАЗАД К ИГРЕ", size_hint_y=None, height=dp(48), background_color=(0.08, 0.48, 0.32, 1))
        content.add_widget(back)
        popup = Popup(title="Покер без занудства", content=content, size_hint=(0.94, 0.88))
        back.bind(on_release=popup.dismiss)
        popup.open()

    @staticmethod
    def _guide_basics():
        return (
            "TEXAS HOLD'EM — ПО-БРАТСКИ\n\n"
            "У вас две закрытые карты, на столе максимум пять общих. Собираем лучшую комбинацию из любых пяти карт.\n\n"
            "PREFLOP — общих карт ещё нет. FLOP — первые три. TURN — четвёртая. RIVER — последняя.\n\n"
            "Позиция решает: действуя позже, вы уже видели выбор соперника. Поэтому BTN обычно может играть шире, чем UTG.\n\n"
            "Размер ставки — это сообщение диапазону соперника. Малый бет давит дёшево, большой защищает и строит банк, овербет показывает полярность: либо очень сильно, либо продуманный блеф.\n\n"
            "Главное, бро: результат одной раздачи ничего не доказывает. Учимся качеству решения, а не магии ривера."
        )

    @staticmethod
    def _guide_blitz():
        return (
            "КАК РЕШАТЬ БЛИЦ\n\n"
            "Сначала прочитайте позицию и историю действий. Потом сравните, кому лучше подошёл борд. Только после этого выбирайте размер.\n\n"
            "PREFLOP даёт три решения: CALL, OPEN-RAISE/RAISE и FOLD. Sizing не выбирается отдельно под одну конкретную руку.\n\n"
            "POSTFLOP без чужой ставки: CHECK, BET 33%, BET 75% и OVERBET. Если соперник уже поставил: FOLD, CALL, SMALL RAISE и BIG RAISE.\n\n"
            "В каждой задаче один вариант лучший, один нормальный и два ошибочных. Идеальный ран 10/10 даёт бонус фантиков."
        )

    @staticmethod
    def _guide_terms():
        return (
            "СЛОВАРЬ БЕЗ ЗАНУДСТВА\n\n"
            "Straight Flush — пять одномастных карт подряд.\n\n"
            "Full House — тройка плюс пара.\n\n"
            "Nuts — лучшая возможная рука прямо сейчас.\n\n"
            "Equity — математическая доля pot руки против range.\n\n"
            "Fold equity — шанс забрать pot через FOLD соперника.\n\n"
            "Polarization — BET от очень сильных рук и bluff, без середины.\n\n"
            "Blocker — карта, уменьшающая число сильных combos у соперника.\n\n"
            "Dead money — чужие blind и limp, уже лежащие в pot.\n\n"
            "Tilt — эмоции сели за руль. Лучший sizing в этот момент — размер паузы."
        )

    @staticmethod
    def _scroll_text(body):
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        text = label(body, 14, WHITE, valign="top", size_hint_y=None, padding=(dp(10), dp(10)))
        text.bind(width=lambda widget, value: setattr(widget, "text_size", (value, None)))
        text.bind(texture_size=lambda widget, value: setattr(widget, "height", value[1] + dp(24)))
        scroll.add_widget(text)
        return scroll

    def _message_popup(self, title, text_value, auto_open=True):
        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        scroll = self._scroll_text(text_value)
        close = Button(text="ПОНЯТНО", size_hint_y=None, height=dp(46))
        content.add_widget(scroll)
        content.add_widget(close)
        popup = Popup(title=title, content=content, size_hint=(0.90, 0.70))
        close.bind(on_release=popup.dismiss)
        if auto_open:
            popup.open()
        return popup

    def _replace_popup(self, popup, title, text_value):
        popup.dismiss()
        self._message_popup(title, text_value)

    def _speak(self, text_value):
        if platform != "android":
            return
        try:
            from android.runnable import run_on_ui_thread
            from jnius import autoclass

            @run_on_ui_thread
            def speak_on_ui():
                try:
                    activity = autoclass("org.kivy.android.PythonActivity").mActivity
                    tts_class = autoclass("android.speech.tts.TextToSpeech")
                    if self._tts is None:
                        self._tts = tts_class(activity, None)
                    self._tts.speak(text_value, tts_class.QUEUE_FLUSH, None, "casino_coach_bot")
                except Exception:
                    pass

            speak_on_ui()
        except Exception:
            pass

    def _read_android_insets(self, *_):
        if platform != "android":
            return
        try:
            from android.runnable import run_on_ui_thread
            from jnius import autoclass

            @run_on_ui_thread
            def read_insets():
                try:
                    activity = autoclass("org.kivy.android.PythonActivity").mActivity
                    insets = activity.getWindow().getDecorView().getRootWindowInsets()
                    if insets is None:
                        return
                    values = (
                        int(insets.getSystemWindowInsetLeft()),
                        int(insets.getSystemWindowInsetTop()),
                        int(insets.getSystemWindowInsetRight()),
                        int(insets.getSystemWindowInsetBottom()),
                    )
                    Clock.schedule_once(lambda _dt: self._apply_insets(values), 0)
                except Exception:
                    pass

            read_insets()
        except Exception:
            pass

    def _apply_insets(self, values):
        left, top, right, bottom = values
        base = self._base_padding
        self.root_layout.padding = [base + left, base + top, base + right, base + bottom]


if __name__ == "__main__":
    CasinoCoachApp().run()
