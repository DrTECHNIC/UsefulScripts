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


def load_characters(filename: str = "..\\Character\\_characters.txt") -> list[tuple[str, str, tuple[int, int, int], int]]:
    characters = []
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
                characters.append((element_name, name, color, rarity))

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

    return characters


def generate_teams(characters, num_teams: int = 1, team_size: int = 4):
    total_needed = num_teams * team_size
    if len(characters) < total_needed:
        raise Exception(
            f"Недостаточно персонажей для {num_teams} команд по {team_size}: "
            f"доступно {len(characters)}, требуется {total_needed}"
        )
    mannequins = [c for c in characters if c[1] in ("Манекен (м)", "Манекен (ж)")]
    others = [c for c in characters if c not in mannequins]
    M = len(mannequins)
    max_mannequins = min(M, num_teams)
    k = random.randint(0, max_mannequins)
    if len(others) < total_needed - k:
        raise Exception(
            f"Невозможно укомплектовать команды: не хватает обычных персонажей "
            f"(нужно {total_needed - k}, есть {len(others)})"
        )
    chosen_mannequins = random.sample(mannequins, k) if k > 0 else []
    chosen_others = random.sample(others, total_needed - k)
    teams = [[] for _ in range(num_teams)]
    mannequin_team_indices = random.sample(range(num_teams), k) if k > 0 else []
    for i, m in enumerate(chosen_mannequins):
        teams[mannequin_team_indices[i]].append(m)
    other_iter = iter(chosen_others)
    for i in range(num_teams):
        while len(teams[i]) < team_size:
            teams[i].append(next(other_iter))
    for team in teams:
        random.shuffle(team)
    return teams


if __name__ == "__main__":
    try:
        all_characters = load_characters()
        teams = generate_teams(all_characters, num_teams=3, team_size=4)
        for i, team in enumerate(teams, start=1):
            members = [
                format_character(name, rarity, color, mode=1)
                for _elem, name, color, rarity in team
            ]
            print(f"Команда {i}: {', '.join(members)}")
    except Exception as e:
        print(f"Ошибка: {e}")
