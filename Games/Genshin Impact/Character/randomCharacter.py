import re, random

def colored(text: str, r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m{text}\033[0m"

def load_characters(filename: str = ".\\_characters.txt") -> list[tuple[str, str, tuple[int,int,int]]]:
    pairs = list()
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
                element_name = match.group(1).strip()
                r, g, b = int(match.group(2)), int(match.group(3)), int(match.group(4))
                color = (r, g, b)
            else:
                element_name = left
                color = None
            if element_name == "Другое":
                if not known_elements:
                    continue
                element_name, color = random.choice(known_elements)
            else:
                known_elements.append((element_name, color))
            characters_list = characters_str.split(",")
            for character in characters_list:
                character = character.strip()
                if character:
                    pairs.append((element_name, character, color))
    return pairs

def random_character(filename: str = ".\\_characters.txt") -> str:
    pairs = load_characters(filename)
    if not pairs:
        raise Exception("Список персонажей пуст. Проверьте файл.")
    return random.choice(pairs)

if __name__ == "__main__":
    try:
        element, name, color = random_character()
        if color:
            print(colored(name, *color))
        else:
            print(name)
    except Exception as e:
        print(e)
