# goalie.py — ви на воротах: удар ПК, стрибок по кліку і сейв за відстанню від рук до м'яча (без tkinter)
import math
import random

from shot import GOAL, SAVE, MISS, miss_chance, aim_to_zone

GOAL_W, GOAL_H = 7.32, 2.44     # справжні розміри воріт, м
FLIGHT_SLOW = 0.75              # час польоту слабкого удару, с
FLIGHT_FAST = 0.45              # час польоту найсильнішого удару, с
WEAK_REACH_BONUS = 1.4          # слабкий удар легше взяти — радіус більший
READ_TIME = 0.4                 # стрибок за стільки секунд до удару нападник бачить напевно


def flight_time(power):
    # чим сильніший удар, тим швидше летить м'яч
    return FLIGHT_SLOW + (FLIGHT_FAST - FLIGHT_SLOW) * power / 100


def distance(a, b):
    # відстань у метрах між двома точками воріт (координати 0..1 по ширині і висоті)
    dx = (a[0] - b[0]) * GOAL_W
    dy = (a[1] - b[1]) * GOAL_H
    return math.hypot(dx, dy)


def move_towards(cur, target, max_m):
    # руки рухаються до цілі, але не більше ніж на max_m метрів за крок
    d = distance(cur, target)
    if d <= max_m:
        return target
    k = max_m / d
    return cur[0] + (target[0] - cur[0]) * k, cur[1] + (target[1] - cur[1]) * k


def clamp01(v):
    return min(max(v, 0.0), 1.0)


def farthest_zone(hands):
    # зона, центр якої найдалі від рук воротаря
    centers = [((z % 3 + 0.5) / 3, (z // 3 + 0.5) / 2) for z in range(6)]
    return max(range(6), key=lambda z: distance(hands, centers[z]))


class Defense:
    # один удар ПК: спершу kick() — куди і як сильно, потім judge() — чи встиг воротар
    def __init__(self, shooter, cfg):
        self.shooter = shooter
        self.min_power = cfg["min_power"]
        self.max_safe = cfg["max_safe"]
        self.reach = cfg["reach"]                 # на скільки метрів дотягуються руки
        self.dive_speed = cfg["dive_speed"]       # швидкість стрибка, м/с
        self.read_chance = cfg["read_chance"]     # шанс, що нападник побачить ранній стрибок
        self.kick_info = None

    def kick(self, hands=None, early=0.0):
        # нападник обирає зону (куди ви рідко тягнетесь), точку в ній і силу.
        # early — за скільки секунд до удару ви стрибнули (0 — не стрибали).
        # Чим раніше стрибок, тим імовірніше нападник це побачить і проб'є в найдальшу від вас зону
        seen = self.read_chance * min(1.0, early / READ_TIME)
        if early > 0 and random.random() < seen:
            zone = farthest_zone(hands)
        else:
            zone = self.shooter.choose_zone()
        power = self.shooter.choose_power(self.min_power, self.max_safe)
        col, row = zone % 3, zone // 3
        ax = (col + random.uniform(0.15, 0.85)) / 3
        ay = (row + random.uniform(0.15, 0.85)) / 2
        missed = power > self.max_safe and random.random() < miss_chance(power, self.max_safe)
        if missed:
            # м'яч летить повз: збоку від штанги або над перекладиною
            if col == 0:
                ax = -0.15
            elif col == 2:
                ax = 1.15
            else:
                ay = -0.3
        self.kick_info = {"zone": zone, "point": (ax, ay), "power": power,
                          "missed": missed, "time": flight_time(power)}
        return self.kick_info

    def judge(self, hands):
        # м'яч долетів: сейв, якщо руки ближче за радіус дотягування
        k = self.kick_info
        reach = self.reach * (WEAK_REACH_BONUS if k["power"] < self.min_power else 1)
        if k["missed"]:
            result = MISS
        elif distance(hands, k["point"]) <= reach:
            result = SAVE
        else:
            result = GOAL
        # нападник запам'ятовує, де були ваші руки
        dive_zone = aim_to_zone(clamp01(hands[0]), clamp01(hands[1]))
        self.shooter.update(dive_zone)
        return result, dive_zone