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
    xp_got = sum(xp_array[:lvl_current - 1]) + xp_lvl_current
    xp_left = xp_total - xp_got
    xp_full_bonus = 1 + xp_bonus / 100
    xp_without_weeklies = xp_left - (3 * max(0, ceil((days_left - days_skip) / 7 - 1)) + (3 - count_weekly)) * xp_weekly * xp_full_bonus
    xp_without_dailies = xp_without_weeklies - (4 * (days_left - days_skip - 1) + (4 - count_daily)) * 1000 * xp_full_bonus
    xp_per_day = xp_without_dailies / (days_left - days_skip)
    return xp_left, max(0, ceil(xp_per_day))


if __name__ == "__main__":
    xp_array = parse(".\\_experiences.txt")
    days_left = int(input("Сколько дней осталось до окончания Боевого пропуска? # "))
    lvl_current = int(input("Какой уровень сейчас улучшается? # "))
    xp_lvl_current = int(input("Сколько опыта уже получено? # "))
    days_skip = int(input("Сколько дней будет пропущено? # "))
    count_daily = int(input("Сколько ежедневных заданий выполнено? # "))
    xp_weekly = int(input("Сколько опыта получается за выполнение еженедельных заданий? # "))
    count_weekly = int(input("Сколько еженедельных заданий выполнено? # "))
    xp_bonus = int(input("Какой бонус опыта действует? # "))
    xp_left, xp_per_day = calculate(xp_array, days_left, lvl_current, xp_lvl_current, days_skip, count_daily, xp_weekly, count_weekly, xp_bonus)
    print(f"Осталось получить {xp_left} XP.")
    print(f"Для этого ежедневно требуется получать {xp_per_day} XP.")
