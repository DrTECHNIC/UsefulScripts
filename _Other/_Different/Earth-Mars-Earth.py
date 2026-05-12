EARTH_DAY_SEC = 24 * 3600                # 86400 секунд в земных сутках
MARS_SOL_SEC = 24 * 3600 + 39 * 60 + 35  # 88775 секунд в одном соле


def earth_to_mars(earth_days=0, earth_hours=0, earth_minutes=0, earth_seconds=0):
    total_earth_days = (earth_days + earth_hours / 24 + earth_minutes / 1440 + earth_seconds / 86400)
    total_earth_seconds = total_earth_days * EARTH_DAY_SEC
    total_sols = total_earth_seconds / MARS_SOL_SEC
    mars_sols = int(total_sols)
    remainder_sol = total_sols - mars_sols
    mars_hours = int(remainder_sol * 24)
    remainder_hour = remainder_sol * 24 - mars_hours
    mars_minutes = int(remainder_hour * 60)
    remainder_minute = remainder_hour * 60 - mars_minutes
    mars_seconds = round(remainder_minute * 60)
    if mars_seconds == 60: mars_seconds, mars_minutes = 0, mars_minutes + 1
    if mars_minutes == 60: mars_minutes, mars_hours = 0, mars_hours + 1
    if mars_hours == 24: mars_hours, mars_sols = 0, mars_sols + 1
    return mars_sols, mars_hours, mars_minutes, mars_seconds


def mars_to_earth(mars_sols=0, mars_hours=0, mars_minutes=0, mars_seconds=0):
    total_mars_days = (mars_sols + mars_hours / 24 + mars_minutes / 1440 + mars_seconds / 86400)
    total_earth_seconds = total_mars_days * MARS_SOL_SEC
    earth_days = int(total_earth_seconds // EARTH_DAY_SEC)
    remainder_sec = total_earth_seconds % EARTH_DAY_SEC
    earth_hours = int(remainder_sec // 3600)
    remainder_sec -= earth_hours * 3600
    earth_minutes = int(remainder_sec // 60)
    earth_seconds = round(remainder_sec % 60)
    if earth_seconds == 60: earth_seconds, earth_minutes = 0, earth_minutes + 1
    if earth_minutes == 60: earth_minutes, earth_hours = 0, earth_hours + 1
    if earth_hours == 24: earth_hours, earth_days = 0, earth_days + 1
    return earth_days, earth_hours, earth_minutes, earth_seconds


def ask_time_components(planet):
    if planet == "Земля":  unit = "дней"
    elif planet == "Марс": unit = "солов"
    else: return None
    try:
        d = input(f"Количество {unit} (Enter=0): ").strip()
        d = float(d) if d else 0.0
        h = input("Часы (Enter=0): ").strip()
        h = float(h) if h else 0.0
        m = input("Минуты (Enter=0): ").strip()
        m = float(m) if m else 0.0
        s = input("Секунды (Enter=0): ").strip()
        s = float(s) if s else 0.0
        return d, h, m, s
    except ValueError:
        print("Ошибка: введите числа.")
        return None


if __name__ == "__main__":
    print("Конвертер времени Земля ↔ Марс\n")
    print("Выберите направление:")
    print("1 — Земля → Марс")
    print("2 — Марс → Земля")
    choice = input("Ваш выбор (1/2): ").strip()
    if choice == "1":
        comp = ask_time_components("Земля")
        if comp is None: exit()
        eD, eh, em, es = comp
        sols, mh, mm, ms = earth_to_mars(eD, eh, em, es)
        total_earth_days = eD + eh / 24 + em / 1440 + es / 86400
        total_sols = total_earth_days * EARTH_DAY_SEC / MARS_SOL_SEC
        print(f"\n{eD} дн {eh} ч {em} мин {es} с (земных) = {total_sols:.4f} солов")
        print(f"Разложение: {sols} солов, {mh} ч, {mm} мин, {ms} с (марсианских)")
    elif choice == "2":
        comp = ask_time_components("Марс")
        if comp is None: exit()
        mS, mh, mm, ms = comp
        edays, eh, em, es = mars_to_earth(mS, mh, mm, ms)
        total_mars_days = mS + mh / 24 + mm / 1440 + ms / 86400
        total_earth_days = total_mars_days * MARS_SOL_SEC / EARTH_DAY_SEC
        print(f"\n{mS} солов {mh} ч {mm} мин {ms} с (марсианских) = {total_earth_days:.4f} земных суток")
        print(f"Разложение: {edays} сут, {eh} ч, {em} мин, {es} с (земных)")
    else:
        print("Неверный выбор.")
