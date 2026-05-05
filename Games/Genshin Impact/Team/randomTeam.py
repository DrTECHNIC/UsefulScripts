import re, random

def colored(text: str, r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m{text}\033[0m"

def load_characters(filename: str = "..\\Character\\_characters.txt") -> list[tuple[str, str, tuple[int,int,int]]]:
    characters = list()
    known_elements: list[tuple[str, tuple[int,int,int]]] = []
    with open(filename, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if ":" not in line:
                continue
            left, right = line.split(":", 1)
            left = left.strip()
            characters_str = right
            match = re.match(r"^(.+?)\s*\((\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3})\)$", left)
            if match:
                element = match.group(1).strip()
                r, g, b = int(match.group(2)), int(match.group(3)), int(match.group(4))
                color = (r, g, b)
            else:
                element = left
                color = None
            if element == "Другое":
                if not known_elements:
                    continue
                element, color = random.choice(known_elements)
            else:
                known_elements.append((element, color))
            for name in characters_str.split(","):
                name = name.strip()
                if name:
                    characters.append((element, name, color))
        return characters

def generate_teams(characters: list[tuple[str, str, tuple[int,int,int]]], num_teams: int = 1, team_size: int = 4) -> list[list[tuple[str, str, tuple[int,int,int]]]]:
    total_needed = num_teams * team_size
    if len(characters) < total_needed:
        raise Exception(f"Недостаточно персонажей для {num_teams} команд по {team_size}: доступно {len(characters)}, требуется {total_needed}")
    mannequins = [c for c in characters if c[1] in ("Манекен (м)", "Манекен (ж)")]
    others = [c for c in characters if c not in mannequins]
    M = len(mannequins)
    max_mannequins = min(M, num_teams)
    k = random.randint(0, max_mannequins)
    if len(others) < total_needed - k:
        raise Exception(f"Невозможно укомплектовать команды: не хватает обычных персонажей (нужно {total_needed - k}, есть {len(others)})")
    chosen_mannequins = random.sample(mannequins, k) if k > 0 else []
    chosen_others = random.sample(others, total_needed - k)
    pool = chosen_mannequins + chosen_others
    random.shuffle(pool)
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
            members = []
            for elem, name, color in team:
                if color:
                    members.append(colored(name, *color))
                else:
                    members.append(name)
            print(f"Команда {i}: {', '.join(members)}")
    except Exception as e:
        print(f"Ошибка: {e}")
