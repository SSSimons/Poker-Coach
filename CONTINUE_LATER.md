# Точка продолжения

Состояние на 4 сентября 2026:

- Casino Coach 0.5.4 запускает обязательный onboarding из глав 1.1–1.5; все 21 вопрос пройдены UI smoke-тестом;
- после первого полного прохождения один раз начисляется 1000 приветственных фантиков;
- Blitz содержит 20 сценариев; preflop всегда показывает ровно три действия CALL, OPEN-RAISE/RAISE и FOLD, а postflop различает свободное действие и ставку соперника;
- спорная задача T♦9♦ на K♦Q♦3♠2♣ исправлена: CHECK — лучший ответ, BET 33% — допустимая альтернатива, а BET 75% больше не предлагается как обязательный;
- EV Battle сам выбирает нового случайного бота, раздаёт руки из позиционных range, отображает динамическую историю и умеет REPLAY;
- EV Battle теперь соблюдает postflop-порядок позиций, отдельно считает pot, оба stack и вклады улицы, а кнопки меняются между CHECK/BET и CALL/RAISE/FOLD;
- боты не смотрят карты героя: их решения основаны на Monte Carlo equity против range позиции, pot odds, sizing и индивидуальном leak;
- Community Sandbox открыт всем и разыгрывает локальную Hold’em-раздачу по улицам;
- poker actions, betting и названия комбинаций в интерфейсе оставлены на английском;
- справочник, кнопка возврата, подписка, AI-разбор и точки редиректа IG/YT сохранены.

Готовые файлы после финальной сборки:

- `CasinoCoach-0.5.4-Samsung-arm64-v8a-debug.apk` — Samsung и другие ARM64-телефоны;
- `CasinoCoach-0.5.4-x86_64-debug.apk` — Android Studio Virtual Device;
- `CasinoCoach-0.5.4-ev-final.png` и `CasinoCoach-0.5.4-ev-action.png` — контрольные скриншоты новой EV-логики.

Исправление 0.5.2: preflop Blitz содержит три действия без выбора sizing — CALL, OPEN-RAISE/RAISE и FOLD. При наличии предыдущего raise средняя кнопка корректно называется RAISE / 3-BET. Четыре процентных sizing остаются только на postflop.

Исправление 0.5.3: postflop-кнопки теперь зависят от последнего действия. Без ставки соперника доступны CHECK и три BET-sizing; против BET доступны FOLD, CALL, SMALL RAISE и BIG RAISE. В задаче с 9♥8♥ на J♥7♣2♥ против BET 33% CALL назначен лучшим ответом.

Исправление 0.5.4: в спорной turn-задаче с T♦9♦ базовой линией стал CHECK. EV Battle переведён на последовательную betting state machine; исправлены позиционный порядок, CALL/RAISE/RE-RAISE, доплаты, переходы улиц, all-in runout и решения ботов по range-equity/pot odds.

Проверка файлов 0.5.4:

- x86_64 SHA-256: `470BF66A07BDA2ECCCF0D09967EAB3BE5B31D97DF236C1C660749D37A77E3134`;
- ARM64 SHA-256: `03D0E72BFBBB3CE2B9954D7AACF204138AA0F61287C0A155F3E068B7D9840210`;
- обе APK проходят `apksigner verify`; Samsung APK содержит только `arm64-v8a`;
- 24 unit-теста и расширенный `tools/smoke_ui.py` проходят;
- x86_64 APK установлена в `CasinoCoach_API_35`; визуально проверены bot FOLD и цепочка `BB CHECK → YOU BET 50 → BB CALL → TURN`, включая pot/stack и action replay.

Важно: Community Sandbox пока локальный и играет против бота. Реальный онлайн возможен, но не должен изображаться готовым: нужны backend, комнаты, аккаунты, WebSocket, серверная колода/валидация, БД, reconnect и anti-cheat. Также не подключены реальные платежи и URL соцсетей. AI-разбор вызывает API только после ввода ключа; публичному APK нужен сервер-посредник.

Для дальнейшей сборки в WSL используйте только скрипты:

```bash
cd /home/se/projects/casino_coach
source /home/se/.venvs/kivy-android/bin/activate
./tools/build_emulator_apk.sh
./tools/build_phone_apk.sh
```

Не выполнять `buildozer android clean`: кэш сборки содержит подготовленные Android-зависимости и патчи упаковки CPython 3.12.
