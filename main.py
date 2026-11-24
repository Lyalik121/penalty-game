# main.py — точка входу: запускає вікно гри
import tkinter as tk
from ui import PenaltyApp


def main():
    root = tk.Tk()
    PenaltyApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()