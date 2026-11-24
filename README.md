# Пенальті з воротарем, що вчиться

Навчальний проєкт (НУБіП, ІПЗ). Аркадна гра: серія з 5 пенальті проти воротаря, який запам'ятовує, куди ви б'єте.

Python 3 + tkinter, тільки стандартна бібліотека.

## Завантажити гру

Гра доступна безкоштовно на itch.io: **посилання буде тут після публікації**

Завантажте `PenaltyGame-windows.zip`, розпакуйте і запустіть `PenaltyGame.exe`. Python не потрібен.

## Запуск з коду

- `python main.py` — гра у вікні
- `python console.py` — консольна версія (тільки логіка)

## Керування

Стрілки або клік — вибір зони, пробіл — запустити шкалу сили, пробіл — удар, Enter — нова гра.

## Збірка гри для itch.io

```
pip install pyinstaller
pyinstaller --windowed --name PenaltyGame main.py
```

У папці `dist/` з'явиться папка `PenaltyGame`. Її треба запакувати в `PenaltyGame-windows.zip` і завантажити на сторінку гри на itch.io (платформа Windows).

## Файли

- `keeper.py` — воротар і його «навчання»
- `shot.py` — результат удару (гол / сейв / промах)
- `game.py` — серія з 5 ударів, рахунок
- `console.py` — консольний прототип
- `ui.py` — графіка tkinter
- `main.py` — точка входу

Логіка (keeper, shot, game) не залежить від tkinter.

## Як підключити логіку до інтерфейсу

```python
from game import Game, SHOTS_IN_SERIES
from shot import GOAL, SAVE, MISS, MIN_POWER, MAX_SAFE

game = Game()
result, keeper_zone = game.shoot(zone, power)  # zone 0..5, power 0..100
game.goals          # скільки голів
game.shot_num       # скільки ударів зроблено
game.is_over()      # True після 5 ударів
game.verdict()      # текст підсумку
game.new_series()   # нова гра
```

Зони воріт:

```
0 | 1 | 2   (верх)
3 | 4 | 5   (низ)
```

Сила: 0–39 слабко (воротар бере і сусідню зону), 40–80 оптимально, понад 80 — шанс промаху.
`result` — один із GOAL / SAVE / MISS. `keeper_zone` — куди стрибнув воротар (для анімації).

## Команда

- Василега Артьом — логіка гри, алгоритм воротаря, консольний прототип
- Коваленко Михайло — графіка й інтерфейс tkinter
