# records.py — таблиця рекордів у файлі (найбільше голів на кожному рівні)
import json
import os

# файл лежить у домашній папці користувача, щоб гра могла писати туди навіть після встановлення
RECORDS_FILE = os.path.join(os.path.expanduser("~"), "penalty_records.json")


def load_records(path=RECORDS_FILE):
    # якщо файлу ще немає або він зіпсований — рекордів немає
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_record(level, goals, path=RECORDS_FILE):
    # зберігає результат, якщо він кращий за рекорд. Повертає True, якщо це новий рекорд
    records = load_records(path)
    if goals <= records.get(level, 0):
        return False
    records[level] = goals
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False)
    except OSError:
        pass   # не вдалось записати — гра все одно працює далі
    return True