import random, re


RARITY_COLORS = {
    1: (0x8a, 0x94, 0x9c),
    2: (0x6c, 0x98, 0x7c),
    3: (0x65, 0xa1, 0xb6),
    4: (0xb2, 0x8b, 0xc6),
    5: (0xd4, 0xa8, 0x63),
    6: (0xd8, 0x5a, 0x5b),
}


def colored(text: str, r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m{text}\033[0m"


def rarity_prefix(rarity, mode: int) -> str:
    if rarity is None or mode == 0:
        return ""
    if mode == 1:
        prefix = f"{rarity}★"
    elif mode == 2:
        prefix = "★" * int(rarity)
    else:
        return ""
    rc = RARITY_COLORS.get(int(rarity))
    return colored(prefix, *rc) if rc else prefix


def format_weapon(weapon_type: str, name: str, rarity: int, mode: int = 0) -> str:
    prefix = rarity_prefix(rarity, mode)
    display = f"{prefix} {name}" if prefix else name
    return f"{weapon_type}: {display}"


def is_header(line: str) -> bool:
    if ":" not in line:
        return False
    left = line.split(":", 1)[0].strip()
    return bool(left) and not left[0].isdigit()


def _parse_weapon(raw: str):
    raw = raw.strip()
    if not raw:
        return None
    m = re.match(r"^([1-6])\s*(.+)$", raw)
    if m:
        return int(m.group(1)), m.group(2).strip()
    return None, raw


def load_weapons(filename: str = ".\\_weapons.txt") -> list[tuple[str, str, int | None]]:
    pairs = []
    current_type = None
    buffer = ""

    def flush(wtype, wstr):
        if wtype is None:
            return
        for raw in wstr.split(","):
            parsed = _parse_weapon(raw)
            if parsed is None:
                continue
            rarity, name = parsed
            if name:
                pairs.append((wtype, name, rarity))

    with open(filename, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            if is_header(line):
                if current_type is not None:
                    flush(current_type, buffer)
                left, right = line.split(":", 1)
                current_type = left.strip()
                buffer = right
            else:
                if current_type is not None:
                    buffer += " " + line.strip()
        if current_type is not None:
            flush(current_type, buffer)

    return pairs


def random_weapon(filename: str = ".\\_weapons.txt"):
    pairs = load_weapons(filename)
    if not pairs:
        raise Exception("Список оружия пуст. Проверьте файл.")
    return random.choice(pairs)


if __name__ == "__main__":
    try:
        weapon_type, name, rarity = random_weapon()
        print(format_weapon(weapon_type, name, rarity, mode=1))
    except Exception as e:
        print(e)
