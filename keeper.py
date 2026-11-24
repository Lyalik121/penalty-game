# keeper.py — воротар, що "вчиться" на ударах гравця
import random

# Зони воріт мають номери 0..5:
#   0 | 1 | 2   (верх)
#   3 | 4 | 5   (низ)
ZONES = [0, 1, 2, 3, 4, 5]
ZONE_NAMES = ["верх-ліво", "верх-центр", "верх-право",
              "низ-ліво", "низ-центр", "низ-право"]

SUSPECT_LEVEL = 2.0   # з якого значення лічильника воротар "щось запідозрив"


class Keeper:
    def __init__(self, skill=0.7, decay=0.8, base=0.5):
        self.skill = skill   # 0 = стрибає навмання, 1 = завжди за статистикою
        self.decay = decay   # наскільки швидко забуваються старі удари
        self.base = base     # базова вага кожної зони (щоб не було 100% передбачуваності)
        self.reset()

    def reset(self):
        # лічильник ударів гравця в кожну зону
        self.history = [0.0] * len(ZONES)

    def choose_zone(self):
        # з ймовірністю skill воротар "думає" за статистикою
        if random.random() < self.skill:
            weights = [self.base + h for h in self.history]
            return random.choices(ZONES, weights=weights)[0]
        # інакше стрибає в випадкову зону
        return random.choice(ZONES)

    def update(self, shot_zone):
        # старі удари поступово забуваються
        for z in ZONES:
            self.history[z] *= self.decay
        # запам'ятовуємо новий удар
        self.history[shot_zone] += 1

    def suspects(self):
        # повертає зону, яку воротар "запідозрив", або None
        top = max(ZONES, key=lambda z: self.history[z])
        if self.history[top] >= SUSPECT_LEVEL:
            return top
        return None