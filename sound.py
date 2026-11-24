# sound.py — прості звуки (winsound на Windows; на інших системах мовчить)
import threading

try:
    import winsound
except ImportError:          # не Windows
    winsound = None

# назва -> послідовність (частота Гц, тривалість мс)
SOUNDS = {
    "kick": [(170, 70)],
    "goal": [(523, 110), (659, 110), (784, 220)],
    "save": [(220, 120), (160, 200)],
    "miss": [(130, 280)],
}


def play(name):
    # грає у окремому потоці, щоб гра не підвисала (Beep блокує виконання)
    if winsound is None or name not in SOUNDS:
        return

    def run():
        try:
            for freq, ms in SOUNDS[name]:
                winsound.Beep(freq, ms)
        except Exception:
            pass             # немає звукової карти — просто без звуку

    threading.Thread(target=run, daemon=True).start()
