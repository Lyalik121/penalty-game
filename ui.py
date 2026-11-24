# ui.py — графічна версія гри на tkinter (вся логіка — у game.py)
import tkinter as tk
from game import Game, SHOTS_IN_SERIES
from keeper import ZONE_NAMES
from levels import LEVELS, LEVEL_ORDER
from records import load_records, save_record
from shot import GOAL, SAVE, MISS

# ---------- розміри й координати ----------
W, H = 600, 480
GX1, GY1, GX2, GY2 = 120, 70, 480, 250     # кути воріт
COL_W = (GX2 - GX1) / 3                    # ширина однієї зони
ROW_H = (GY2 - GY1) / 2                    # висота однієї зони
BALL_START = (300, 375)                    # точка пенальті
KEEPER_START = (300, GY2 - 32)             # воротар стоїть по центру
BALL_R = 13
BAR_X1, BAR_Y1, BAR_X2, BAR_Y2 = 150, 418, 450, 436   # шкала сили
ANIM_STEPS = 20                            # кадрів в анімації удару

GRASS_1, GRASS_2 = "#2e8b57", "#339966"    # дві смуги газону
RESULT_TEXT = {GOAL: "ГОЛ!", SAVE: "СЕЙВ!", MISS: "ПРОМАХ!"}
RESULT_COLOR = {GOAL: "#7CFC00", SAVE: "#ff4d4d", MISS: "#dddddd"}


def zone_rect(zone):
    # прямокутник зони на екрані: рядок = zone // 3, стовпчик = zone % 3
    row, col = zone // 3, zone % 3
    x1 = GX1 + col * COL_W
    y1 = GY1 + row * ROW_H
    return x1, y1, x1 + COL_W, y1 + ROW_H


def zone_center(zone):
    x1, y1, x2, y2 = zone_rect(zone)
    return (x1 + x2) / 2, (y1 + y2) / 2


def zone_at(x, y):
    # яка зона під курсором (або None, якщо клік поза воротами)
    if not (GX1 <= x < GX2 and GY1 <= y < GY2):
        return None
    col = int((x - GX1) // COL_W)
    row = int((y - GY1) // ROW_H)
    return row * 3 + col


def power_x(power):
    # координата x на шкалі для сили 0..100
    return BAR_X1 + (BAR_X2 - BAR_X1) * power / 100


class PenaltyApp:
    def __init__(self, root):
        self.root = root
        root.title("Пенальті з воротарем, що вчиться")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=W, height=H, highlightthickness=0)
        self.canvas.pack()

        self.game = Game()
        self.selected = 4        # обрана зона (спочатку низ-центр)
        self.power = 0
        self.power_dir = 1       # шкала рухається вгору (1) чи вниз (-1)
        self.state = "menu"      # menu / aim / power / flying / result / over

        self.draw_field()
        self.create_items()
        self.setup_power_bar()

        root.bind("<Key>", self.on_key)
        self.canvas.bind("<Button-1>", self.on_click)
        self.show_menu()

    # ================= малювання =================
    def draw_field(self):
        c = self.canvas
        # газон смугами
        stripe = 60
        for i in range(W // stripe + 1):
            color = GRASS_1 if i % 2 == 0 else GRASS_2
            c.create_rectangle(i * stripe, 0, (i + 1) * stripe, H, fill=color, outline="")
        # лінія воріт і штрафний майданчик
        c.create_line(0, GY2, W, GY2, fill="white", width=2)
        c.create_rectangle(70, GY2, 530, 300, outline="white", width=2)
        c.create_rectangle(20, GY2, 580, 400, outline="white", width=2)
        # точка пенальті
        x, y = BALL_START
        c.create_oval(x - 4, y - 4, x + 4, y + 4, fill="white", outline="")
        # сітка воріт
        for x in range(GX1, GX2 + 1, 15):
            c.create_line(x, GY1, x, GY2, fill="#b8d8c4")
        for y in range(GY1, GY2 + 1, 15):
            c.create_line(GX1, y, GX2, y, fill="#b8d8c4")
        # штанги і перекладина
        c.create_line(GX1, GY2, GX1, GY1, GX2, GY1, GX2, GY2, fill="white", width=8)

    def create_items(self):
        c = self.canvas
        # межі зон (видно тільки під час прицілювання)
        self.zone_lines = [
            c.create_line(GX1 + COL_W, GY1, GX1 + COL_W, GY2, fill="yellow", dash=(4, 4)),
            c.create_line(GX1 + 2 * COL_W, GY1, GX1 + 2 * COL_W, GY2, fill="yellow", dash=(4, 4)),
            c.create_line(GX1, GY1 + ROW_H, GX2, GY1 + ROW_H, fill="yellow", dash=(4, 4)),
        ]
        self.highlight = c.create_rectangle(0, 0, 0, 0, outline="yellow", width=3)

        # воротар: руки, тулуб, голова, рукавички
        self.k_arm_l = c.create_line(0, 0, 0, 0, fill="#ff8c00", width=7)
        self.k_arm_r = c.create_line(0, 0, 0, 0, fill="#ff8c00", width=7)
        self.k_body = c.create_rectangle(0, 0, 0, 0, fill="#ff8c00", outline="black")
        self.k_head = c.create_oval(0, 0, 0, 0, fill="#f1c27d", outline="black")
        self.k_glove_l = c.create_oval(0, 0, 0, 0, fill="white", outline="black")
        self.k_glove_r = c.create_oval(0, 0, 0, 0, fill="white", outline="black")

        # м'яч з плямою
        self.ball = c.create_oval(0, 0, 0, 0, fill="white", outline="black", width=2)
        self.ball_spot = c.create_oval(0, 0, 0, 0, fill="black", outline="")

        # шкала сили: три кольорові ділянки, рамка і бігунок
        self.bar_weak = c.create_rectangle(0, 0, 0, 0, fill="#c9a227", outline="")
        self.bar_good = c.create_rectangle(0, 0, 0, 0, fill="#2fb34a", outline="")
        self.bar_risk = c.create_rectangle(0, 0, 0, 0, fill="#c0392b", outline="")
        c.create_rectangle(BAR_X1, BAR_Y1, BAR_X2, BAR_Y2, outline="white", width=2)
        self.bar_marker = c.create_rectangle(0, 0, 0, 0, fill="white", outline="black")
        self.lbl_weak = c.create_text(0, BAR_Y2 + 12, text="слабко", fill="white", font=("Arial", 9))
        self.lbl_good = c.create_text(0, BAR_Y2 + 12, text="ідеально", fill="white", font=("Arial", 9))
        self.lbl_risk = c.create_text(0, BAR_Y2 + 12, text="ризик", fill="white", font=("Arial", 9))

        # тексти
        self.hud = c.create_text(10, 10, anchor="nw", fill="white", font=("Arial", 14, "bold"))
        self.msg = c.create_text(W / 2, 320, fill="white", font=("Arial", 12))
        self.big = c.create_text(W / 2, 160, fill="white", font=("Arial", 44, "bold"))

    def place_keeper(self, x, y, lean=0.0):
        # lean від -1 (стрибок вліво) до 1 (вправо): руки тягнуться в бік стрибка
        c = self.canvas
        c.coords(self.k_body, x - 16, y - 20, x + 16, y + 32)
        c.coords(self.k_head, x - 11 + lean * 8, y - 42, x + 11 + lean * 8, y - 20)
        gy = y - 28 - abs(lean) * 12                  # у стрибку руки вище
        lx, rx = x - 32 + lean * 22, x + 32 + lean * 22
        c.coords(self.k_arm_l, x - 14, y - 14, lx, gy)
        c.coords(self.k_arm_r, x + 14, y - 14, rx, gy)
        c.coords(self.k_glove_l, lx - 8, gy - 8, lx + 8, gy + 8)
        c.coords(self.k_glove_r, rx - 8, gy - 8, rx + 8, gy + 8)

    def place_ball(self, x, y, r=BALL_R):
        self.canvas.coords(self.ball, x - r, y - r, x + r, y + r)
        s = r * 0.4
        self.canvas.coords(self.ball_spot, x - s, y - s, x + s, y + s)

    def setup_power_bar(self):
        # ділянки шкали залежать від рівня (min_power і max_safe)
        lo, hi = self.game.min_power, self.game.max_safe
        c = self.canvas
        c.coords(self.bar_weak, BAR_X1, BAR_Y1, power_x(lo), BAR_Y2)
        c.coords(self.bar_good, power_x(lo), BAR_Y1, power_x(hi), BAR_Y2)
        c.coords(self.bar_risk, power_x(hi), BAR_Y1, BAR_X2, BAR_Y2)
        c.coords(self.lbl_weak, power_x(lo / 2), BAR_Y2 + 12)
        c.coords(self.lbl_good, power_x((lo + hi) / 2), BAR_Y2 + 12)
        c.coords(self.lbl_risk, power_x((hi + 100) / 2), BAR_Y2 + 12)

    def update_power_bar(self):
        x = power_x(self.power)
        self.canvas.coords(self.bar_marker, x - 3, BAR_Y1 - 5, x + 3, BAR_Y2 + 5)

    def update_hud(self):
        g = self.game
        level = LEVELS[g.level]["name"]
        if g.golden_shot and not g.is_over():
            shot = "ЗОЛОТИЙ УДАР"
        else:
            shot = f"Удар {min(g.shot_num + 1, SHOTS_IN_SERIES)}/{SHOTS_IN_SERIES}"
        self.canvas.itemconfig(self.hud, text=f"{shot}   Голи: {g.goals}   Рівень: {level}")

    def show_zones(self, visible):
        state = "normal" if visible else "hidden"
        for item in self.zone_lines + [self.highlight]:
            self.canvas.itemconfig(item, state=state)

    def show_panel(self, lines):
        # темна панель поверх гри (меню або підсумок)
        c = self.canvas
        c.delete("panel")
        c.create_rectangle(60, 40, 540, 450, fill="#123524", outline="white", width=2, tags="panel")
        y = 80
        for text, size, bold in lines:
            font = ("Arial", size, "bold") if bold else ("Arial", size)
            c.create_text(W / 2, y, text=text, fill="white", font=font, tags="panel")
            y += size + 18

    # ================= стани гри =================
    def show_menu(self):
        self.state = "menu"
        records = load_records()
        lines = [("Пенальті з воротарем,", 24, True), ("що вчиться", 24, True), ("", 6, False),
                 ("Оберіть рівень:", 14, False)]
        for i, key in enumerate(LEVEL_ORDER, start=1):
            best = records.get(key, 0)
            lines.append((f"{i} — {LEVELS[key]['name']}   (рекорд: {best})", 14, True))
        lines += [("", 6, False),
                  ("Стрілки або мишка — вибір зони", 11, False),
                  ("Пробіл — шкала сили, ще раз пробіл — удар", 11, False),
                  ("Воротар запам'ятовує, куди ви б'єте!", 11, False)]
        self.show_panel(lines)

    def start_game(self, level):
        self.game.set_level(level)
        self.setup_power_bar()
        self.canvas.delete("panel")
        self.start_shot()

    def start_shot(self):
        self.state = "aim"
        self.power = 0
        self.power_dir = 1
        self.place_ball(*BALL_START)
        self.place_keeper(*KEEPER_START)
        self.canvas.itemconfig(self.big, text="")
        self.show_zones(True)
        self.canvas.coords(self.highlight, *zone_rect(self.selected))
        self.update_power_bar()
        self.update_hud()
        # підказка, що воротар почав читати гравця
        text = "Оберіть зону стрілками або мишкою, потім пробіл"
        if self.game.keeper.suspects() is not None:
            text = "Воротар щось запідозрив...\n" + text
        self.canvas.itemconfig(self.msg, text=text)

    def start_power(self):
        self.state = "power"
        self.canvas.itemconfig(self.msg, text="Пробіл — зупинити шкалу сили")
        self.tick_power()

    def tick_power(self):
        # шкала бігає 0 -> 100 -> 0, поки гравець не натисне пробіл
        if self.state != "power":
            return
        self.power += 3 * self.power_dir
        if self.power >= 100:
            self.power, self.power_dir = 100, -1
        elif self.power <= 0:
            self.power, self.power_dir = 0, 1
        self.update_power_bar()
        self.root.after(20, self.tick_power)

    def shoot(self):
        self.state = "flying"
        self.show_zones(False)
        self.canvas.itemconfig(self.msg, text="")
        result, keeper_zone = self.game.shoot(self.selected, self.power)
        self.last_result = result

        # куди летить воротар і в який бік нахиляється
        self.keeper_target = zone_center(keeper_zone)
        self.keeper_target = (self.keeper_target[0], self.keeper_target[1] + 8)
        self.lean = [-1, 0, 1][keeper_zone % 3]

        # куди летить м'яч
        if result == SAVE:
            self.ball_target = (self.keeper_target[0] + self.lean * 22, self.keeper_target[1] - 28)
        elif result == MISS:
            x, y = zone_center(self.selected)
            col = self.selected % 3
            if col == 0:
                x = GX1 - 45                                # повз лівої штанги
            elif col == 2:
                x = GX2 + 45                                # повз правої штанги
            else:
                y = GY1 - 35                                # над перекладиною
            self.ball_target = (x, y)
        else:
            self.ball_target = zone_center(self.selected)
        self.animate(0)

    def animate(self, step):
        # плавно рухаємо м'яч і воротаря від старту до цілі
        t = step / ANIM_STEPS
        bx = BALL_START[0] + (self.ball_target[0] - BALL_START[0]) * t
        by = BALL_START[1] + (self.ball_target[1] - BALL_START[1]) * t
        # воротар реагує трохи пізніше за м'яч
        kt = max(0.0, (t - 0.2) / 0.8)
        kx = KEEPER_START[0] + (self.keeper_target[0] - KEEPER_START[0]) * kt
        ky = KEEPER_START[1] + (self.keeper_target[1] - KEEPER_START[1]) * kt
        self.place_ball(bx, by, BALL_R * (1 - 0.35 * t))   # м'яч "віддаляється"
        self.place_keeper(kx, ky, self.lean * kt)
        if step < ANIM_STEPS:
            self.root.after(25, self.animate, step + 1)
        else:
            self.show_result()

    def show_result(self):
        self.state = "result"
        r = self.last_result
        self.canvas.itemconfig(self.big, text=RESULT_TEXT[r], fill=RESULT_COLOR[r])
        self.update_hud()
        if self.game.is_over():
            self.root.after(1300, self.show_summary)
        else:
            if self.game.golden_shot:
                self.canvas.itemconfig(self.msg, text="Нічия! Буде золотий удар")
            self.root.after(1300, self.start_shot)

    def show_summary(self):
        self.state = "over"
        g = self.game
        st = g.stats()
        new_record = save_record(g.level, g.goals)
        lines = [(g.verdict(), 18, True),
                 (f"Голів: {g.goals} з {g.shot_num}", 16, False),
                 ("", 4, False),
                 (f"Воротар вгадав зону: {st['guessed']} раз(и)", 12, False),
                 (f"Сейвів: {st['saves']}   Промахів: {st['misses']}", 12, False),
                 (f"Ваша улюблена зона: {ZONE_NAMES[st['favourite']]}", 12, False)]
        if new_record:
            lines.append(("НОВИЙ РЕКОРД!", 16, True))
        lines += [("", 4, False),
                  ("Enter — ще раз    Esc — меню", 12, True)]
        self.show_panel(lines)

    # ================= керування =================
    def on_key(self, event):
        key = event.keysym
        if self.state == "menu":
            if key in ("1", "2", "3"):
                self.start_game(LEVEL_ORDER[int(key) - 1])
        elif self.state == "aim":
            row, col = self.selected // 3, self.selected % 3
            if key == "Left" and col > 0:
                col -= 1
            elif key == "Right" and col < 2:
                col += 1
            elif key == "Up" and row > 0:
                row -= 1
            elif key == "Down" and row < 1:
                row += 1
            elif key == "space":
                self.start_power()
                return
            self.selected = row * 3 + col
            self.canvas.coords(self.highlight, *zone_rect(self.selected))
        elif self.state == "power" and key == "space":
            self.shoot()
        elif self.state == "over":
            if key == "Return":
                self.start_game(self.game.level)
            elif key == "Escape":
                self.show_menu()

    def on_click(self, event):
        # клік по зоні = вибір зони і одразу перехід до сили
        if self.state != "aim":
            return
        zone = zone_at(event.x, event.y)
        if zone is not None:
            self.selected = zone
            self.canvas.coords(self.highlight, *zone_rect(zone))
            self.start_power()