# match.py — матч по черзі (гравець б'є і ловить) і тренування на воротах (без tkinter)
from keeper import Keeper, ZONES
from shooter import Shooter
from goalie import Defense
from shot import resolve_shot, GOAL, SAVE, MISS
from levels import LEVELS

SHOTS_EACH = 5          # ударів у кожного в основній серії
TRAINING_SHOTS = 5      # ударів ПК у тренуванні


class Match:
    def __init__(self, level="medium"):
        self.set_level(level)

    def set_level(self, level):
        self.level = level
        cfg = LEVELS[level]
        self.keeper = Keeper(cfg["skill"], cfg["decay"], cfg["base"])     # ловить ваші удари
        self.shooter = Shooter(cfg["skill"], cfg["decay"], cfg["base"])   # б'є вам
        self.defense = Defense(self.shooter, cfg)                         # ваша гра на воротах
        self.min_power = cfg["min_power"]
        self.max_safe = cfg["max_safe"]
        self.new_match()

    def new_match(self):
        self.keeper.reset()
        self.shooter.reset()
        self.player_shots = []   # ваші удари: (зона, зона воротаря, результат)
        self.pc_shots = []       # удари ПК: (зона, де були ваші руки, результат)
        self.turn = "shoot"      # "shoot" — б'єте ви, "save" — ви на воротах
        self.finished = False

    @property
    def player_goals(self):
        return sum(1 for s in self.player_shots if s[2] == GOAL)

    @property
    def pc_goals(self):
        return sum(1 for s in self.pc_shots if s[2] == GOAL)

    def shoot(self, zone, power):
        # ваш удар
        keeper_zone = self.keeper.choose_zone()
        result = resolve_shot(zone, power, keeper_zone, self.min_power, self.max_safe)
        self.keeper.update(zone)
        self.player_shots.append((zone, keeper_zone, result))
        self.turn = "save"
        self._check_end()
        return result, keeper_zone

    def pc_kick(self, hands=None, early=0.0):
        # удар ПК: куди летить м'яч, з якою силою і скільки секунд
        return self.defense.kick(hands, early)

    def finish_save(self, hands):
        # м'яч долетів; hands — де були ваші руки (0..1 по ширині і висоті воріт)
        result, dive_zone = self.defense.judge(hands)
        self.pc_shots.append((self.defense.kick_info["zone"], dive_zone, result))
        self.turn = "shoot"
        self._check_end()
        return result

    def _check_end(self):
        # правила серії пенальті
        np, nc = len(self.player_shots), len(self.pc_shots)
        pg, cg = self.player_goals, self.pc_goals
        if np <= SHOTS_EACH and nc <= SHOTS_EACH:
            # основна серія: кінець, якщо хтось уже не наздожене навіть з усіма ударами, що лишились
            if pg + (SHOTS_EACH - np) < cg or cg + (SHOTS_EACH - nc) < pg:
                self.finished = True
        elif np == nc and pg != cg:
            # додаткові удари: після кожної пари ударів, якщо рахунок різний — кінець
            self.finished = True

    def is_over(self):
        return self.finished

    def is_win(self):
        return self.player_goals > self.pc_goals

    def verdict(self):
        if self.is_win():
            return "Ви виграли серію пенальті!"
        return "ПК виграв серію пенальті."

    def stats(self):
        dives = [0] * len(ZONES)
        for _, dive, _ in self.pc_shots:
            dives[dive] += 1
        return {
            "saves": sum(1 for s in self.pc_shots if s[2] == SAVE),
            "pc_misses": sum(1 for s in self.pc_shots if s[2] == MISS),
            "favourite_dive": max(ZONES, key=lambda z: dives[z]),
        }


class SaveTraining:
    turn = "save"   # у тренуванні ви тільки на воротах

    def __init__(self, level="medium"):
        self.set_level(level)

    def set_level(self, level):
        self.level = level
        cfg = LEVELS[level]
        self.shooter = Shooter(cfg["skill"], cfg["decay"], cfg["base"])
        self.defense = Defense(self.shooter, cfg)
        self.new_series()

    def new_series(self):
        self.shooter.reset()
        self.pc_shots = []
        self.finished = False

    @property
    def saves(self):
        # відбитий або повз ворота — гол не пропущено
        return sum(1 for s in self.pc_shots if s[2] != GOAL)

    def pc_kick(self, hands=None, early=0.0):
        return self.defense.kick(hands, early)

    def finish_save(self, hands):
        result, dive_zone = self.defense.judge(hands)
        self.pc_shots.append((self.defense.kick_info["zone"], dive_zone, result))
        if len(self.pc_shots) >= TRAINING_SHOTS:
            self.finished = True
        return result

    def is_over(self):
        return self.finished

    def is_win(self):
        return self.saves >= 2

    def verdict(self):
        if self.saves >= 3:
            return "Легенда воріт!"
        if self.saves == 2:
            return "Добрий воротар!"
        return "Нападник виявився сильнішим."