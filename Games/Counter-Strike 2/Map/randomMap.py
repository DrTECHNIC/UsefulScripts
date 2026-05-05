import random

def load_maps(filename: str = ".\\_maps.txt") -> list[tuple[str, str]]:
    pairs = list()
    with open(filename, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if ":" not in line:
                continue
            type_part, maps_part = line.split(":", 1)
            map_type = type_part.strip()
            maps_list = maps_part.split(",")
            for map in maps_list:
                map = map.strip()
                if map:
                    pairs.append((map_type, map))
    return pairs

def random_map(filename: str = ".\\_maps.txt") -> str:
    pairs = load_maps(filename)
    if not pairs:
        raise Exception("Список оружия пуст. Проверьте файл.")
    map_type, map_name = random.choice(pairs)
    return f"{map_type}: {map_name}"

if __name__ == "__main__":
    try:
        result = random_map()
        print(result)
    except Exception as e:
        print(e)
