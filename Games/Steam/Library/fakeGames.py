"""
fakeGames.py
============

Собирает консольное приложение в .exe.

Параметр picture:
    ""   | None | "none"   ->  без рисунка
    "random"               ->  при КАЖДОМ запуске .exe — случайный рисунок
    "pot" / "cat" / ...    ->  всегда один и тот же рисунок

В окне выводятся:
    - заголовок (app_name),
    - название рисунка + сам рисунок (если есть),
    - расширенная информация об устройстве,
    - счётчик сессии и общего времени.

Время пишется в файл РЯДОМ С .EXE:
    <имя>.pt
"""

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
import random
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


# ─────────── статистика времени ───────────

def _sanitize(s):
    out = "".join(c if c.isalnum() or c in " _-" else "_" for c in s)
    out = out.strip(" _-")
    return out or "app"


def _stats_path(safe_name):
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent
    return base / f"{safe_name}.pt"


class PlaytimeTracker:
    def __init__(self, name, autosave=5.0):
        self.display_name = name
        self.safe_name = _sanitize(name)
        self.autosave = autosave
        self.path = _stats_path(self.safe_name)
        self.total = 0.0
        self.session_start = time.time()
        self.last_save = self.session_start
        self._closed = False
        self._load()
        atexit.register(self._finalize)

    def _load(self):
        try:
            self.total = float(self.path.read_text(encoding="utf-8").strip())
        except Exception:
            self.total = 0.0

    def _save(self):
        try:
            self.path.write_text(f"{self.total:.2f}", encoding="utf-8")
        except Exception:
            pass

    def session_elapsed(self):
        return time.time() - self.session_start

    def tick(self):
        now = time.time()
        if now - self.last_save >= self.autosave:
            self.total += now - self.last_save
            self.last_save = now
            self._save()

    def _finalize(self):
        if self._closed:
            return
        self._closed = True
        now = time.time()
        if now > self.last_save:
            self.total += now - self.last_save
            self.last_save = now
        self._save()

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
    time.sleep(1.2)
    print()
    print("  HACKER TERMINAL v3.14  ::  режим проникновения")
    print("  " + "-" * 62)
    print()
    for i, msg in enumerate(HACK_STEPS, 1):
        print(f"  [{i:02d}/{len(HACK_STEPS)}] {msg}...")
        tracker.tick()
        time.sleep(0.30 + random.random() * 0.45)
        print(f"          [+] OK  ::  {_hexrand(16)}:{_hexrand(16)}")
    print()
    print("  " + "-" * 62)
    print("  ДОСТУП К СИСТЕМЕ ПЕНТАГОНА ПОЛУЧЕН!")
    print("  Поток данных:")
    for _ in range(6):
        print(f"  > {_hexrand(56)}")
        time.sleep(0.12)
    print()
    print("  ... шутка :)")
    print("  Это была пасхалка. Возвращаемся к делу.")
    time.sleep(2.5)


# ─────────── режим рисунка ───────────
#
# PICTURE_MODE:
#   "none"   — рисунок не выводится
#   "fixed"  — всегда PICTURE_KEY
#   "random" — каждый запуск .exe выбирается новый рисунок
#
# ALL_PICTURES — все рисунки, встроенные в .exe.

PICTURE_MODE = __PICTURE_MODE__
PICTURE_KEY  = __PICTURE_KEY__
ALL_PICTURES = __ALL_PICTURES__

PICTURE_TITLE = ""
PICTURE = []


def resolve_picture():
    """Определить, какой рисунок показывать в этом запуске."""
    global PICTURE_TITLE, PICTURE
    if PICTURE_MODE == "none":
        PICTURE_TITLE, PICTURE = "", []
        return
    if PICTURE_MODE == "fixed":
        data = ALL_PICTURES.get(PICTURE_KEY)
        if not data:
            PICTURE_TITLE, PICTURE = "", []
            return
    elif PICTURE_MODE == "random":
        key = random.choice(list(ALL_PICTURES.keys()))
        data = ALL_PICTURES[key]
    else:
        PICTURE_TITLE, PICTURE = "", []
        return
    PICTURE_TITLE = data["title"]
    PICTURE = data["lines"]


def draw_picture():
    if not PICTURE:
        return
    pad = max(0, 47 - len(PICTURE_TITLE))
    print("  ── Рисунок: " + PICTURE_TITLE + " " + "─" * pad)
    for line in PICTURE:
        print("  " + line)
'''


BODY = r'''

APP_TITLE = __APP_TITLE__

# Вероятность, что при запуске проиграется пасхалка. 0.10 = 10%.
HACK_EASTER_EGG_CHANCE = 0.10


def main():
    tracker = PlaytimeTracker(APP_TITLE)
    try:
        # выбрать рисунок для ЭТОГО запуска
        resolve_picture()

        # ─── пасхалка ───
        if random.random() < HACK_EASTER_EGG_CHANCE:
            run_hacking_easter_egg(tracker)

        # ─── обычный режим ───
        blink = 0
        dev_rows = collect_device_info()
        last_refresh = time.time()
        while True:
            if time.time() - last_refresh >= 5.0:
                dev_rows = collect_device_info()
                last_refresh = time.time()

            clear()
            print("=" * 64)
            print(f"  {APP_TITLE}")
            print("=" * 64)
            print()

            if PICTURE:
                draw_picture()
                print()

            draw_device_info(dev_rows)
            print()

            dots = "." * (blink % 4)
            print(f"  Занят{dots}")
            print()
            print(f"  {tracker.session_line() if hasattr(tracker, 'session_line') else tracker.status_line()}")
            print("  Ctrl+C — выход.")
            print("=" * 64)

            tracker.tick()
            time.sleep(0.5)
            blink += 1
    except KeyboardInterrupt:
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
    """Возвращает (mode, key) для встраивания в .exe.

    mode: "none" | "fixed" | "random"
    key : ключ из PICTURES (только для mode="fixed")
    """
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
    """Собрать .exe.

    app_name — произвольное имя (заголовок в окне).
    picture  — "" / None / "none" / "random" / ключ из PICTURES.
    """
    if not isinstance(app_name, str) or not app_name.strip():
        print("app_name должен быть непустой строкой.")
        sys.exit(1)

    mode, key = _resolve_picture(picture)
    safe = _safe_name(app_name)

    src = HEADER.replace("__PICTURE_MODE__", repr(mode))
    src = src.replace("__PICTURE_KEY__", repr(key))
    src = src.replace("__ALL_PICTURES__", repr(PICTURES))     # весь словарь
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
