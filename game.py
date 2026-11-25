# game.py — серія з 5 ударів, рахунок, рівні і "золотий удар" (без tkinter)
from keeper import Keeper, ZONES
from shot import resolve_shot, GOAL, SAVE, MISS
from levels import LEVELS

SHOTS_IN_SERIES = 5
WIN_GOALS = 4        # стільки голів з 5 — перемога
DRAW_GOALS = 3       # стільки голів — нічия, буде "золотий удар"


class Game:
    turn = "shoot"   # у цьому режимі гравець тільки б'є

    def __init__(self, level="medium"):
        self.set_level(level)

    def set_level(self, level):
        # беремо налаштування рівня і створюємо під них воротаря
        self.level = level
        cfg = LEVELS[level]
        self.keeper = Keeper(cfg["skill"], cfg["decay"], cfg["base"])
        self.min_power = cfg["min_power"]
        self.max_safe = cfg["max_safe"]
        self.new_series()

    def new_series(self):
        self.keeper.reset()        # кожна серія — воротар починає з нуля
        self.shot_num = 0          # скільки ударів уже зроблено
        self.goals = 0
        self.shots = []            # історія: (зона удару, зона воротаря, результат)
        self.golden_shot = False   # чи зараз "золотий удар"
        self.finished = False

    def is_over(self):
        return self.finished

    def shoot(self, zone, power):
        # воротар обирає зону ДО того, як дізнається про удар
        keeper_zone = self.keeper.choose_zone()
        result = resolve_shot(zone, power, keeper_zone, self.min_power, self.max_safe)
        # після удару воротар запам'ятовує, куди били
        self.keeper.update(zone)

        self.shot_num += 1
        if result == GOAL:
            self.goals += 1
        self.shots.append((zone, keeper_zone, result))

        # чи закінчилась серія
        if self.golden_shot:
            self.finished = True                 # золотий удар — завжди останній
        elif self.shot_num == SHOTS_IN_SERIES:
            if self.goals == DRAW_GOALS:
                self.golden_shot = True          # нічия — даємо ще один удар
            else:
                self.finished = True
        return result, keeper_zone

    def is_win(self):
        if self.golden_shot:
            # у золотому ударі вирішує тільки останній удар
            return self.shots[-1][2] == GOAL
        return self.goals >= WIN_GOALS

    def verdict(self):
        if self.golden_shot:
            if self.is_win():
                return "Золотий удар забито! Перемога!"
            return "Золотий удар не забито. Воротар переміг."
        if self.is_win():
            return "Перемога над воротарем!"
        return "Воротар переміг."

    def stats(self):
        # статистика серії для екрана підсумку
        per_zone = [0] * len(ZONES)
        guessed = 0
        saves = 0
        misses = 0
        for zone, keeper_zone, result in self.shots:
            per_zone[zone] += 1
            if zone == keeper_zone:
                guessed += 1
            if result == SAVE:
                saves += 1
            elif result == MISS:
                misses += 1
        favourite = max(ZONES, key=lambda z: per_zone[z])
        return {
            "per_zone": per_zone,       # скільки разів били в кожну зону
            "guessed": guessed,         # скільки разів воротар вгадав зону
            "saves": saves,
            "misses": misses,
            "favourite": favourite,     # улюблена зона гравця
        }