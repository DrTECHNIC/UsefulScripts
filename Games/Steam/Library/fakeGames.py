from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path


PICTURES = {
    "pot": {
        "title": "Кастрюля на плите",
        "lines": [
            "      (  ) (  ) (  ) (  )",
            "       ) (  ) (  ) (  )",
            "      (  ) (  ) (  ) (  )",
            "    .---------------------.",
            "   /                       \\",
            "  |   ~~~~~~~~~~~~~~~~~~~   |",
            "  |   ~~~~~~~~~~~~~~~~~~~   |",
            "  |   ~~~~~~~~~~~~~~~~~~~   |",
            "   \\                       /",
            "    '---------------------'",
            "         \\___________/",
        ],
    },
    "tv": {
        "title": "Телевизор",
        "lines": [
            "      _______________________________",
            "     |  ___________________________ |",
            "     | |                           ||",
            "     | |      O   O   O            ||",
            "     | |      O   O   O            ||",
            "     | |                           ||",
            "     | |___________________________||",
            "     |_____________________________|",
            "            \\_______________/",
        ],
    },
    "bed": {
        "title": "Кровать",
        "lines": [
            "    ___________________________",
            "   /                           \\",
            "  |  o  o  o  o  o  o  o  o     |",
            "  |___________________________ |",
            "  |                           | |",
            "  |___________________________| |",
            "   |                         |  |",
            "   |_________________________|__|",
            "       ||             ||",
            "       ||             ||",
        ],
    },
    "cat": {
        "title": "Кот",
        "lines": [
            "        /\\_____/\\",
            "       /  o   o  \\",
            "      ( ==  ^  == )",
            "       )         (",
            "      (           )",
            "     ( (  )   (  ) )",
            "    (__(__)___(__)__)",
        ],
    },
    "coffee": {
        "title": "Чашка кофе",
        "lines": [
            "        ( ( (",
            "         ) ) )",
            "        ........",
            "        |      |]",
            "        \\      /",
            "         `----'",
        ],
    },
    "book": {
        "title": "Книга",
        "lines": [
            "      _______",
            "     /|     /|",
            "    / |    / |",
            "   /  |   /  |",
            "  |___|__|___|",
            "  |   |  |   |",
            "  |___|__|___|",
        ],
    },
    "computer": {
        "title": "Компьютер",
        "lines": [
            "      _____________________",
            "     |  _________________  |",
            "     | |                 | |",
            "     | |   > _           | |",
            "     | |                 | |",
            "     | |_________________| |",
            "     |_____________________|",
            "              |  |",
            "           ___|__|___",
            "          |          |",
            "          |__________|",
        ],
    },
    "skull": {
        "title": "Череп",
        "lines": [
            "         _______",
            "        /       \\",
            "       |  X   X  |",
            "       |    ^    |",
            "       |  \\___/  |",
            "        \\_______/",
            "         |_____|",
        ],
    },
    "moon": {
        "title": "Луна",
        "lines": [
            "         ___",
            "       /     \\",
            "      |   *   |",
            "       \\ ___ /",
        ],
    },
    "gamepad": {
        "title": "Геймпад",
        "lines": [
            "     ____________",
            "    /            \\",
            "   |  (+)    (o)  |",
            "   |   o      o   |",
            "    \\____________/",
        ],
    },
    "pizza": {
        "title": "Пицца",
        "lines": [
            "          _____",
            "         /     \\",
            "        /  o o  \\",
            "       / o  o o  \\",
            "      /  o o  o   \\",
            "      \\___________/",
        ],
    },
    "ghost": {
        "title": "Призрак",
        "lines": [
            "       .-''''''-.",
            "     .'          '.",
            "    /   O      O   \\",
            "   :                :",
            "   |                |",
            "   :    .------.    :",
            "    \\  '        '  /",
            "     '.          .'",
            "       '-......-'",
        ],
    },
    "note": {
        "title": "Формула на бумажке",
        "lines": [
            "        ___________",
            "       |           |",
            "       |   J =     |",
            "       |   m*v^2   |",
            "       |  -------  |",
            "       |     2     |",
            "       |___________|",
        ],
    },
}


HEADER = r'''
import sys, os, time, atexit, platform, socket, shutil
import getpass, datetime, uuid, locale
import random, json
from pathlib import Path

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def clear():
    os.system("cls" if os.name == "nt" else "clear")


# ─────────── неблокирующее чтение клавиш ───────────

def _read_key():
    if os.name == "nt":
        try:
            import msvcrt
        except Exception:
            return None
        if not msvcrt.kbhit():
            return None
        b = msvcrt.getch()
        if b in (b"\x00", b"\xe0"):
            if msvcrt.kbhit():
                msvcrt.getch()
            return None
        try:
            return b.decode("latin-1")
        except Exception:
            return None
    else:
        try:
            import select
            if select.select([sys.stdin], [], [], 0)[0]:
                return sys.stdin.read(1)
        except Exception:
            pass
        return None


def _flush_keys():
    if os.name == "nt":
        try:
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getch()
        except Exception:
            pass


# ─────────── статистика времени и настройки в .pt ───────────

STORAGE_KEY = __STORAGE_KEY__   # вшитое при сборке имя-идентификатор


def _sanitize(s):
    out = "".join(c if c.isalnum() or c in " _-" else "_" for c in s)
    out = out.strip(" _-")
    return out or "app"


def _exe_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _pt_path_for(name):
    return _exe_dir() / f"{_sanitize(name)}.pt"


def _read_pt(path):
    """Читает .pt. Понимает новый (JSON) и старый (одно число) форматы."""
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except Exception:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    try:
        return {"total_seconds": float(raw), "legacy": True}
    except Exception:
        return {}


def _default_cfg(default_name):
    return {
        "storage_key": STORAGE_KEY,
        "name": default_name,
        "total_seconds": 0.0,
        "show_title": True,
        "show_picture": True,
        "show_device": True,
        "show_time": True,
        "show_hint": True,
        "picture_key": None,
    }


def _fill_defaults(data, default_name):
    base = _default_cfg(default_name)
    for k, v in base.items():
        data.setdefault(k, v)
    data["storage_key"] = STORAGE_KEY
    return data


def load_or_init(default_name):
    """Найти наш .pt (по storage_key) или подготовить данные нового."""
    base = _exe_dir()

    # 1) поиск по storage_key
    for p in base.glob("*.pt"):
        data = _read_pt(p)
        if data.get("storage_key") == STORAGE_KEY:
            return p, _fill_defaults(data, default_name)

    # 2) миграция: файл с именем APP_TITLE (старый формат — просто число)
    p = base / f"{_sanitize(default_name)}.pt"
    if p.exists():
        data = _read_pt(p)
        return p, _fill_defaults(data, default_name)

    # 3) совсем новый
    return p, _default_cfg(default_name)


class PlaytimeTracker:
    def __init__(self, cfg, cfg_path, autosave=0.5):
        self.cfg = cfg
        self.path = cfg_path
        self.autosave = autosave
        self.total = float(cfg.get("total_seconds", 0.0) or 0.0)
        self.session_start = time.time()
        self.last_save = self.session_start
        self._closed = False
        atexit.register(self._finalize)

    @property
    def display_name(self):
        return self.cfg.get("name", "app")

    def save(self):
        self.cfg["total_seconds"] = round(self.total, 2)
        try:
            self.path.write_text(
                json.dumps(self.cfg, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def session_elapsed(self):
        return time.time() - self.session_start

    def tick(self):
        now = time.time()
        if now - self.last_save >= self.autosave:
            self.total += now - self.last_save
            self.last_save = now
            self.save()

    def _finalize(self):
        if self._closed:
            return
        self._closed = True
        now = time.time()
        if now > self.last_save:
            self.total += now - self.last_save
            self.last_save = now
        self.save()

    def rename(self, new_name):
        now = time.time()
        self.total += now - self.last_save
        self.last_save = now

        old_path = self.path
        new_path = _pt_path_for(new_name)

        # если целевой файл — наш же, сливаем времена
        if new_path != old_path and new_path.exists():
            other = _read_pt(new_path)
            if other.get("storage_key") == STORAGE_KEY:
                self.total += float(other.get("total_seconds", 0.0) or 0.0)

        self.cfg["name"] = new_name
        self.path = new_path
        self.save()

        if old_path != new_path and old_path.exists():
            try:
                old_path.unlink()
            except Exception:
                pass

        self.session_start = time.time()

    @staticmethod
    def fmt(seconds):
        seconds = int(seconds)
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}ч {m:02d}мин {s:02d}с"
        if m:
            return f"{m}мин {s:02d}с"
        return f"{s}с"

    def status_line(self):
        return (f"Сессия: {self.fmt(self.session_elapsed())}"
                f"  |  Всего: {self.fmt(self.total)}")


# ─────────── информация об устройстве ───────────

def _fmt_bytes(n):
    if not n:
        return "0 Б"
    for unit in ("Б", "КБ", "МБ", "ГБ", "ТБ"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} ПБ"


def _get_ram():
    try:
        if sys.platform == "win32":
            import ctypes
            class MS(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            ms = MS()
            ms.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            return ms.ullTotalPhys, ms.ullAvailPhys
        if sys.platform.startswith("linux"):
            info = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    info[k.strip()] = int(v.strip().split()[0]) * 1024
            return info.get("MemTotal", 0), info.get("MemAvailable", 0)
        if sys.platform == "darwin":
            import subprocess as sp
            total = int(sp.check_output(["sysctl", "-n", "hw.memsize"]).strip())
            return total, 0
    except Exception:
        pass
    return 0, 0


def _get_swap():
    try:
        if sys.platform == "win32":
            import ctypes
            class MS(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            ms = MS()
            ms.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            return ms.ullTotalPageFile, ms.ullAvailPageFile
        if sys.platform.startswith("linux"):
            info = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    info[k.strip()] = int(v.strip().split()[0]) * 1024
            return info.get("SwapTotal", 0), info.get("SwapFree", 0)
    except Exception:
        pass
    return 0, 0


def _get_boot_time():
    try:
        if sys.platform == "win32":
            import ctypes
            return time.time() - ctypes.windll.kernel32.GetTickCount64() / 1000.0
        if sys.platform.startswith("linux"):
            with open("/proc/stat") as f:
                for line in f:
                    if line.startswith("btime"):
                        return float(line.split()[1])
        if sys.platform == "darwin":
            import subprocess as sp
            out = sp.check_output(["sysctl", "-n", "kern.boottime"]).decode()
            return float(out.split("sec =")[1].split(",")[0].strip())
    except Exception:
        pass
    return None


def _get_screen():
    try:
        if sys.platform == "win32":
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        if sys.platform.startswith("linux"):
            import subprocess as sp
            out = sp.check_output(["xrandr"]).decode(errors="ignore")
            for line in out.splitlines():
                if " connected" in line and "x" in line:
                    for token in line.split():
                        if "x" in token and token[0].isdigit():
                            w, h = token.split("x")[:2]
                            return int(w), int(h)
    except Exception:
        pass
    return None, None


def _get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "?"


def _get_mac():
    try:
        n = uuid.getnode()
        return ":".join(f"{(n >> e) & 0xff:02X}" for e in range(40, -1, -8))
    except Exception:
        return "?"


def _get_os_full():
    try:
        if sys.platform == "win32":
            rel, ver, csd, _ = platform.win32_ver()
            return f"{rel} {ver} {csd}".strip() or platform.version()
        if sys.platform == "darwin":
            return platform.mac_ver()[0] or platform.version()
        if sys.platform.startswith("linux"):
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return platform.version()


def _get_cpu_freq():
    try:
        if sys.platform.startswith("linux"):
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "cpu MHz" in line:
                        mhz = float(line.split(":")[1].strip())
                        if mhz > 1000:
                            return f"{mhz / 1000:.2f} ГГц"
                        return f"{mhz:.0f} МГц"
        if sys.platform == "darwin":
            import subprocess as sp
            out = sp.check_output(["sysctl", "-n", "hw.cpufrequency"]).decode().strip()
            hz = int(out)
            return f"{hz / 1e9:.2f} ГГц"
    except Exception:
        pass
    return None


def collect_device_info():
    rows = []
    try:
        host = socket.gethostname()
    except Exception:
        host = "?"
    try:
        fqdn = socket.getfqdn()
    except Exception:
        fqdn = ""
    try:
        user = getpass.getuser()
    except Exception:
        user = os.getenv("USERNAME") or os.getenv("USER") or "?"

    rows.append(("Хост",         host))
    if fqdn and fqdn != host:
        rows.append(("FQDN",     fqdn))
    rows.append(("Пользователь", user))
    rows.append(("Дом. папка",   str(Path.home())))

    rows.append(("ОС",           f"{platform.system()} {platform.release()}"))
    rows.append(("Версия ОС",    _get_os_full()))
    rows.append(("Ядро",         platform.version()))
    rows.append(("Архитектура",  platform.machine()))

    rows.append(("CPU",          platform.processor() or "неизвестно"))
    freq = _get_cpu_freq()
    if freq:
        rows.append(("Частота CPU", freq))
    rows.append(("Ядер",         str(os.cpu_count())))

    ram_total, ram_free = _get_ram()
    if ram_total:
        used = ram_total - ram_free
        pct = 100.0 * used / ram_total
        rows.append(("RAM", f"{_fmt_bytes(used)} / {_fmt_bytes(ram_total)} ({pct:.0f}%)"))

    sw_total, sw_free = _get_swap()
    if sw_total:
        rows.append(("Swap", f"{_fmt_bytes(sw_total - sw_free)} / {_fmt_bytes(sw_total)}"))

    try:
        total, used, free = shutil.disk_usage(os.path.abspath(os.sep))
        rows.append(("Диск", f"{_fmt_bytes(free)} свободно из {_fmt_bytes(total)}"))
    except Exception:
        pass

    scr_w, scr_h = _get_screen()
    if scr_w:
        rows.append(("Экран", f"{scr_w} x {scr_h}"))

    rows.append(("IP",  _get_ip()))
    rows.append(("MAC", _get_mac()))

    rows.append(("Время",        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    if time.tzname:
        rows.append(("Часовой пояс", time.tzname[0]))

    boot = _get_boot_time()
    if boot:
        rows.append(("Аптайм", PlaytimeTracker.fmt(time.time() - boot)))

    rows.append(("PID", str(os.getpid())))

    try:
        loc = locale.getlocale()
        lang = loc[0] or "?"
        enc = loc[1] or "?"
        rows.append(("Локаль", f"{lang} / {enc}"))
    except Exception:
        pass

    rows.append(("Python", platform.python_version()))
    if getattr(sys, "frozen", False):
        rows.append(("Файл .exe", Path(sys.executable).name))
    else:
        rows.append(("Скрипт", Path(sys.argv[0]).name))

    return rows


def draw_device_info(rows):
    print("  ── Устройство " + "─" * 48)
    for key, val in rows:
        sval = str(val)
        if len(sval) > 90:
            sval = sval[:87] + "..."
        print(f"    {key:<13}: {sval}")
    print("  " + "─" * 61)


# ─────────── пасхалка: взлом Пентагона ───────────

HACK_STEPS = [
    "Инициализация протокола взлома",
    "Подключение к главному серверу",
    "Сканирование открытых портов",
    "Отпечаток операционной системы",
    "Обход межсетевого экрана",
    "Подбор эксплойта под версию ядра",
    "Инъекция полезной нагрузки",
    "Повышение привилегий до root",
    "SQL-инъекция в базу данных",
    "Извлечение хешей паролей",
    "Brute-force по словарю",
    "Расшифровка файловой системы",
    "Дамп пользовательской базы",
    "Установка бэкдора",
    "Открытие обратного шелла",
    "Подмена цифровой подписи",
    "Удаление логов доступа",
    "Заметание следов",
]

HEX_DIGITS = "0123456789ABCDEF"


def _hexrand(n=32):
    return "".join(random.choice(HEX_DIGITS) for _ in range(n))


def run_hacking_easter_egg(tracker):
    clear()
    print("=" * 64)
    print("  !!! ВНИМАНИЕ !!!")
    print("  ОБНАРУЖЕНА ПОПЫТКА НЕСАНКЦИОНИРОВАННОГО ДОСТУПА")
    print("=" * 64)
    time.sleep(1.0)
    print()
    print("  HACKER TERMINAL v3.14  ::  режим проникновения")
    print("  " + "-" * 62)
    print()
    for i, msg in enumerate(HACK_STEPS, 1):
        print(f"  [{i:02d}/{len(HACK_STEPS)}] {msg}...")
        tracker.tick()
        time.sleep(0.25 + random.random() * 0.35)
        print(f"          [+] OK  ::  {_hexrand(16)}:{_hexrand(16)}")
    print()
    print("  " + "-" * 62)
    print("  ДОСТУП К СИСТЕМЕ ПЕНТАГОНА ПОЛУЧЕН!")
    print("  Поток данных:")
    for _ in range(6):
        print(f"  > {_hexrand(56)}")
        time.sleep(0.10)
    print()
    print("  ... шутка :)")
    print("  Это была пасхалка. Возвращаемся к делу.")
    time.sleep(2.0)


# ─────────── выбор рисунка ───────────

PICTURE_MODE = __PICTURE_MODE__
PICTURE_KEY  = __PICTURE_KEY__
ALL_PICTURES = __ALL_PICTURES__

PICTURE_TITLE = ""
PICTURE = []
CURRENT_PICTURE_KEY = None


def set_picture_by_key(key):
    global PICTURE_TITLE, PICTURE, CURRENT_PICTURE_KEY
    if key and key in ALL_PICTURES:
        data = ALL_PICTURES[key]
        PICTURE_TITLE = data["title"]
        PICTURE = data["lines"]
        CURRENT_PICTURE_KEY = key
    else:
        PICTURE_TITLE, PICTURE, CURRENT_PICTURE_KEY = "", [], None


def pick_random_picture():
    if not ALL_PICTURES:
        set_picture_by_key(None)
        return
    key = random.choice(list(ALL_PICTURES.keys()))
    set_picture_by_key(key)


def resolve_picture():
    if PICTURE_MODE == "none":
        set_picture_by_key(None)
    elif PICTURE_MODE == "fixed":
        set_picture_by_key(PICTURE_KEY)
    elif PICTURE_MODE == "random":
        pick_random_picture()
    else:
        set_picture_by_key(None)


def draw_picture():
    if not PICTURE:
        return
    pad = max(0, 47 - len(PICTURE_TITLE))
    print("  ── Рисунок: " + PICTURE_TITLE + " " + "─" * pad)
    for line in PICTURE:
        print("  " + line)


# ─────────── рендер экрана ───────────

def render_screen(state, tracker, dev_rows, blink):
    clear()
    print("=" * 64)
    if state["show_title"]:
        print(f"  {state['title']}")
        print("=" * 64)
    print()

    if state["show_picture"] and PICTURE:
        draw_picture()
        print()

    if state["show_device"]:
        draw_device_info(dev_rows)
        print()

    if state["show_time"]:
        dots = "." * (blink % 4)
        print(f"  Занят{dots}")
        print()
        print(f"  {tracker.status_line()}")
        print()

    if state["show_hint"]:
        print("  " + "─" * 60)
        print("  0 выход   1 название   2 рисунок   3 показатели")
        print("  4 время   5 переименовать   6 сменить рисунок   \\ подсказка")
        print("  " + "─" * 60)

    print("=" * 64)


# ─────────── переименование ───────────

def prompt_rename(tracker):
    _flush_keys()
    clear()
    print("=" * 64)
    print("  ПЕРЕИМЕНОВАНИЕ ПРИЛОЖЕНИЯ")
    print("=" * 64)
    print()
    print(f"  Текущее имя      : {tracker.display_name}")
    print(f"  Файл со временем : {tracker.path.name}")
    print()
    try:
        raw = input("  Новое имя (Enter — отмена): ")
    except (EOFError, KeyboardInterrupt):
        raw = ""
    _flush_keys()
    return raw.strip()
'''


BODY = r'''

APP_TITLE = __APP_TITLE__

# Вероятность пасхалки при запуске. 0.10 = 10%.
HACK_EASTER_EGG_CHANCE = 0.10


def main():
    cfg_path, cfg = load_or_init(APP_TITLE)
    tracker = PlaytimeTracker(cfg, cfg_path)

    state = {
        "title":        cfg["name"],
        "show_title":   cfg["show_title"],
        "show_picture": cfg["show_picture"],
        "show_device":  cfg["show_device"],
        "show_time":    cfg["show_time"],
        "show_hint":    cfg["show_hint"],
    }

    # рисунок: приоритет — сохранённый вручную
    saved_pic = cfg.get("picture_key")
    if saved_pic and saved_pic in ALL_PICTURES:
        set_picture_by_key(saved_pic)
    else:
        resolve_picture()

    def persist():
        cfg["name"]         = state["title"]
        cfg["show_title"]   = state["show_title"]
        cfg["show_picture"] = state["show_picture"]
        cfg["show_device"]  = state["show_device"]
        cfg["show_time"]    = state["show_time"]
        cfg["show_hint"]    = state["show_hint"]
        cfg["picture_key"]  = CURRENT_PICTURE_KEY
        tracker.save()

    try:
        if random.random() < HACK_EASTER_EGG_CHANCE:
            run_hacking_easter_egg(tracker)

        blink = 0
        dev_rows = collect_device_info()
        last_dev_refresh = time.time()
        last_render = 0.0

        while True:
            key = _read_key()
            if key:
                changed = False
                if key == "0":
                    break
                elif key == "1":
                    state["show_title"] = not state["show_title"];    changed = True
                elif key == "2":
                    state["show_picture"] = not state["show_picture"]; changed = True
                elif key == "3":
                    state["show_device"] = not state["show_device"];   changed = True
                elif key == "4":
                    state["show_time"] = not state["show_time"];       changed = True
                elif key == "5":
                    new_name = prompt_rename(tracker)
                    if new_name:
                        tracker.rename(new_name)
                        state["title"] = new_name
                        changed = True
                    last_render = 0.0
                elif key == "6":
                    pick_random_picture()
                    state["show_picture"] = True
                    changed = True
                elif key == "\\":
                    state["show_hint"] = not state["show_hint"];       changed = True

                if changed:
                    persist()

            now = time.time()
            if now - last_render >= 0.3:
                if now - last_dev_refresh >= 5.0:
                    dev_rows = collect_device_info()
                    last_dev_refresh = now
                render_screen(state, tracker, dev_rows, blink)
                last_render = now
                blink += 1

            tracker.tick()
            time.sleep(0.05)

    except KeyboardInterrupt:
        pass

    print("\nПока!")


if __name__ == "__main__":
    main()
'''


ROOT      = Path(__file__).parent.resolve()
SRC_DIR   = ROOT / "build_src"
BUILD_DIR = ROOT / "build_tmp"
DIST_DIR  = ROOT / "dist"


def _safe_name(name: str) -> str:
    out = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
    out = out.strip(" _-")
    return out or "app"


def _resolve_picture(picture):
    if picture is None:
        return "none", None
    if isinstance(picture, str):
        key = picture.strip().lower()
        if key == "" or key == "none":
            return "none", None
        if key == "random":
            return "random", None
        if picture in PICTURES:
            return "fixed", picture
        if key in PICTURES:
            return "fixed", key
    print(f"Неизвестный рисунок: {picture!r}")
    print(f"Доступные: {', '.join(PICTURES)}, 'random', '' (нет)")
    sys.exit(1)


def ensure_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller не найден, устанавливаю...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def build(app_name: str, picture="") -> Path:
    if not isinstance(app_name, str) or not app_name.strip():
        print("app_name должен быть непустой строкой.")
        sys.exit(1)

    mode, key = _resolve_picture(picture)
    safe = _safe_name(app_name)

    src = HEADER.replace("__PICTURE_MODE__", repr(mode))
    src = src.replace("__PICTURE_KEY__",  repr(key))
    src = src.replace("__ALL_PICTURES__", repr(PICTURES))
    src = src.replace("__STORAGE_KEY__",  repr(safe))
    src += BODY.replace("__APP_TITLE__", repr(app_name))

    ensure_pyinstaller()
    SRC_DIR.mkdir(exist_ok=True)
    BUILD_DIR.mkdir(exist_ok=True)
    DIST_DIR.mkdir(exist_ok=True)

    src_path = SRC_DIR / f"{safe}.py"
    src_path.write_text(src, encoding="utf-8")

    work = BUILD_DIR / safe
    work.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile", "--console",
        "--name", safe,
        "--distpath", str(DIST_DIR),
        "--workpath", str(work),
        "--specpath", str(work),
        str(src_path),
    ]
    subprocess.check_call(cmd)

    suffix = ".exe" if os.name == "nt" else ""
    exe = DIST_DIR / f"{safe}{suffix}"

    if mode == "none":
        pic_report = "— (без рисунка)"
    elif mode == "fixed":
        pic_report = f"{PICTURES[key]['title']}  (всегда)"
    else:
        pic_report = f"случайный из {len(PICTURES)} шт. при каждом запуске"

    print()
    print("Готово!")
    print(f"  Заголовок  : {app_name}")
    print(f"  Рисунок    : {pic_report}")
    print(f"  .exe       : {exe}")
    print(f"  .pt        : {exe.parent / (safe + '.pt')}  (появится после первого запуска)")
    print()
    print("Добавь .exe в Steam:")
    print("  Игры -> Добавить стороннюю игру в мою библиотеку...")
    print("  ПКМ по ярлыку -> Свойства")
    return exe


if __name__ == "__main__":
    build(
        app_name="name", # любой текст — попадёт в заголовок
        picture="random", # "" / None / "none" / "random" / ключ
    )
