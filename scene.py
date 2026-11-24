# scene.py — малювання стадіону, поля, воріт, гравця, воротаря і м'яча
import math
import random
from theme import BG, RED, lerp_color, title_font

W, H = 960, 600
GX1, GX2, GY1, GY2 = 340, 620, 232, 330    # ворота на екрані (ліво, право, верх, низ)
BALL_SPOT = (480, 430)                     # точка пенальті
KEEPER_HOME = (480, 326)                   # де стоїть воротар (координата ніг)
GRASS = "#2f7a3e"                          # колір тіней на газоні


def draw_stadium(c, dim=0.0):
    # трибуни: ряди квадратиків-глядачів. dim — наскільки затемнити (для меню)
    rnd = random.Random(7)          # однаковий натовп при кожному малюванні
    for y in range(0, 260, 4):
        c.create_line(0, y, W, y, fill=lerp_color("#05080d", "#0d1620", y / 260))
    fan_colors = ["#e9e9e9", "#e8b84a", "#3b6fd1", "#8fb7d9", "#1d2a38", "#1d2a38", "#26364a"]
    for row in range(11):
        y = 30 + row * 19
        size = 7 + row * 0.6                    # нижні ряди ближче — квадратики більші
        c.create_rectangle(0, y + size + 2, W, y + size + 5, fill="#0a1118", outline="")
        x = rnd.randint(0, 8)
        while x < W:
            color = lerp_color(rnd.choice(fan_colors), BG, dim)
            c.create_rectangle(x, y, x + size, y + size, fill=color, outline="")
            x += size + rnd.randint(3, 9)
    # рекламні щити
    ads = ["ПЕНАЛЬТІ", "НУБіП", "ГОЛ!", "ІПЗ", "ПЕНАЛЬТІ", "НУБіП", "ГОЛ!"]
    bw = W / len(ads)
    for i, text in enumerate(ads):
        x1 = i * bw
        c.create_rectangle(x1 + 2, 238, x1 + bw - 2, 268, fill=lerp_color("#1b2b2a", BG, dim),
                           outline=lerp_color("#2f4a44", BG, dim))
        color = ["#e8b84a", "#4fd18b", "#ff6b5a"][i % 3]
        c.create_text(x1 + bw / 2, 253, text=text, fill=lerp_color(color, BG, dim), font=title_font(14))


def draw_pitch(c, dim=0.0):
    # газон смугами: що ближче до гравця, то смуги ширші (перспектива)
    y, i, step = 268, 0, 10
    while y < H:
        color = "#3f9a4f" if i % 2 == 0 else "#47a858"
        c.create_rectangle(0, y, W, y + step, fill=lerp_color(color, BG, dim), outline="")
        y += step
        step = int(step * 1.18) + 1
        i += 1
    # розмітка: лінія воріт, воротарський і штрафний майданчики
    line = lerp_color("#ffffff", BG, dim)
    c.create_line(0, GY2, W, GY2, fill=line, width=3)
    c.create_polygon(290, GY2, 670, GY2, 720, 380, 240, 380, outline=line, fill="", width=3)
    c.create_polygon(130, GY2, 830, GY2, 960, 470, 0, 470, outline=line, fill="", width=3)
    x, y = BALL_SPOT
    c.create_oval(x - 6, y + 4, x + 6, y + 10, fill=line, outline="")


def draw_goal(c, dx=0):
    # ворота з сіткою; dx — зсув вбік (у меню ворота праворуч)
    x1, x2 = GX1 + dx, GX2 + dx
    c.create_polygon(x1, GY1, x2, GY1, x2 - 14, GY1 - 18, x1 + 14, GY1 - 18, fill="#c9d3d6", outline="")
    for x in range(x1, x2, 8):
        c.create_line(x, GY1, x, GY2, fill="#dfe8e6")
    for y in range(GY1, GY2, 8):
        c.create_line(x1, y, x2, y, fill="#dfe8e6")
    c.create_line(x1, GY2, x1, GY1, x2, GY1, x2, GY2, fill="white", width=7)


def draw_keeper(c, x, y, lean=0.0, hands=-44, tag="dyn"):
    # воротар; (x, y) — точка між ногами, lean від -1 (стрибок вліво) до 1 (вправо),
    # hands — висота рук відносно ніг (-44 — стоїть, -70 — вгору, -22 — вниз).
    # У стрибку тіло нахиляється разом із lean (повертаємо навколо тазу).
    shadow_y = max(y, KEEPER_HOME[1])        # тінь завжди на газоні
    c.create_oval(x - 26, shadow_y - 4, x + 26, shadow_y + 6, fill=GRASS, outline="", tags=tag)
    a = lean * 0.9                           # кут нахилу (радіани)
    ca, sa = math.cos(a), math.sin(a)
    px, py = x, y - 30                       # центр повороту — таз

    def rot(dx, dy):
        # точка (dx, dy) відносно ніг -> координати на екрані з поворотом
        rx, ry = dx, dy + 30
        return px + rx * ca - ry * sa, py + rx * sa + ry * ca

    def box(x1, y1, x2, y2, color):
        pts = []
        for dx, dy in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
            pts += rot(dx, dy)
        c.create_polygon(pts, fill=color, outline="", tags=tag)

    box(-9, -26, -3, 0, "#f1c9a0")           # ноги
    box(3, -26, 9, 0, "#f1c9a0")
    box(-11, -36, 11, -24, "#111111")        # шорти
    box(-13, -64, 13, -36, "#2ec4d6")        # футболка
    # руки тягнуться до точки рукавичок (вона не залежить від нахилу)
    hx, hy = keeper_hands(x, y, lean, hands)
    lx, rx_ = hx - 26, hx + 26
    sl, sr = rot(-12, -60), rot(12, -60)
    c.create_line(sl[0], sl[1], lx, hy, fill="#2ec4d6", width=6, tags=tag)
    c.create_line(sr[0], sr[1], rx_, hy, fill="#2ec4d6", width=6, tags=tag)
    c.create_oval(lx - 6, hy - 6, lx + 6, hy + 6, fill="white", outline="#333333", tags=tag)   # рукавички
    c.create_oval(rx_ - 6, hy - 6, rx_ + 6, hy + 6, fill="white", outline="#333333", tags=tag)
    hcx, hcy = rot(0, -72)                   # голова
    c.create_oval(hcx - 8, hcy - 8.5, hcx + 8, hcy + 8.5, fill="#c98b5b", outline="", tags=tag)
    kx, ky = rot(0, -76)                     # волосся
    c.create_oval(kx - 8, ky - 5, kx + 8, ky + 4, fill="#2b1a10", outline="", tags=tag)


def keeper_hands(x, y, lean, hands=-44):
    # точка між рукавичками воротаря (сюди летить м'яч, коли сейв)
    return x + lean * 30, y + hands


def draw_player(c, x, y, tag="player", swing=0.0):
    # гравець зі спини; (x, y) — точка між ногами
    # swing 0..1 — права нога відводиться назад (розбіг і замах)
    skin, shirt = "#e0b48a", "#2741c9"
    lift, bx = swing * 30, swing * 12
    c.create_oval(x - 50, y - 8, x + 50, y + 10, fill=GRASS, outline="", tags=tag)
    c.create_polygon(x - 28, y - 70, x - 8, y - 70, x - 12, y, x - 30, y, fill=skin, outline="", tags=tag)
    c.create_polygon(x + 8, y - 70, x + 28, y - 70, x + 30 + bx, y - lift, x + 12 + bx, y - lift,
                     fill=skin, outline="", tags=tag)
    c.create_rectangle(x - 30, y - 12, x - 10, y, fill="#f4f4f4", outline="", tags=tag)       # гетри
    c.create_rectangle(x + 10 + bx, y - 12 - lift, x + 30 + bx, y - lift, fill="#f4f4f4", outline="", tags=tag)
    c.create_polygon(x - 34, y - 112, x + 34, y - 112, x + 36, y - 66, x - 36, y - 66,
                     fill="#1b1f3b", outline="", tags=tag)                                     # шорти
    c.create_polygon(x - 42, y - 200, x + 42, y - 200, x + 38, y - 108, x - 38, y - 108,
                     fill=shirt, outline="", tags=tag)                                         # футболка
    c.create_polygon(x - 42, y - 198, x - 58, y - 140, x - 50, y - 136, x - 36, y - 180,
                     fill=shirt, outline="", tags=tag)                                         # рукави
    c.create_polygon(x + 42, y - 198, x + 58, y - 140, x + 50, y - 136, x + 36, y - 180,
                     fill=shirt, outline="", tags=tag)
    c.create_line(x - 54, y - 138, x - 50, y - 100, fill=skin, width=10, tags=tag)             # руки
    c.create_line(x + 54, y - 138, x + 50, y - 100, fill=skin, width=10, tags=tag)
    c.create_text(x, y - 160, text="7", fill="white", font=title_font(30), tags=tag)
    c.create_rectangle(x - 9, y - 214, x + 9, y - 198, fill=skin, outline="", tags=tag)        # шия
    c.create_oval(x - 20, y - 252, x + 20, y - 208, fill=skin, outline="", tags=tag)           # голова
    c.create_arc(x - 21, y - 254, x + 21, y - 214, start=-10, extent=200, fill="#1a120c", outline="", tags=tag)


def draw_ball(c, x, y, r=11, shadow_y=None, tag="dyn"):
    # м'яч із тінню; r зменшується, коли м'яч летить до воріт
    sy = shadow_y if shadow_y is not None else y + r
    c.create_oval(x - r, sy - r * 0.3, x + r, sy + r * 0.3, fill=GRASS, outline="", tags=tag)
    c.create_oval(x - r, y - r, x + r, y + r, fill="white", outline="#555555", tags=tag)
    s = r * 0.4
    c.create_polygon(x - s, y - s * 0.7, x + s, y - s * 0.7, x + s * 1.2, y + s * 0.8, x, y + s * 1.5,
                     x - s * 1.2, y + s * 0.8, fill="#222222", tags=tag)


def draw_crosshair(c, x, y, ball, tag="dyn"):
    # приціл і пунктир від м'яча
    c.create_line(ball[0], ball[1], x, y, fill="#e8f5e9", dash=(4, 6), tags=tag)
    c.create_oval(x - 16, y - 16, x + 16, y + 16, outline=RED, width=3, tags=tag)
    c.create_oval(x - 6, y - 6, x + 6, y + 6, outline="white", width=2, tags=tag)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        c.create_line(x + dx * 10, y + dy * 10, x + dx * 22, y + dy * 22, fill="white", width=2, tags=tag)


def draw_star(c, x, y, r, color, tag=""):
    # п'ятикутна зірка (логотип)
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        a = -math.pi / 2 + i * math.pi / 5
        pts += [x + rr * math.cos(a), y + rr * math.sin(a)]
    c.create_polygon(pts, fill=color, outline="", tags=tag)


def draw_icon(c, icon, x, y, color, tag=""):
    # прості іконки для карток меню
    if icon == "play":
        c.create_polygon(x - 6, y - 9, x + 9, y, x - 6, y + 9, fill=color, tags=tag)
    elif icon == "levels":
        for i, h in enumerate([6, 11, 16]):
            c.create_rectangle(x - 10 + i * 8, y + 8 - h, x - 4 + i * 8, y + 8, fill=color, outline="", tags=tag)
    elif icon == "list":
        for i in range(3):
            c.create_line(x - 9, y - 7 + i * 7, x + 9, y - 7 + i * 7, fill=color, width=3, tags=tag)
    else:
        c.create_text(x, y, text="?", fill=color, font=title_font(16), tags=tag)

