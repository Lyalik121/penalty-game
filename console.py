# console.py — консольна версія (прототип 2): лише логіка, без графіки
from game import Game, SHOTS_IN_SERIES
from keeper import ZONE_NAMES
from levels import LEVELS, LEVEL_ORDER
from records import save_record
from shot import GOAL, SAVE, MISS

RESULT_TEXT = {GOAL: "ГОЛ!", SAVE: "Сейв воротаря", MISS: "Промах повз ворота"}


def ask_int(prompt, low, high):
    # питаємо число, поки не введуть правильне
    while True:
        text = input(prompt)
        if text.isdigit() and low <= int(text) <= high:
            return int(text)
        print(f"Введіть число від {low} до {high}")


def main():
    # вибір рівня
    for i, key in enumerate(LEVEL_ORDER, start=1):
        print(f"{i} — {LEVELS[key]['name']}")
    level = LEVEL_ORDER[ask_int("Рівень (1-3): ", 1, 3) - 1]
    game = Game(level)

    print("Зони воріт:\n 1 | 2 | 3   (верх)\n 4 | 5 | 6   (низ)")
    while not game.is_over():
        if game.golden_shot:
            print("\nНічия! ЗОЛОТИЙ УДАР")
        else:
            print(f"\nУдар {game.shot_num + 1}/{SHOTS_IN_SERIES}, голів: {game.goals}")
        zone = ask_int("Зона (1-6): ", 1, 6) - 1
        power = ask_int("Сила (0-100): ", 0, 100)
        result, keeper_zone = game.shoot(zone, power)
        print(f"Воротар стрибнув: {ZONE_NAMES[keeper_zone]} -> {RESULT_TEXT[result]}")
        # показуємо, що воротар запам'ятав (для налаштування параметрів)
        print("Статистика воротаря:", [round(h, 2) for h in game.keeper.history])

    # підсумок
    st = game.stats()
    print(f"\nПідсумок: {game.goals} голів. {game.verdict()}")
    print(f"Воротар вгадав зону {st['guessed']} раз(и), сейвів: {st['saves']}, промахів: {st['misses']}")
    print(f"Ваша улюблена зона: {ZONE_NAMES[st['favourite']]}")
    if save_record(level, game.goals):
        print("Новий рекорд!")


if __name__ == "__main__":
    main()