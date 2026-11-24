# shot.py — визначає результат удару
import random

GOAL = "GOAL"
SAVE = "SAVE"
MISS = "MISS"

MAX_MISS_CHANCE = 0.6   # шанс промаху при силі 100


def miss_chance(power, max_safe):
    # при силі max_safe шанс промаху 0, при силі 100 — MAX_MISS_CHANCE
    return (power - max_safe) / (100 - max_safe) * MAX_MISS_CHANCE


def aim_to_zone(ax, ay):
    # точка прицілу (ax, ay від 0 до 1 всередині воріт) -> номер зони 0..5
    col = min(int(ax * 3), 2)
    row = min(int(ay * 2), 1)
    return row * 3 + col


def is_adjacent(a, b):
    # зони сусідні, якщо відрізняються рівно на одну клітинку по горизонталі або вертикалі
    row_a, col_a = a // 3, a % 3
    row_b, col_b = b // 3, b % 3
    return abs(row_a - row_b) + abs(col_a - col_b) == 1


def resolve_shot(shot_zone, power, keeper_zone, min_power=40, max_safe=80):
    # 1) занадто сильний удар може піти повз ворота
    if power > max_safe and random.random() < miss_chance(power, max_safe):
        return MISS
    # 2) воротар вгадав зону
    if keeper_zone == shot_zone:
        return SAVE
    # 3) слабкий удар — воротар встигає в сусідню зону
    if power < min_power and is_adjacent(keeper_zone, shot_zone):
        return SAVE
    return GOAL