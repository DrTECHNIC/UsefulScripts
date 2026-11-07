import re, random


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


def rarity_prefix(rarity: int, mode: int) -> str:
    if rarity is None or mode == 0:
        return ""
    if mode == 1:
        prefix = f"{rarity}★"
    elif mode == 2:
        prefix = "★" * rarity
    else:
        return ""
    rc = RARITY_COLORS.get(rarity)
    return colored(prefix, *rc) if rc else prefix


def format_character(name: str, rarity: int, color: str, mode: int = 0) -> str:
    name_str = colored(name, *color) if color else name
    prefix = rarity_prefix(rarity, mode)
    return f"{prefix} {name_str}" if prefix else name_str


def load_characters(filename: str = ".\\_characters.txt") -> list[tuple[str, str, tuple[int, int, int], int]]:
    pairs = []
    known_elements: list[tuple[str, tuple[int, int, int]]] = []
    current_element = None
    current_color = None
    buffer = ""
    def flush_block(element_name, color, chars_str):
        if element_name == "Другое":
            if not known_elements:
                return
            element_name, color = random.choice(known_elements)
        else:
            known_elements.append((element_name, color))
        for raw in chars_str.split(","):
            raw = raw.strip()
            if not raw:
                continue
            m = re.match(r"^([456])\s*(.+)$", raw)
            if m:
                rarity, name = int(m.group(1)), m.group(2).strip()
            else:
                rarity, name = None, raw
            if name:
                pairs.append((element_name, name, color, rarity))

    with open(filename, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            if ":" in line:
                if current_element is not None:
                    flush_block(current_element, current_color, buffer)
                left, right = line.split(":", 1)
                left = left.strip()
                match = re.match(r"^(.+?)\s*\((\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3})\)$", left)
                if match:
                    current_element = match.group(1).strip()
                    r, g, b = int(match.group(2)), int(match.group(3)), int(match.group(4))
                    current_color = (r, g, b)
                else:
                    current_element = left
                    current_color = None
                buffer = right
            else:
                if current_element is not None:
                    buffer += " " + line.strip()
        if current_element is not None:
            flush_block(current_element, current_color, buffer)

    return pairs


def random_character(filename: str = ".\\_characters.txt") -> str:
    pairs = load_characters(filename)
    if not pairs:
        raise Exception("Список персонажей пуст. Проверьте файл.")
    return random.choice(pairs)


if __name__ == "__main__":
    try:
        element, name, color, rarity = random_character()
        print(format_character(name, int(rarity), color, mode=1))
    except Exception as e:
        print(e)
