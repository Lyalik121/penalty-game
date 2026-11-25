import math
import tkinter as tk

import theme
from sound import play as play_sound
from game import Game, SHOTS_IN_SERIES
from match import Match, SaveTraining, SHOTS_EACH, TRAINING_SHOTS
from goalie import move_towards, clamp01, GOAL_W
from keeper import ZONE_NAMES
from levels import LEVELS, LEVEL_ORDER
from records import load_records, save_record
from shot import GOAL, SAVE, MISS, aim_to_zone
from theme import (PANEL, PANEL_LINE, TEXT, MUTED, GOLD, GREEN, RED, BLUE, PURPLE, BG,
                   font, title_font, round_rect, lerp_color)
from scene import (W, H, GX1, GX2, GY1, GY2, BALL_SPOT, KEEPER_HOME,
                   draw_stadium, draw_pitch, draw_goal, draw_keeper, keeper_hands,
                   draw_player, draw_ball, draw_crosshair, draw_star, draw_icon)

FRAME_MS = 16
AIM_SPEED = 0.018
POWER_SPEED = 2.2
FLIGHT_SPEED = 0.04
RUNUP_FRAMES = 22
PC_RUNUP_FRAMES = 95
HANDS_START = (0.5, 0.6)
PX_PER_M = (GX2 - GX1) / GOAL_W
PLAYER_HOME = (330, 590)
RESULT_FRAMES = 70
BANNER_FRAMES = 50

PLAYER_SHIRT, PC_SHIRT = "#2741c9", "#c0392b"
AI_KEEPER_SHIRT, YOU_KEEPER_SHIRT = "#2ec4d6", "#35c46f"

SHOT_RESULT = {GOAL: ("ГОЛ!", GREEN, "goal"), SAVE: ("СЕЙВ!", RED, "save"), MISS: ("ПРОМАХ!", "#dddddd", "miss")}
SAVE_RESULT = {GOAL: ("ПРОПУСТИЛИ", RED, "save"), SAVE: ("СЕЙВ!", GREEN, "goal"),
               MISS: ("ПОВЗ ВОРОТА!", GREEN, "goal")}

STEPS = ["aim_x", "aim_y", "power"]
STEP_TEXT = {
    "aim_x": ("НАПРЯМОК", "Приціл рухається вліво-вправо · пробіл — зупинити"),
    "aim_y": ("ВИСОТА", "Приціл рухається вгору-вниз · пробіл — зупинити"),
    "power": ("СИЛА", "Зупиніть шкалу в зеленій зоні · пробіл — удар"),
}
GAME_STATES = STEPS + ["runup", "pc_runup", "save_flight", "flying", "result"]

KEEPER_IDLE_HANDS = -44
MODE_NAMES = {"series": "Швидка гра", "match": "Матч", "training": "На воротах"}


def aim_point(ax, ay):
    return GX1 + ax * (GX2 - GX1), GY1 + ay * (GY2 - GY1)


def bounce(value, direction, speed, low, high):
    value += direction * speed
    if value >= high:
        return high, -1
    if value <= low:
        return low, 1
    return value, direction


def lerp(a, b, t):
    return a + (b - a) * t


class PenaltyApp:
    def __init__(self, root):
        self.root = root
        root.title("Пенальті з воротарем, що вчиться")
        root.resizable(False, False)
        theme.pick_fonts(root)
        self.canvas = tk.Canvas(root, width=W, height=H, bg=BG, highlightthickness=0)
        self.canvas.pack()

        self.level = "medium"
        self.mode = "match"
        self.logic = None
        self.buttons = []
        self.last_game = None
        self.state = "menu"
        self.banner_frames = 0

        self.mouse = HANDS_START
        root.bind("<Key>", self.on_key)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_mouse)
        self.show_menu()
        self.tick()

    def clear(self):
        self.canvas.delete("all")
        self.buttons = []

    def panel(self, x1, y1, x2, y2, outline=PANEL_LINE, tag=""):
        round_rect(self.canvas, x1, y1, x2, y2, r=14, fill=PANEL, outline=outline, width=2, tags=tag)

    def button(self, x1, y1, x2, y2, text, action, primary=True, tag=""):
        c = self.canvas
        if primary:
            round_rect(c, x1, y1, x2, y2, r=10, fill=GOLD, outline="", tags=tag)
            c.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=text, fill="#1a1405", font=title_font(11), tags=tag)
        else:
            round_rect(c, x1, y1, x2, y2, r=10, fill=PANEL, outline=PANEL_LINE, width=2, tags=tag)
            c.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=text, fill=TEXT, font=title_font(11), tags=tag)
        self.buttons.append((x1, y1, x2, y2, action))

    def card(self, x, y, icon, title, sub, accent, action):
        c = self.canvas
        self.panel(x, y, x + 270, y + 62)
        c.create_line(x + 2, y + 12, x + 2, y + 50, fill=accent, width=4)
        round_rect(c, x + 14, y + 12, x + 52, y + 50, r=10, fill="", outline=accent, width=2)
        draw_icon(c, icon, x + 33, y + 31, accent)
        c.create_text(x + 66, y + 23, text=title, anchor="w", fill=TEXT, font=title_font(14))
        c.create_text(x + 66, y + 44, text=sub, anchor="w", fill=MUTED, font=font(9))
        c.create_text(x + 250, y + 31, text="→", fill=MUTED, font=font(14))
        self.buttons.append((x, y, x + 270, y + 62, action))

    def show_menu(self):
        self.state = "menu"
        self.clear()
        c = self.canvas
        draw_stadium(c, dim=0.6)
        draw_pitch(c, dim=0.6)
        draw_goal(c, dx=230)
        draw_keeper(c, 710, KEEPER_HOME[1], tag="bg")

        draw_star(c, 46, 40, 14, GOLD)
        c.create_text(72, 32, text="НАВЧАЛЬНИЙ ПРОЄКТ", anchor="w", fill=MUTED, font=font(8, True))
        c.create_text(72, 48, text="ПЕНАЛЬТІ", anchor="w", fill=TEXT, font=title_font(13))
        c.create_line(40, 125, 70, 125, fill=GOLD, width=2)
        c.create_text(80, 125, text="PYTHON + TKINTER · 2026", anchor="w", fill="#c9d3d6", font=font(9, True))
        c.create_text(36, 190, text="ПЕНАЛЬТІ", anchor="w", fill=TEXT, font=title_font(58))
        c.create_text(38, 252, text="ВОРОТАР, ЩО ВЧИТЬСЯ", anchor="w", fill=GOLD, font=title_font(28))
        c.create_text(40, 290, text="Він запам'ятовує, куди ви б'єте. Перехитріть його.",
                      anchor="w", fill="#c9d3d6", font=font(11))

        level_name = LEVELS[self.level]["name"].lower()
        self.card(36, 318, "play", "МАТЧ", "По черзі: б'єте і ловите", GOLD,
                  lambda: self.start_mode("match"))
        self.card(320, 318, "play", "НА ВОРОТАХ", f"Клік мишкою — стрибок · {level_name}", GREEN,
                  lambda: self.start_mode("training"))
        self.card(36, 390, "play", "ШВИДКА ГРА", f"Тільки удари, 5 спроб · {level_name}", BLUE,
                  lambda: self.start_mode("series"))
        self.card(320, 390, "levels", "РІВНІ", "Зараз: " + LEVELS[self.level]["name"], GREEN, self.show_levels)
        self.card(36, 462, "list", "РЕКОРДИ", "Найкращі серії ударів", BLUE, self.show_records)
        self.card(320, 462, "help", "ЯК ГРАТИ", "Приціл, сила, гра мишкою", PURPLE, self.show_help)
        c.create_text(40, 548, text="ENTER — МАТЧ", anchor="w", fill="#c9d3d6", font=font(9, True))

        self.panel(680, 350, 930, 422, outline=GOLD)
        if self.last_game:
            text, mode, level = self.last_game
            c.create_text(698, 368, text="ОСТАННЯ ГРА · " + MODE_NAMES[mode].upper(), anchor="w",
                          fill=MUTED, font=font(8, True))
            c.create_text(698, 392, text=text, anchor="w", fill=TEXT, font=title_font(15))
            c.create_text(698, 410, text=LEVELS[level]["name"] + " рівень", anchor="w", fill=MUTED, font=font(9))
            self.button(840, 376, 916, 402, "РЕВАНШ", lambda: self.start_mode(mode, level))
        else:
            c.create_text(698, 368, text="ПЕРША ГРА", anchor="w", fill=MUTED, font=font(8, True))
            c.create_text(698, 392, text="Воротар ще не знає вас", anchor="w", fill=TEXT, font=title_font(14))
            c.create_text(698, 410, text="Скористайтесь цим!", anchor="w", fill=MUTED, font=font(9))

        self.panel(680, 434, 930, 566)
        c.create_text(698, 452, text="РЕКОРДИ · ШВИДКА ГРА", anchor="w", fill=MUTED, font=font(8, True))
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
        self.buttons = []
        c = self.canvas
        self.panel(230, 100, 730, 530, outline=GOLD)
        c.create_text(W / 2, 135, text=title, fill=TEXT, font=title_font(22))
        self.button(420, 480, 540, 512, "НАЗАД", self.show_menu, primary=False)

    def show_levels(self):
        self.state = "levels"
        self.overlay("ОБЕРІТЬ РІВЕНЬ")
        c = self.canvas
        desc = {"easy": "Воротар і нападник часто діють навмання",
                "medium": "Помічають ваші улюблені кути і стрибки",
                "hard": "Довго пам'ятають, зелена зона сили вужча"}
        for i, (key, color) in enumerate(zip(LEVEL_ORDER, [GREEN, GOLD, RED])):
            y = 170 + i * 92
            selected = key == self.level
            round_rect(c, 270, y, 690, y + 78, r=12, fill="#1d3a2c" if selected else "#132530",
                       outline=color, width=3 if selected else 2)
            c.create_text(300, y + 39, text=str(i + 1), fill=color, font=title_font(26))
            c.create_text(340, y + 28, text=LEVELS[key]["name"].upper() + ("  ✓" if selected else ""),
                          anchor="w", fill=TEXT, font=title_font(16))
            c.create_text(340, y + 52, text=desc[key], anchor="w", fill=MUTED, font=font(10))
            self.buttons.append((270, y, 690, y + 78, lambda k=key: self.choose_level(k)))

    def choose_level(self, level):
        self.level = level
        self.show_menu()

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
        c.create_text(W / 2, 420, text="Найбільше голів за серію в режимі «Швидка гра»",
                      fill=MUTED, font=font(10))

    def show_help(self):
        self.state = "help"
        self.overlay("ЯК ГРАТИ")
        lines = ["Удар: приціл бігає вліво-вправо — пробіл, потім",
                 "вгору-вниз — пробіл, потім шкала сили — пробіл.",
                 "Зелена зона сили — ідеально, червона — ризик промаху.",
                 "",
                 "На воротах: наведіть мишку і клікніть — воротар стрибне.",
                 "Стрибнете зарано — нападник побачить і проб'є в інший бік.",
                 "",
                 "Матч: по 5 ударів по черзі, далі — до першої різниці.",
                 "Воротар і нападник ПК вчаться на ваших звичках!"]
        for i, text in enumerate(lines):
            self.canvas.create_text(262, 180 + i * 30, text=text, anchor="w", fill=TEXT, font=font(12))

    def start_mode(self, mode, level=None):
        if level:
            self.level = level
        self.mode = mode
        if mode == "series":
            self.logic = Game(self.level)
        elif mode == "match":
            self.logic = Match(self.level)
        else:
            self.logic = SaveTraining(self.level)
        self.clear()
        c = self.canvas
        draw_stadium(c)
        draw_pitch(c)
        draw_goal(c)
        self.shot_log = []
        self.pc_log = []
        self.start_turn()

    def start_turn(self):
        self.ball = BALL_SPOT
        self.ball_r = 11
        self.ball_shadow = BALL_SPOT[1] + 11
        self.keeper_x, self.keeper_y = KEEPER_HOME
        self.keeper_lean = 0.0
        self.keeper_hands = KEEPER_IDLE_HANDS
        self.player_pos = PLAYER_HOME
        self.swing = 0.0
        self.result = None
        if self.logic.turn == "shoot":
            self.state = "aim_x"
            self.ax, self.ay = 0.5, 0.5
            self.aim_dir = 1
            self.power, self.power_dir = 0, 1
            self.banner = "ВАШ УДАР"
        else:
            self.state = "pc_runup"
            self.run_t = 0.0
            self.hands = HANDS_START
            self.dive_target = None
            self.dive_early = 0.0
            self.banner = "ВИ НА ВОРОТАХ"
        self.banner_frames = BANNER_FRAMES if self.mode == "match" else 0

    def press(self):
        if self.state == "aim_x":
            self.state = "aim_y"
            self.ay, self.aim_dir = 0.95, -1
        elif self.state == "aim_y":
            self.state = "power"
        elif self.state == "power":
            self.shoot()

    def keeper_target(self, zone):
        col, row = zone % 3, zone // 3
        lean = [-1, 0, 1][col]
        zx = GX1 + (col + 0.5) * (GX2 - GX1) / 3
        if row == 0:
            hands, zy = -70, GY1 + 28
        else:
            hands, zy = -22, GY2 - 26
        ky = min(KEEPER_HOME[1], zy - hands)
        return zx - lean * 30, ky, float(lean), hands

    def ball_target(self, zone, point, result):
        if result == SAVE:
            return keeper_hands(*self.k_to[:3], self.k_to[3])
        tx, ty = point
        if result == MISS:
            col = zone % 3
            if col == 0:
                tx = GX1 - 45
            elif col == 2:
                tx = GX2 + 45
            else:
                ty = GY1 - 35
        return tx, ty

    def prepare_flight(self, keeper_to, ball_to):
        self.t = 0.0
        self.k_from = (self.keeper_x, self.keeper_y, 0.0, KEEPER_IDLE_HANDS)
        self.k_to = keeper_to
        self.b_from = BALL_SPOT
        self.b_to = ball_to

    def shoot(self):
        zone = aim_to_zone(self.ax, self.ay)
        self.result, keeper_zone = self.logic.shoot(zone, self.power)
        self.shot_log.append((aim_point(self.ax, self.ay), keeper_zone, self.result))
        self.k_to = self.keeper_target(keeper_zone)
        self.prepare_flight(self.k_to, self.ball_target(zone, aim_point(self.ax, self.ay), self.result))
        self.state = "runup"
        self.run_t = 0.0

    def update_runup(self):
        self.run_t = min(1.0, self.run_t + 1 / RUNUP_FRAMES)
        r = self.run_t
        self.player_pos = (PLAYER_HOME[0] + 50 * r, PLAYER_HOME[1] - 30 * r)
        self.swing = math.sin(math.pi * r)
        if r >= 1.0:
            self.swing = 0.0
            self.state = "flying"
            play_sound("kick")

    def dive(self):
        if self.dive_target is not None:
            return
        self.dive_target = self.mouse
        if self.state == "pc_runup":
            self.dive_early = (1 - self.run_t) * PC_RUNUP_FRAMES * FRAME_MS / 1000

    def move_hands(self):
        if self.dive_target is None:
            return
        speed = LEVELS[self.logic.level]["dive_speed"]
        self.hands = move_towards(self.hands, self.dive_target, speed * FRAME_MS / 1000)

    def update_pc_runup(self):
        self.run_t = min(1.0, self.run_t + 1 / PC_RUNUP_FRAMES)
        r = self.run_t
        self.player_pos = (PLAYER_HOME[0] + 50 * r, PLAYER_HOME[1] - 30 * r)
        kick = max(0.0, (r - 0.75) / 0.25)
        self.swing = math.sin(math.pi * kick)
        self.move_hands()
        if r >= 1.0:
            self.swing = 0.0
            play_sound("kick")
            self.pc_kick()

    def pc_kick(self):
        k = self.logic.pc_kick(self.hands, self.dive_early)
        self.t = 0.0
        self.flight_step = FRAME_MS / 1000 / k["time"]
        self.b_from = BALL_SPOT
        self.b_to = aim_point(*k["point"])
        self.state = "save_flight"

    def update_save_flight(self):
        self.move_hands()
        self.t = min(1.0, self.t + self.flight_step)
        t = self.t
        (bx1, by1), (bx2, by2) = self.b_from, self.b_to
        self.ball = (lerp(bx1, bx2, t), lerp(by1, by2, t) - 25 * 4 * t * (1 - t))
        self.ball_r = lerp(11, 6, t)
        self.ball_shadow = lerp(BALL_SPOT[1] + 11, GY2 + 2, t)
        if t >= 1.0:
            self.result = self.logic.finish_save(self.hands)
            if self.result == SAVE:
                self.ball = aim_point(*self.hands)
            self.pc_log.append((self.b_to, self.logic.pc_shots[-1][1], self.result))
            self.state = "result"
            self.frames_left = RESULT_FRAMES
            play_sound(SAVE_RESULT[self.result][2])

    def keeper_from_hands(self):
        hx, hy = aim_point(*self.hands)
        lean = max(-1.0, min(1.0, (self.hands[0] - 0.5) * 2.4))
        feet = KEEPER_HOME[1]
        offset = hy - feet
        if offset < -78:
            feet = hy + 78
            offset = -78
        offset = min(offset, -14)
        return hx - lean * 30, feet, lean, offset

    def update_flight(self):
        self.t = min(1.0, self.t + FLIGHT_SPEED)
        t = self.t
        (bx1, by1), (bx2, by2) = self.b_from, self.b_to
        self.ball = (lerp(bx1, bx2, t), lerp(by1, by2, t) - 25 * 4 * t * (1 - t))
        self.ball_r = lerp(11, 6, t)
        self.ball_shadow = lerp(BALL_SPOT[1] + 11, GY2 + 2, t)
        kt = max(0.0, (t - 0.15) / 0.85)
        f, to = self.k_from, self.k_to
        self.keeper_x = lerp(f[0], to[0], kt)
        self.keeper_y = lerp(f[1], to[1], kt)
        self.keeper_lean = lerp(f[2], to[2], kt)
        self.keeper_hands = lerp(f[3], to[3], kt)
        if t >= 1.0:
            self.state = "result"
            self.frames_left = RESULT_FRAMES
            table = SAVE_RESULT if self.is_saving() else SHOT_RESULT
            play_sound(table[self.result][2])

    def tick(self):
        s = self.state
        if s == "aim_x":
            self.ax, self.aim_dir = bounce(self.ax, self.aim_dir, AIM_SPEED, 0.0, 1.0)
        elif s == "aim_y":
            self.ay, self.aim_dir = bounce(self.ay, self.aim_dir, AIM_SPEED, 0.0, 1.0)
        elif s == "power":
            self.power, self.power_dir = bounce(self.power, self.power_dir, POWER_SPEED, 0, 100)
        elif s == "runup":
            self.update_runup()
        elif s == "pc_runup":
            self.update_pc_runup()
        elif s == "save_flight":
            self.update_save_flight()
        elif s == "flying":
            self.update_flight()
        elif s == "result":
            self.frames_left -= 1
            if self.frames_left <= 0:
                if self.logic.is_over():
                    self.show_summary()
                else:
                    self.start_turn()
        if self.banner_frames > 0:
            self.banner_frames -= 1
        if self.state in GAME_STATES:
            self.draw_frame()
        self.root.after(FRAME_MS, self.tick)

    def is_saving(self):
        if self.state in STEPS or self.state == "runup":
            return False
        if self.state in ("pc_runup", "save_flight"):
            return True
        if self.mode == "series":
            return False
        if self.mode == "training":
            return True
        return len(self.logic.pc_shots) == len(self.logic.player_shots)

    def draw_frame(self):
        c = self.canvas
        c.delete("dyn")
        saving = self.is_saving()
        draw_player(c, *self.player_pos, tag="dyn", swing=self.swing,
                    shirt=PC_SHIRT if saving else PLAYER_SHIRT, number="9" if saving else "7")
        if saving:
            kx, ky, lean, hands = self.keeper_from_hands()
            draw_keeper(c, kx, ky, lean, hands=hands, shirt=YOU_KEEPER_SHIRT)
            if self.state in ("pc_runup", "save_flight"):
                self.draw_reach()
        else:
            draw_keeper(c, self.keeper_x, self.keeper_y, self.keeper_lean, hands=self.keeper_hands,
                        shirt=AI_KEEPER_SHIRT)
        if self.state in STEPS:
            draw_crosshair(c, *aim_point(self.ax, self.ay), BALL_SPOT)
        draw_ball(c, *self.ball, r=self.ball_r, shadow_y=self.ball_shadow)
        self.draw_scoreboard()
        self.draw_intuition(saving)
        if self.state in STEPS:
            self.draw_step_panel()
        elif self.state in ("pc_runup", "save_flight"):
            self.draw_goalie_panel()
        if self.state == "result":
            text, color, _ = (SAVE_RESULT if saving else SHOT_RESULT)[self.result]
            c.create_text(W / 2, 175, text=text, fill=color, font=title_font(52), tags="dyn")
            if self.mode == "series" and self.logic.golden_shot and not self.logic.is_over():
                c.create_text(W / 2, 215, text="Нічия! Буде золотий удар", fill=GOLD,
                              font=title_font(16), tags="dyn")
        elif self.banner_frames > 0:
            c.create_text(W / 2, 175, text=self.banner, fill=GOLD, font=title_font(40), tags="dyn")

    def draw_reach(self):
        c = self.canvas
        hx, hy = aim_point(*self.hands)
        r = LEVELS[self.logic.level]["reach"] * PX_PER_M
        c.create_oval(hx - r, hy - r, hx + r, hy + r, outline="white", width=2, dash=(6, 4), tags="dyn")
        mx, my = aim_point(*(self.dive_target or self.mouse))
        c.create_line(mx - 6, my, mx + 6, my, fill=GOLD, width=2, tags="dyn")
        c.create_line(mx, my - 6, mx, my + 6, fill=GOLD, width=2, tags="dyn")

    def scoreboard_frame(self, left, left_sub, left_score, right, right_sub, right_score, label):
        c = self.canvas
        round_rect(c, 270, 14, 690, 74, r=16, fill=PANEL, outline=PANEL_LINE, width=2, tags="dyn")
        c.create_text(292, 36, text=left, anchor="w", fill=TEXT, font=title_font(15), tags="dyn")
        c.create_text(292, 56, text=left_sub, anchor="w", fill=MUTED, font=font(9), tags="dyn")
        c.create_text(428, 44, text=str(left_score), fill=TEXT, font=title_font(28), tags="dyn")
        c.create_text(668, 36, text=right, anchor="e", fill=TEXT, font=title_font(15), tags="dyn")
        c.create_text(668, 56, text=right_sub, anchor="e", fill=MUTED, font=font(9), tags="dyn")
        c.create_text(532, 44, text=str(right_score), fill=TEXT, font=title_font(28), tags="dyn")
        c.create_line(455, 22, 455, 66, fill=PANEL_LINE, tags="dyn")
        c.create_line(505, 22, 505, 66, fill=PANEL_LINE, tags="dyn")
        c.create_text(480, 30, text=label, fill=MUTED, font=font(8, True), tags="dyn")

    def dots(self, y, results, total, good, current):
        c = self.canvas
        step = 7.5 if total <= 6 else 6
        start = 480 - (total - 1) * step / 2
        for i in range(total):
            x = start + i * step
            if i < len(results):
                color = GREEN if results[i] in good else RED
                c.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline="", tags="dyn")
            elif i == len(results) and current:
                c.create_oval(x - 3.5, y - 3.5, x + 3.5, y + 3.5, outline=GOLD, width=2, tags="dyn")
            else:
                c.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#3a4a55", outline="", tags="dyn")

    def draw_scoreboard(self):
        g = self.logic
        level = LEVELS[g.level]["name"].lower()
        busy = self.state in ("runup", "flying", "result")
        if self.mode == "series":
            current = g.shot_num if busy else g.shot_num + 1
            label = "ЗОЛОТИЙ" if g.golden_shot else f"УДАР {min(current, SHOTS_IN_SERIES)}/{SHOTS_IN_SERIES}"
            self.scoreboard_frame("ВИ", "Нападник", g.goals, "ВОРОТАР", "ШІ · " + level,
                                  g.shot_num - g.goals, label)
            total = SHOTS_IN_SERIES + (1 if g.golden_shot else 0)
            self.dots(50, [s[2] for s in g.shots], total, (GOAL,), not busy)
        elif self.mode == "match":
            rnd = len(g.player_shots) + (1 if g.turn == "shoot" and not busy else 0)
            label = "ДОДАТКОВІ" if rnd > SHOTS_EACH else f"РАУНД {max(rnd, 1)}/{SHOTS_EACH}"
            self.scoreboard_frame("ВИ", "Б'єте і ловите", g.player_goals, "ПК", "ШІ · " + level,
                                  g.pc_goals, label)
            total = min(8, max(SHOTS_EACH, len(g.player_shots) + 1, len(g.pc_shots) + 1))
            self.dots(44, [s[2] for s in g.player_shots], total, (GOAL,), not busy and g.turn == "shoot")
            self.dots(57, [s[2] for s in g.pc_shots], total, (SAVE, MISS), not busy and g.turn == "save")
        else:
            n = len(g.pc_shots)
            current = n if busy else n + 1
            self.scoreboard_frame("СЕЙВИ", "Ви на воротах", g.saves, "ГОЛИ", "ПК · " + level,
                                  n - g.saves, f"УДАР {min(current, TRAINING_SHOTS)}/{TRAINING_SHOTS}")
            self.dots(50, [s[2] for s in g.pc_shots], TRAINING_SHOTS, (SAVE, MISS), not busy)

    def draw_intuition(self, saving):
        c = self.canvas
        brain = self.logic.shooter if saving else self.logic.keeper
        title = "НАПАДНИК ВИВЧАЄ ВАС" if saving else "ІНТУЇЦІЯ ВОРОТАРЯ"
        round_rect(c, 20, 14, 230, 92, r=14, fill=PANEL, outline=PANEL_LINE, width=2, tags="dyn")
        c.create_text(36, 30, text=title, anchor="w", fill=MUTED, font=font(8, True), tags="dyn")
        top = max(2.0, max(brain.history))
        for z, h in enumerate(brain.history):
            x1, y1 = 36 + (z % 3) * 38, 42 + (z // 3) * 22
            c.create_rectangle(x1, y1, x1 + 34, y1 + 18, outline="",
                               fill=lerp_color("#1c2c36", RED, h / top), tags="dyn")
        if brain.suspects() is not None:
            line1, line2 = ("Він бачить, куди", "ви стрибаєте!") if saving else ("Він помітив", "ваш кут!")
            c.create_text(158, 52, text=line1, anchor="w", fill=TEXT, font=font(9), tags="dyn")
            c.create_text(158, 68, text=line2, anchor="w", fill=GOLD, font=font(9, True), tags="dyn")
        else:
            c.create_text(158, 52, text="Вивчає", anchor="w", fill=TEXT, font=font(9), tags="dyn")
            c.create_text(158, 68, text="вас...", anchor="w", fill=MUTED, font=font(9), tags="dyn")

    def draw_step_panel(self):
        c, g = self.canvas, self.logic
        step = STEPS.index(self.state)
        title, hint = STEP_TEXT[self.state]
        round_rect(c, 640, 470, 940, 582, r=16, fill=PANEL, outline=PANEL_LINE, width=2, tags="dyn")
        for i in range(3):
            color = GOLD if i <= step else "#3a4a55"
            c.create_line(752 + i * 20, 488, 766 + i * 20, 488, fill=color, width=3, tags="dyn")
        c.create_text(790, 507, text=title, fill=TEXT, font=title_font(14), tags="dyn")
        c.create_text(790, 528, text=hint, fill=MUTED, font=font(9), tags="dyn")
        if self.state == "power":
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

    def draw_goalie_panel(self):
        c = self.canvas
        round_rect(c, 640, 470, 940, 582, r=16, fill=PANEL, outline=PANEL_LINE, width=2, tags="dyn")
        c.create_text(790, 494, text="ВИ НА ВОРОТАХ", fill=TEXT, font=title_font(14), tags="dyn")
        if self.dive_target is None:
            line1, line2 = "Наведіть мишку і клікніть — стрибок", "Зарано — нападник побачить!"
        else:
            line1, line2 = "Стрибок!", "Коло — куди дотягуються руки"
        c.create_text(790, 516, text=line1, fill=MUTED, font=font(9), tags="dyn")
        c.create_text(790, 536, text=line2, fill=GOLD, font=font(10, True), tags="dyn")
        left = 1 - self.run_t if self.state == "pc_runup" else 0
        c.create_rectangle(665, 554, 915, 564, fill="#3a4a55", outline="", tags="dyn")
        c.create_rectangle(665, 554, 665 + 250 * left, 564, fill=GOLD, outline="", tags="dyn")
        label = "НАПАДНИК РОЗБІГАЄТЬСЯ" if self.state == "pc_runup" else "УДАР!"
        c.create_text(30, 575, text=label, anchor="w", fill=GOLD, font=title_font(12), tags="dyn")

    def show_summary(self):
        self.state = "over"
        g = self.logic
        win = g.is_win()
        c = self.canvas
        self.buttons = []

        if self.mode == "series":
            st = g.stats()
            title = "ПЕРЕМОГА" if win else "ПОРАЗКА"
            score = f"{g.goals} : {g.shot_num - g.goals}"
            lines = [f"Воротар вгадав зону: {st['guessed']} раз(и)",
                     f"Сейвів: {st['saves']}    Промахів: {st['misses']}",
                     f"Ваша улюблена зона: {ZONE_NAMES[st['favourite']]}"]
            new_record = save_record(g.level, g.goals)
        elif self.mode == "match":
            st = g.stats()
            title = "ПЕРЕМОГА" if win else "ПОРАЗКА"
            score = f"{g.player_goals} : {g.pc_goals}"
            lines = [f"Ваших голів: {g.player_goals} з {len(g.player_shots)}",
                     f"Відбито ударів ПК: {st['saves']}    ПК повз: {st['pc_misses']}",
                     f"Ви найчастіше тягнулися: {ZONE_NAMES[st['favourite_dive']]}"]
            new_record = False
        else:
            title = "ТРЕНУВАННЯ"
            score = f"{g.saves} з {TRAINING_SHOTS}"
            saves = sum(1 for s in g.pc_shots if s[2] == SAVE)
            lines = [f"Відбито: {saves}    Повз ворота: {g.saves - saves}",
                     f"Пропущено: {TRAINING_SHOTS - g.saves}"]
            new_record = False
        self.last_game = (f"{title.capitalize()} {score}", self.mode, g.level)

        self.panel(130, 100, 830, 510, outline=GREEN if win else RED, tag="dyn")
        c.create_text(W / 2, 140, text=title, fill=GREEN if win else RED, font=title_font(30), tags="dyn")
        c.create_text(W / 2, 178, text=g.verdict(), fill=TEXT, font=font(12), tags="dyn")
        c.create_text(300, 240, text=score, fill=TEXT, font=title_font(40), tags="dyn")
        for i, text in enumerate(lines):
            c.create_text(300, 300 + i * 26, text=text, fill=MUTED, font=font(11), tags="dyn")
        if new_record:
            c.create_text(300, 395, text="НОВИЙ РЕКОРД!", fill=GOLD, font=title_font(18), tags="dyn")

        if self.mode == "training":
            self.draw_shot_map(550, 255, self.pc_log, "КАРТА УДАРІВ ПК",
                               {GOAL: RED, SAVE: GREEN}, ["гол ПК", "сейв", "повз"], "де були ваші руки")
        else:
            self.draw_shot_map(550, 255, self.shot_log, "КАРТА ВАШИХ УДАРІВ",
                               {GOAL: GREEN, SAVE: RED}, ["гол", "сейв", "промах"], "де стрибав воротар")
        self.button(330, 445, 470, 481, "ЩЕ РАЗ", lambda: self.start_mode(self.mode), tag="dyn")
        self.button(490, 445, 630, 481, "МЕНЮ", self.show_menu, primary=False, tag="dyn")

    def draw_shot_map(self, mx, my, log, title, colors, labels, dashed_label):
        c, k = self.canvas, 0.8
        gw, gh = (GX2 - GX1) * k, (GY2 - GY1) * k
        cw, ch = gw / 3, gh / 2
        c.create_text(mx + gw / 2, my - 45, text=title, fill=MUTED, font=font(8, True), tags="dyn")
        c.create_rectangle(mx, my, mx + gw, my + gh, fill="#132530", outline="white", width=2, tags="dyn")
        for i in (1, 2):
            c.create_line(mx + i * cw, my, mx + i * cw, my + gh, fill=PANEL_LINE, tags="dyn")
        c.create_line(mx, my + ch, mx + gw, my + ch, fill=PANEL_LINE, tags="dyn")
        for n, (pt, kz, res) in enumerate(log):
            zx, zy = mx + (kz % 3) * cw, my + (kz // 3) * ch
            c.create_rectangle(zx + 3, zy + 3, zx + cw - 3, zy + ch - 3, outline="#2ec4d6",
                               dash=(3, 3), tags="dyn")
            sx = min(max(mx + (pt[0] - GX1) * k, mx), mx + gw)
            sy = min(max(my + (pt[1] - GY1) * k, my), my + gh)
            color = colors.get(res, "#dddddd")
            c.create_oval(sx - 7, sy - 7, sx + 7, sy + 7, fill=color, outline="#05080d", tags="dyn")
            c.create_text(sx, sy, text=str(n + 1), fill="#05080d", font=font(7, True), tags="dyn")
        ly = my + gh + 24
        legend = [(colors[GOAL], labels[0]), (colors[SAVE], labels[1]), ("#dddddd", labels[2])]
        for i, (color, label) in enumerate(legend):
            x = mx + i * 70
            c.create_oval(x, ly - 5, x + 10, ly + 5, fill=color, outline="", tags="dyn")
            c.create_text(x + 15, ly, text=label, anchor="w", fill=MUTED, font=font(8), tags="dyn")
        c.create_rectangle(mx, ly + 17, mx + 12, ly + 27, outline="#2ec4d6", dash=(3, 3), tags="dyn")
        c.create_text(mx + 18, ly + 22, text=dashed_label, anchor="w", fill=MUTED, font=font(8), tags="dyn")

    def on_key(self, event):
        key = event.keysym
        s = self.state
        if s == "menu":
            if key == "Return":
                self.start_mode("match")
        elif s == "levels":
            if key in ("1", "2", "3"):
                self.choose_level(LEVEL_ORDER[int(key) - 1])
            elif key == "Escape":
                self.show_menu()
        elif s in ("records", "help"):
            if key in ("Escape", "Return"):
                self.show_menu()
        elif s in STEPS:
            if key == "space":
                self.press()
        elif s in ("pc_runup", "save_flight"):
            if key == "space":
                self.dive()
        elif s == "over":
            if key == "Return":
                self.start_mode(self.mode)
            elif key == "Escape":
                self.show_menu()

    def on_click(self, event):
        if self.state in STEPS:
            self.press()
            return
        if self.state in ("pc_runup", "save_flight"):
            self.on_mouse(event)
            self.dive()
            return
        for x1, y1, x2, y2, action in reversed(self.buttons):
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                action()
                return

    def on_mouse(self, event):
        self.mouse = (clamp01((event.x - GX1) / (GX2 - GX1)), clamp01((event.y - GY1) / (GY2 - GY1)))