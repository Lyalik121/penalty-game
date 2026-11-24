# ui.py — інтерфейс гри: меню, екран гри, підсумок (вся логіка — у game.py)
import math
import tkinter as tk

import theme
from sound import play as play_sound
from game import Game, SHOTS_IN_SERIES
from keeper import ZONE_NAMES
from levels import LEVELS, LEVEL_ORDER
from records import load_records, save_record
from shot import GOAL, SAVE, MISS, aim_to_zone
from theme import (PANEL, PANEL_LINE, TEXT, MUTED, GOLD, GREEN, RED, BLUE, PURPLE, BG,
                   font, title_font, round_rect, lerp_color)
from scene import (W, H, GX1, GX2, GY1, GY2, BALL_SPOT, KEEPER_HOME,
                   draw_stadium, draw_pitch, draw_goal, draw_keeper, keeper_hands,
                   draw_player, draw_ball, draw_crosshair, draw_star, draw_icon)

FRAME_MS = 16             # один кадр ~16 мс (≈60 кадрів за секунду)
AIM_SPEED = 0.018         # швидкість прицілу (частка ширини воріт за кадр)
POWER_SPEED = 2.2         # швидкість шкали сили (одиниць за кадр)
FLIGHT_SPEED = 0.04       # швидкість польоту м'яча (t від 0 до 1)
RUNUP_FRAMES = 22         # скільки кадрів триває розбіг гравця
PLAYER_HOME = (330, 590)  # де стоїть гравець до удару
RESULT_FRAMES = 70        # скільки кадрів показуємо напис ГОЛ!/СЕЙВ!

RESULT_TEXT = {GOAL: "ГОЛ!", SAVE: "СЕЙВ!", MISS: "ПРОМАХ!"}
RESULT_SOUND = {GOAL: "goal", SAVE: "save", MISS: "miss"}
RESULT_COLOR = {GOAL: GREEN, SAVE: RED, MISS: "#dddddd"}

# три кроки удару: назва і підказка
STEPS = ["aim_x", "aim_y", "power"]
STEP_TEXT = {
    "aim_x": ("НАПРЯМОК", "Приціл рухається вліво-вправо · пробіл — зупинити"),
    "aim_y": ("ВИСОТА", "Приціл рухається вгору-вниз · пробіл — зупинити"),
    "power": ("СИЛА", "Зупиніть шкалу в зеленій зоні · пробіл — удар"),
}
GAME_STATES = STEPS + ["runup", "flying", "result"]

KEEPER_IDLE_HANDS = -44   # де руки воротаря, коли він стоїть (відносно ніг)


def aim_point(ax, ay):
    # точка прицілу (0..1) -> координати на екрані
    return GX1 + ax * (GX2 - GX1), GY1 + ay * (GY2 - GY1)


def bounce(value, direction, speed, low, high):
    # рух туди-назад між low і high (для прицілу і шкали сили)
    value += direction * speed
    if value >= high:
        return high, -1
    if value <= low:
        return low, 1
    return value, direction


def lerp(a, b, t):
    # значення між a і b
    return a + (b - a) * t


class PenaltyApp:
    def __init__(self, root):
        self.root = root
        root.title("Пенальті з воротарем, що вчиться")
        root.resizable(False, False)
        theme.pick_fonts(root)
        self.canvas = tk.Canvas(root, width=W, height=H, bg=BG, highlightthickness=0)
        self.canvas.pack()

        self.game = Game()
        self.buttons = []         # кнопки поточного екрана: (x1, y1, x2, y2, дія)
        self.last_game = None     # (текст результату, рівень) для панелі "Остання гра"
        self.state = "menu"

        root.bind("<Key>", self.on_key)
        self.canvas.bind("<Button-1>", self.on_click)
        self.show_menu()
        self.tick()               # запускаємо ігровий цикл

    # ================= допоміжне малювання =================
    def clear(self):
        self.canvas.delete("all")
        self.buttons = []

    def panel(self, x1, y1, x2, y2, outline=PANEL_LINE, tag=""):
        round_rect(self.canvas, x1, y1, x2, y2, r=14, fill=PANEL, outline=outline, width=2, tags=tag)

    def button(self, x1, y1, x2, y2, text, action, primary=True, tag=""):
        # жовта (primary) або контурна кнопка, яку можна натиснути мишкою
        c = self.canvas
        if primary:
            round_rect(c, x1, y1, x2, y2, r=10, fill=GOLD, outline="", tags=tag)
            c.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=text, fill="#1a1405", font=title_font(11), tags=tag)
        else:
            round_rect(c, x1, y1, x2, y2, r=10, fill=PANEL, outline=PANEL_LINE, width=2, tags=tag)
            c.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=text, fill=TEXT, font=title_font(11), tags=tag)
        self.buttons.append((x1, y1, x2, y2, action))

    def card(self, x, y, icon, title, sub, accent, action):
        # картка меню з іконкою
        c = self.canvas
        self.panel(x, y, x + 270, y + 70)
        c.create_line(x + 2, y + 12, x + 2, y + 58, fill=accent, width=4)
        round_rect(c, x + 16, y + 15, x + 56, y + 55, r=10, fill="", outline=accent, width=2)
        draw_icon(c, icon, x + 36, y + 35, accent)
        c.create_text(x + 70, y + 27, text=title, anchor="w", fill=TEXT, font=title_font(15))
        c.create_text(x + 70, y + 49, text=sub, anchor="w", fill=MUTED, font=font(9))
        c.create_text(x + 250, y + 35, text="→", fill=MUTED, font=font(14))
        self.buttons.append((x, y, x + 270, y + 70, action))

    # ================= меню =================
    def show_menu(self):
        self.state = "menu"
        self.clear()
        c = self.canvas
        draw_stadium(c, dim=0.6)
        draw_pitch(c, dim=0.6)
        draw_goal(c, dx=230)
        draw_keeper(c, 710, KEEPER_HOME[1], tag="bg")

        # логотип і заголовок
        draw_star(c, 46, 40, 14, GOLD)
        c.create_text(72, 32, text="НАВЧАЛЬНИЙ ПРОЄКТ", anchor="w", fill=MUTED, font=font(8, True))
        c.create_text(72, 48, text="ПЕНАЛЬТІ", anchor="w", fill=TEXT, font=title_font(13))
        c.create_line(40, 135, 70, 135, fill=GOLD, width=2)
        c.create_text(80, 135, text="PYTHON + TKINTER · 2026", anchor="w", fill="#c9d3d6", font=font(9, True))
        c.create_text(36, 205, text="ПЕНАЛЬТІ", anchor="w", fill=TEXT, font=title_font(58))
        c.create_text(38, 268, text="ВОРОТАР, ЩО ВЧИТЬСЯ", anchor="w", fill=GOLD, font=title_font(28))
        c.create_text(40, 305, text="Він запам'ятовує, куди ви б'єте. Перехитріть його.",
                      anchor="w", fill="#c9d3d6", font=font(11))

        # картки
        self.card(36, 340, "play", "ШВИДКА ГРА", "5 ударів · середній рівень", GOLD,
                  lambda: self.start_game("medium"))
        self.card(320, 340, "levels", "РІВНІ", "Легкий · Середній · Складний", GREEN, self.show_levels)
        self.card(36, 422, "list", "РЕКОРДИ", "Ваші найкращі серії", BLUE, self.show_records)
        self.card(320, 422, "help", "ЯК ГРАТИ", "Приціл, висота, сила", PURPLE, self.show_help)
        c.create_text(40, 520, text="ENTER — ШВИДКА ГРА", anchor="w", fill="#c9d3d6", font=font(9, True))

        # остання гра
        self.panel(680, 350, 930, 422, outline=GOLD)
        if self.last_game:
            text, level = self.last_game
            c.create_text(698, 368, text="ОСТАННЯ ГРА", anchor="w", fill=MUTED, font=font(8, True))
            c.create_text(698, 392, text=text, anchor="w", fill=TEXT, font=title_font(15))
            c.create_text(698, 410, text=LEVELS[level]["name"] + " рівень", anchor="w", fill=MUTED, font=font(9))
            self.button(840, 376, 916, 402, "РЕВАНШ", lambda: self.start_game(level))
        else:
            c.create_text(698, 368, text="ПЕРША ГРА", anchor="w", fill=MUTED, font=font(8, True))
            c.create_text(698, 392, text="Воротар ще не знає вас", anchor="w", fill=TEXT, font=title_font(14))
            c.create_text(698, 410, text="Скористайтесь цим!", anchor="w", fill=MUTED, font=font(9))

        # рекорди
        self.panel(680, 434, 930, 566)
        c.create_text(698, 452, text="РЕКОРДИ", anchor="w", fill=MUTED, font=font(8, True))
        records = load_records()
        for i, (key, color) in enumerate(zip(LEVEL_ORDER, [GREEN, GOLD, RED])):
            x = 692 + i * 80
            round_rect(c, x, 466, x + 72, 556, r=10, fill="#132530", outline="")
            c.create_oval(x + 28, 478, x + 44, 494, outline=color, width=2)
            c.create_text(x + 36, 516, text=str(records.get(key, 0)), fill=color, font=title_font(22))
            c.create_text(x + 36, 542, text=LEVELS[key]["name"].upper(), fill=MUTED, font=font(7, True))

        c.create_text(W / 2, 582, text="Гра створена: Василега Артьом, Коваленко Михайло",
                      fill="#c9d3d6", font=font(9, True))

    def overlay(self, title):
        # велика панель поверх меню (рівні, рекорди, як грати)
        self.buttons = []           # кнопки меню під панеллю не мають натискатись
        c = self.canvas
        self.panel(230, 110, 730, 520, outline=GOLD)
        c.create_text(W / 2, 145, text=title, fill=TEXT, font=title_font(22))
        self.button(420, 470, 540, 502, "НАЗАД", self.show_menu, primary=False)

    def show_levels(self):
        self.state = "levels"
        self.overlay("ОБЕРІТЬ РІВЕНЬ")
        c = self.canvas
        desc = {"easy": "Воротар часто стрибає навмання і швидко забуває",
                "medium": "Воротар помічає ваші улюблені кути",
                "hard": "Воротар довго пам'ятає, зелена зона сили вужча"}
        for i, (key, color) in enumerate(zip(LEVEL_ORDER, [GREEN, GOLD, RED])):
            y = 180 + i * 92
            round_rect(c, 270, y, 690, y + 78, r=12, fill="#132530", outline=color, width=2)
            c.create_text(300, y + 39, text=str(i + 1), fill=color, font=title_font(26))
            c.create_text(340, y + 28, text=LEVELS[key]["name"].upper(), anchor="w", fill=TEXT, font=title_font(16))
            c.create_text(340, y + 52, text=desc[key], anchor="w", fill=MUTED, font=font(10))
            self.buttons.append((270, y, 690, y + 78, lambda k=key: self.start_game(k)))

    def show_records(self):
        self.state = "records"
        self.overlay("РЕКОРДИ")
        c = self.canvas
        records = load_records()
        for i, (key, color) in enumerate(zip(LEVEL_ORDER, [GREEN, GOLD, RED])):
            y = 200 + i * 70
            c.create_text(300, y, text=LEVELS[key]["name"], anchor="w", fill=TEXT, font=title_font(18))
            c.create_text(660, y, text=f"{records.get(key, 0)} голів", anchor="e", fill=color, font=title_font(18))
            c.create_line(300, y + 26, 660, y + 26, fill=PANEL_LINE)
        c.create_text(W / 2, 420, text="Рекорд — найбільше голів за одну серію на рівні",
                      fill=MUTED, font=font(10))

    def show_help(self):
        self.state = "help"
        self.overlay("ЯК ГРАТИ")
        lines = ["1. Приціл бігає вліво-вправо — пробіл, щоб зупинити.",
                 "2. Потім вгору-вниз — пробіл ще раз.",
                 "3. Шкала сили: зелена зона — ідеально,",
                 "    жовта — слабко, червона — ризик промаху.",
                 "4. Серія — 5 ударів. 4+ голи — перемога, 3 — золотий удар.",
                 "",
                 "Воротар запам'ятовує, куди ви б'єте, і читає",
                 "улюблені кути. Міняйте тактику!"]
        for i, text in enumerate(lines):
            self.canvas.create_text(270, 190 + i * 32, text=text, anchor="w", fill=TEXT, font=font(12))

    # ================= гра =================
    def start_game(self, level):
        self.game.set_level(level)
        self.clear()
        c = self.canvas
        # статичний фон малюємо один раз, а рухомі речі — щокадру з тегом "dyn"
        draw_stadium(c)
        draw_pitch(c)
        draw_goal(c)
        self.shot_log = []                 # (точка прицілу, зона воротаря, результат) для карти ударів
        self.start_shot()

    def start_shot(self):
        self.state = "aim_x"
        self.ax, self.ay = 0.5, 0.5        # приціл у центрі воріт
        self.aim_dir = 1
        self.power, self.power_dir = 0, 1
        self.ball = BALL_SPOT
        self.ball_r = 11
        self.ball_shadow = BALL_SPOT[1] + 11
        self.keeper_x, self.keeper_y = KEEPER_HOME
        self.keeper_lean = 0.0
        self.keeper_hands = KEEPER_IDLE_HANDS
        self.result = None
        self.player_pos = PLAYER_HOME
        self.swing = 0.0

    def press(self):
        # пробіл або клік: зупинити поточний крок
        if self.state == "aim_x":
            self.state = "aim_y"
            self.ay, self.aim_dir = 0.95, -1     # висота стартує знизу
        elif self.state == "aim_y":
            self.state = "power"
        elif self.state == "power":
            self.shoot()

    def shoot(self):
        zone = aim_to_zone(self.ax, self.ay)
        self.result, keeper_zone = self.game.shoot(zone, self.power)
        self.state = "runup"               # спочатку розбіг, потім політ м'яча
        self.run_t = 0.0
        self.t = 0.0
        self.shot_log.append((aim_point(self.ax, self.ay), keeper_zone, self.result))

        # куди стрибає воротар: руки мають опинитись у центрі його зони
        col, row = keeper_zone % 3, keeper_zone // 3
        lean = [-1, 0, 1][col]
        zx = GX1 + (col + 0.5) * (GX2 - GX1) / 3
        if row == 0:                                 # верхня зона — стрибок вгору
            hands = -70
            zy = GY1 + 28
        else:                                        # нижня — руки внизу
            hands = -22
            zy = GY2 - 26
        self.k_from = (self.keeper_x, self.keeper_y, 0.0, KEEPER_IDLE_HANDS)
        ky = min(KEEPER_HOME[1], zy - hands)         # ноги не можуть бути нижче газону
        self.k_to = (zx - lean * 30, ky, float(lean), hands)

        # куди летить м'яч
        tx, ty = aim_point(self.ax, self.ay)
        if self.result == SAVE:
            tx, ty = keeper_hands(*self.k_to[:3], self.k_to[3])
        elif self.result == MISS:
            aim_col = zone % 3
            if aim_col == 0:
                tx = GX1 - 45                         # повз лівої штанги
            elif aim_col == 2:
                tx = GX2 + 45                         # повз правої
            else:
                ty = GY1 - 35                         # над перекладиною
        self.b_from = BALL_SPOT
        self.b_to = (tx, ty)

    def update_runup(self):
        # розбіг: гравець іде до м'яча, права нога відводиться назад і падає в удар
        self.run_t = min(1.0, self.run_t + 1 / RUNUP_FRAMES)
        r = self.run_t
        self.player_pos = (PLAYER_HOME[0] + 50 * r, PLAYER_HOME[1] - 30 * r)
        self.swing = math.sin(math.pi * r)
        if r >= 1.0:
            self.swing = 0.0
            self.state = "flying"
            play_sound("kick")

    def update_flight(self):
        # один кадр польоту м'яча і стрибка воротаря
        self.t = min(1.0, self.t + FLIGHT_SPEED)
        t = self.t
        (bx1, by1), (bx2, by2) = self.b_from, self.b_to
        self.ball = (lerp(bx1, bx2, t), lerp(by1, by2, t) - 25 * 4 * t * (1 - t))   # невелика дуга
        self.ball_r = lerp(11, 6, t)
        self.ball_shadow = lerp(BALL_SPOT[1] + 11, GY2 + 2, t)
        kt = max(0.0, (t - 0.15) / 0.85)             # воротар реагує трохи пізніше
        f, to = self.k_from, self.k_to
        self.keeper_x = lerp(f[0], to[0], kt)
        self.keeper_y = lerp(f[1], to[1], kt)
        self.keeper_lean = lerp(f[2], to[2], kt)
        self.keeper_hands = lerp(f[3], to[3], kt)
        if t >= 1.0:
            self.state = "result"
            self.frames_left = RESULT_FRAMES
            play_sound(RESULT_SOUND[self.result])

    # ================= ігровий цикл =================
    def tick(self):
        # викликається кожні FRAME_MS: оновлюємо стан і перемальовуємо рухомі об'єкти
        s = self.state
        if s == "aim_x":
            self.ax, self.aim_dir = bounce(self.ax, self.aim_dir, AIM_SPEED, 0.0, 1.0)
        elif s == "aim_y":
            self.ay, self.aim_dir = bounce(self.ay, self.aim_dir, AIM_SPEED, 0.0, 1.0)
        elif s == "power":
            self.power, self.power_dir = bounce(self.power, self.power_dir, POWER_SPEED, 0, 100)
        elif s == "runup":
            self.update_runup()
        elif s == "flying":
            self.update_flight()
        elif s == "result":
            self.frames_left -= 1
            if self.frames_left <= 0:
                if self.game.is_over():
                    self.show_summary()
                else:
                    self.start_shot()
        if self.state in GAME_STATES:
            self.draw_frame()
        self.root.after(FRAME_MS, self.tick)

    def draw_frame(self):
        c = self.canvas
        c.delete("dyn")              # стираємо все рухоме з минулого кадру
        draw_player(c, *self.player_pos, tag="dyn", swing=self.swing)
        draw_keeper(c, self.keeper_x, self.keeper_y, self.keeper_lean, hands=self.keeper_hands)
        if self.state in STEPS:
            draw_crosshair(c, *aim_point(self.ax, self.ay), BALL_SPOT)
        draw_ball(c, *self.ball, r=self.ball_r, shadow_y=self.ball_shadow)
        self.draw_scoreboard()
        self.draw_intuition()
        if self.state in STEPS:
            self.draw_step_panel()
        if self.state == "result":
            c.create_text(W / 2, 175, text=RESULT_TEXT[self.result], fill=RESULT_COLOR[self.result],
                          font=title_font(56), tags="dyn")
            if self.game.golden_shot and not self.game.is_over():
                c.create_text(W / 2, 215, text="Нічия! Буде золотий удар", fill=GOLD,
                              font=title_font(16), tags="dyn")

    def draw_scoreboard(self):
        c, g = self.canvas, self.game
        round_rect(c, 270, 14, 690, 74, r=16, fill=PANEL, outline=PANEL_LINE, width=2, tags="dyn")
        c.create_text(292, 36, text="ВИ", anchor="w", fill=TEXT, font=title_font(15), tags="dyn")
        c.create_text(292, 56, text="Нападник", anchor="w", fill=MUTED, font=font(9), tags="dyn")
        c.create_text(428, 44, text=str(g.goals), fill=TEXT, font=title_font(28), tags="dyn")
        c.create_text(668, 36, text="ВОРОТАР", anchor="e", fill=TEXT, font=title_font(15), tags="dyn")
        c.create_text(668, 56, text="ШІ · " + LEVELS[g.level]["name"].lower(), anchor="e",
                      fill=MUTED, font=font(9), tags="dyn")
        c.create_text(532, 44, text=str(g.shot_num - g.goals), fill=TEXT, font=title_font(28), tags="dyn")
        c.create_line(455, 22, 455, 66, fill=PANEL_LINE, tags="dyn")
        c.create_line(505, 22, 505, 66, fill=PANEL_LINE, tags="dyn")

        # номер удару: під час польоту показуємо поточний, а не наступний
        current = g.shot_num if self.state in ("flying", "result") else g.shot_num + 1
        if g.golden_shot:
            label = "ЗОЛОТИЙ"
        else:
            label = f"УДАР {min(current, SHOTS_IN_SERIES)}/{SHOTS_IN_SERIES}"
        c.create_text(480, 30, text=label, fill=MUTED, font=font(8, True), tags="dyn")

        # кружечки ударів: зелений — гол, червоний — ні, жовтий контур — поточний
        n = SHOTS_IN_SERIES + (1 if g.golden_shot else 0)
        start = 480 - (n - 1) * 7.5 / 2
        for i in range(n):
            x = start + i * 7.5
            if i < len(g.shots):
                color = GREEN if g.shots[i][2] == GOAL else RED
                c.create_oval(x - 3, 47, x + 3, 53, fill=color, outline="", tags="dyn")
            elif i == len(g.shots):
                c.create_oval(x - 3.5, 46.5, x + 3.5, 53.5, outline=GOLD, width=2, tags="dyn")
            else:
                c.create_oval(x - 3, 47, x + 3, 53, fill="#3a4a55", outline="", tags="dyn")

    def draw_intuition(self):
        # міні-карта воріт: червоним — зони, які воротар запам'ятав
        c = self.canvas
        keeper = self.game.keeper
        round_rect(c, 20, 14, 230, 92, r=14, fill=PANEL, outline=PANEL_LINE, width=2, tags="dyn")
        c.create_text(36, 30, text="ІНТУЇЦІЯ ВОРОТАРЯ", anchor="w", fill=MUTED, font=font(8, True), tags="dyn")
        top = max(2.0, max(keeper.history))
        for z, h in enumerate(keeper.history):
            x1, y1 = 36 + (z % 3) * 38, 42 + (z // 3) * 22
            c.create_rectangle(x1, y1, x1 + 34, y1 + 18, outline="",
                               fill=lerp_color("#1c2c36", RED, h / top), tags="dyn")
        if keeper.suspects() is not None:
            c.create_text(158, 52, text="Він помітив", anchor="w", fill=TEXT, font=font(9), tags="dyn")
            c.create_text(158, 68, text="ваш кут!", anchor="w", fill=GOLD, font=font(9, True), tags="dyn")
        else:
            c.create_text(158, 52, text="Вивчає", anchor="w", fill=TEXT, font=font(9), tags="dyn")
            c.create_text(158, 68, text="вас...", anchor="w", fill=MUTED, font=font(9), tags="dyn")

    def draw_step_panel(self):
        # панель кроку внизу праворуч + підказка зліва
        c, g = self.canvas, self.game
        step = STEPS.index(self.state)
        title, hint = STEP_TEXT[self.state]
        round_rect(c, 640, 470, 940, 582, r=16, fill=PANEL, outline=PANEL_LINE, width=2, tags="dyn")
        for i in range(3):
            color = GOLD if i <= step else "#3a4a55"
            c.create_line(752 + i * 20, 488, 766 + i * 20, 488, fill=color, width=3, tags="dyn")
        c.create_text(790, 507, text=title, fill=TEXT, font=title_font(14), tags="dyn")
        c.create_text(790, 528, text=hint, fill=MUTED, font=font(9), tags="dyn")

        if self.state == "power":
            # шкала сили з кольоровими ділянками (межі залежать від рівня)
            x1, x2, y1, y2 = 665, 915, 546, 562
            px = lambda p: x1 + (x2 - x1) * p / 100
            c.create_rectangle(x1, y1, px(g.min_power), y2, fill="#c9a227", outline="", tags="dyn")
            c.create_rectangle(px(g.min_power), y1, px(g.max_safe), y2, fill="#2fb34a", outline="", tags="dyn")
            c.create_rectangle(px(g.max_safe), y1, x2, y2, fill="#c0392b", outline="", tags="dyn")
            c.create_rectangle(x1, y1, x2, y2, outline="white", tags="dyn")
            m = px(self.power)
            c.create_rectangle(m - 3, y1 - 5, m + 3, y2 + 5, fill="white", outline="black", tags="dyn")
            if self.power > g.max_safe:
                round_rect(c, 868, 478, 930, 494, r=6, fill="", outline=RED, tags="dyn")
                c.create_text(899, 486, text="РИЗИК", fill=RED, font=font(7, True), tags="dyn")
        else:
            round_rect(c, 735, 543, 845, 571, r=10, fill=GOLD, outline="", tags="dyn")
            c.create_text(790, 557, text="ЗУПИНИТИ", fill="#1a1405", font=title_font(11), tags="dyn")

        c.create_text(30, 575, text=f"КРОК {step + 1}/3 · {title}", anchor="w", fill=GOLD,
                      font=title_font(12), tags="dyn")

    # ================= підсумок =================
    def show_summary(self):
        self.state = "over"
        g = self.game
        st = g.stats()
        new_record = save_record(g.level, g.goals)
        win = g.is_win()
        self.last_game = (f"{'Перемога' if win else 'Поразка'} {g.goals} : {g.shot_num - g.goals}", g.level)

        c = self.canvas
        self.buttons = []
        self.panel(130, 100, 830, 510, outline=GREEN if win else RED, tag="dyn")
        c.create_text(W / 2, 140, text="ПЕРЕМОГА" if win else "ПОРАЗКА", fill=GREEN if win else RED,
                      font=title_font(30), tags="dyn")
        c.create_text(W / 2, 178, text=g.verdict(), fill=TEXT, font=font(12), tags="dyn")
        c.create_text(300, 240, text=f"{g.goals} : {g.shot_num - g.goals}", fill=TEXT,
                      font=title_font(40), tags="dyn")
        lines = [f"Воротар вгадав зону: {st['guessed']} раз(и)",
                 f"Сейвів: {st['saves']}    Промахів: {st['misses']}",
                 f"Ваша улюблена зона: {ZONE_NAMES[st['favourite']]}"]
        for i, text in enumerate(lines):
            c.create_text(300, 300 + i * 26, text=text, fill=MUTED, font=font(11), tags="dyn")
        if new_record:
            c.create_text(300, 395, text="НОВИЙ РЕКОРД!", fill=GOLD, font=title_font(18), tags="dyn")
        self.draw_shot_map(550, 255)
        self.button(330, 445, 470, 481, "ЩЕ РАЗ", lambda: self.start_game(g.level), tag="dyn")
        self.button(490, 445, 630, 481, "МЕНЮ", self.show_menu, primary=False, tag="dyn")

    def draw_shot_map(self, mx, my):
        # карта ударів: точки — куди цілився гравець, пунктир — де стрибав воротар
        c, k = self.canvas, 0.8
        gw, gh = (GX2 - GX1) * k, (GY2 - GY1) * k
        cw, ch = gw / 3, gh / 2
        c.create_text(mx + gw / 2, my - 45, text="КАРТА УДАРІВ", fill=MUTED, font=font(8, True), tags="dyn")
        c.create_rectangle(mx, my, mx + gw, my + gh, fill="#132530", outline="white", width=2, tags="dyn")
        for i in (1, 2):
            c.create_line(mx + i * cw, my, mx + i * cw, my + gh, fill=PANEL_LINE, tags="dyn")
        c.create_line(mx, my + ch, mx + gw, my + ch, fill=PANEL_LINE, tags="dyn")
        for n, (pt, kz, res) in enumerate(self.shot_log):
            zx, zy = mx + (kz % 3) * cw, my + (kz // 3) * ch
            c.create_rectangle(zx + 3, zy + 3, zx + cw - 3, zy + ch - 3, outline="#2ec4d6",
                               dash=(3, 3), tags="dyn")
            sx, sy = mx + (pt[0] - GX1) * k, my + (pt[1] - GY1) * k
            color = {GOAL: GREEN, SAVE: RED}.get(res, "#dddddd")
            c.create_oval(sx - 7, sy - 7, sx + 7, sy + 7, fill=color, outline="#05080d", tags="dyn")
            c.create_text(sx, sy, text=str(n + 1), fill="#05080d", font=font(7, True), tags="dyn")
        ly = my + gh + 24
        for i, (color, label) in enumerate([(GREEN, "гол"), (RED, "сейв"), ("#dddddd", "промах")]):
            x = mx + i * 70
            c.create_oval(x, ly - 5, x + 10, ly + 5, fill=color, outline="", tags="dyn")
            c.create_text(x + 15, ly, text=label, anchor="w", fill=MUTED, font=font(8), tags="dyn")
        c.create_rectangle(mx, ly + 17, mx + 12, ly + 27, outline="#2ec4d6", dash=(3, 3), tags="dyn")
        c.create_text(mx + 18, ly + 22, text="де стрибав воротар", anchor="w", fill=MUTED, font=font(8), tags="dyn")

    # ================= керування =================
    def on_key(self, event):
        key = event.keysym
        s = self.state
        if s == "menu":
            if key == "Return":
                self.start_game("medium")
        elif s == "levels":
            if key in ("1", "2", "3"):
                self.start_game(LEVEL_ORDER[int(key) - 1])
            elif key == "Escape":
                self.show_menu()
        elif s in ("records", "help"):
            if key in ("Escape", "Return"):
                self.show_menu()
        elif s in STEPS:
            if key == "space":
                self.press()
        elif s == "over":
            if key == "Return":
                self.start_game(self.game.level)
            elif key == "Escape":
                self.show_menu()

    def on_click(self, event):
        if self.state in STEPS:
            self.press()             # у грі клік працює як пробіл
            return
        # шукаємо кнопку під курсором (останні додані — зверху)
        for x1, y1, x2, y2, action in reversed(self.buttons):
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                action()
                return
