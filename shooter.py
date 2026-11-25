# shooter.py — ПК-нападник, що "вчиться" на стрибках гравця-воротаря
import random
from keeper import ZONES, SUSPECT_LEVEL

STAND_ZONE = 4   # гравець не обрав зону — стоїть по центру внизу


class Shooter:
    def __init__(self, skill=0.7, decay=0.8, base=0.5):
        self.skill = skill   # як часто нападник б'є "з розрахунком", а не навмання
        self.decay = decay   # наскільки швидко забуваються старі стрибки
        self.base = base     # базова вага кожної зони
        self.reset()

    def reset(self):
        # лічильник: куди гравець стрибав
        self.history = [0.0] * len(ZONES)

    def choose_zone(self):
        # нападник частіше б'є туди, куди гравець стрибає РІДШЕ
        if random.random() < self.skill:
            top = max(self.history)
            weights = [self.base + (top - h) for h in self.history]
            return random.choices(ZONES, weights=weights)[0]
        return random.choice(ZONES)

    def choose_power(self, min_power, max_safe):
        # переважно нормальний удар, іноді занадто сильний або слабкий
        r = random.random()
        if r < 0.75:
            return random.randint(min_power, max_safe)
        if r < 0.9:
            return random.randint(max_safe + 1, 100)
        return random.randint(20, min_power - 1)

    def update(self, dive_zone):
        # старі стрибки забуваються, новий запам'ятовується
        for z in ZONES:
            self.history[z] *= self.decay
        self.history[dive_zone] += 1

    def suspects(self):
        # зона, куди гравець стрибає надто часто (нападник це помітив), або None
        top = max(ZONES, key=lambda z: self.history[z])
        if self.history[top] >= SUSPECT_LEVEL:
            return top
        return None