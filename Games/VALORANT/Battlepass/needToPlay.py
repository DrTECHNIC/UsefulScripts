from math import ceil


def parse(filename: str = ".\\_experiences.txt") -> list[int]:
    numbers = []
    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            if not line.strip(): continue
            if ":" in line: values_part = line.split(":", 1)[1]
            else: continue
            for token in values_part.split(","):
                if token.strip(): numbers.append(int(token.strip()))
    return numbers


def calculate(xp_array: list[int], days_left: int, lvl_current: int = 2, xp_lvl_current: int = 0, days_skip: int = 0, count_daily: int = 0, xp_weekly: int = 0, count_weekly: int = 3, xp_bonus: int = 0):
    xp_total = sum(xp_array)
    xp_got = sum(xp_array[: lvl_current - 1]) + xp_lvl_current
    xp_left = xp_total - xp_got
    effective_days = days_left - days_skip
    if effective_days <= 0:
        return xp_left, None
    future_weeks = max(0, ceil(effective_days / 7 - 1))
    rem_weeklies_current = max(0, 3 - count_weekly)
    base_weekly_xp = xp_weekly
    total_weekly_xp = rem_weeklies_current * base_weekly_xp
    for week in range(1, future_weeks + 1):
        total_weekly_xp += 3 * (base_weekly_xp + 500 * week)
    total_dailies = 4 * (effective_days - 1) + (4 - count_daily)
    total_dailies = max(0, total_dailies)
    total_daily_xp = total_dailies * 1000
    xp_deficit = xp_left - total_weekly_xp - total_daily_xp
    if xp_deficit <= 0:
        return xp_left, 0
    daily_raw = xp_deficit / effective_days
    daily_base = daily_raw / (1 + xp_bonus / 100)
    return xp_left, ceil(daily_base)


def rounds_needed(daily_xp: int) -> tuple[int, int]:
    if daily_xp <= 0: return 0, 0
    return ceil(daily_xp / 100), ceil(daily_xp / 300)


if __name__ == "__main__":
    xp_array = parse(".\\_experiences_bp.txt" if input("Выполняешь Боевой пропуск? (д/н) # ").lower() in ("д", "y")
    else ".\\_experiences_bp_mini.txt" if input("Выполняешь Событийный пропуск? (д/н) # ").lower() in ("д", "y")
    else input("Введи путь к файлу с очками опыта # "))
    days_left = int(input("Сколько дней осталось до окончания Пропуска? # "))
    lvl_current = int(input("Какой уровень сейчас улучшается? # "))
    xp_lvl_current = int(input("Сколько опыта уже получено? # "))
    days_skip = int(input("Сколько дней будет пропущено? # "))
    count_daily = int(input("Сколько ежедневных заданий выполнено? # "))
    xp_weekly = int(input("Сколько опыта получается за выполнение еженедельных заданий? # "))
    count_weekly = int(input("Сколько еженедельных заданий выполнено? # "))
    xp_bonus = int(input("Какой бонус опыта действует? # "))
    xp_left, xp_per_day = calculate(xp_array, days_left, lvl_current, xp_lvl_current, days_skip, count_daily, xp_weekly, count_weekly, xp_bonus)
    if xp_per_day is None:
        print("Не осталось дней для игры. Закрыть пропуск невозможно.")
    else:
        print(f"Осталось получить {xp_left} XP.")
        print(f"Для этого ежедневно требуется получать {xp_per_day} XP.")
        played, won = rounds_needed(xp_per_day)
        print(f"Вариант 1: ежедневно играть {played} раундов ({ceil(played / 5)} быстрых игр).")
        print(f"Вариант 2: ежедневно выигрывать {won} раундов ({ceil(won / 5)} быстрых игр).")
