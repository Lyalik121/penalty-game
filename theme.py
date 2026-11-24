# theme.py — кольори, шрифти і допоміжні функції малювання (спільні для всього інтерфейсу)
import tkinter.font as tkfont

# ---------- кольори ----------
BG = "#05080d"          # фон (темна ніч над стадіоном)
PANEL = "#0e1a22"       # фон панелей і карток
PANEL_LINE = "#2a3d48"  # рамка панелей
TEXT = "#ffffff"
MUTED = "#8aa0ad"       # сірий текст підписів
GOLD = "#e8b84a"        # головний акцент
GREEN = "#3ddc84"
RED = "#ff5a4f"
BLUE = "#4f8cff"
PURPLE = "#b06cff"

# ---------- шрифти ----------
# назви шрифтів визначаються після створення вікна (pick_fonts), бо до цього tkinter їх не бачить
_font_name = "Arial"
_title_name = "Arial"


def pick_fonts(root):
    # беремо перший шрифт зі списку, який є в системі
    global _font_name, _title_name
    families = set(tkfont.families(root))
    for name in ("Bahnschrift", "Segoe UI", "Fira Sans", "Arial"):
        if name in families:
            _font_name = name
            break
    for name in ("Bahnschrift SemiBold Condensed", "Bahnschrift", "Fira Sans Black", "Arial Black", "Arial"):
        if name in families:
            _title_name = name
            break


def font(size, bold=False):
    # звичайний текст
    return (_font_name, size, "bold") if bold else (_font_name, size)


def title_font(size):
    # заголовки і великі цифри
    return (_title_name, size, "bold")


# ---------- допоміжні функції ----------
def lerp_color(c1, c2, t):
    # колір між c1 і c2: t=0 -> c1, t=1 -> c2
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def round_rect(c, x1, y1, x2, y2, r=14, **kw):
    # прямокутник із заокругленими кутами (многокутник зі згладжуванням)
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)
