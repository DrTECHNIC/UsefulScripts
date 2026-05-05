import random

def load_weapons(filename: str = ".\\_weapons.txt") -> list[tuple[str, str]]:
    pairs = list()
    with open(filename, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if ":" not in line:
                continue
            type_part, weapons_part = line.split(":", 1)
            weapon_type = type_part.strip()
            weapons_list = weapons_part.split(",")
            for weapon in weapons_list:
                weapon = weapon.strip()
                if weapon:
                    pairs.append((weapon_type, weapon))
    return pairs

def random_weapon(filename: str = ".\\_weapons.txt") -> str:
    pairs = load_weapons(filename)
    if not pairs:
        raise Exception("Список оружия пуст. Проверьте файл.")
    weapon_type, weapon_name = random.choice(pairs)
    return f"{weapon_type}: {weapon_name}"

if __name__ == "__main__":
    try:
        result = random_weapon()
        print(result)
    except Exception as e:
        print(e)
