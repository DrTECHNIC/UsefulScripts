def gradient(value_type: str, min_value: any, max_value: any, count: int) -> bool:
    try:
        match value_type:
            case "integer":
                try:
                    min_value = int(min_value)
                    max_value = int(max_value)
                except ValueError:
                    raise Exception("`minValue` and `maxValue` should be integers")
                if not (count >= 0):
                    raise Exception("`count` should be greater than or equal to 0")
                print(integer_calculate(min_value, count, (max_value - min_value) / (count - 1))
                      if count != 1 else [round((min_value + max_value) / 2)])
                return True

            case "color":
                try:
                    min_value = str(min_value)
                    max_value = str(max_value)
                except ValueError:
                    raise Exception("`minValue` and `maxValue` should be strings")
                if not (len(min_value) == len(max_value) == 7):
                    raise Exception("`minValue` and `maxValue` must have same length (7 symbols)")
                if not (count >= 0):
                    raise Exception("`count` should be greater than or equal to 0")
                r, g, b = color_calculate(min_value, max_value, count)
                color_print([color_get(r[i], g[i], b[i]) for i in range(count)])
                return True

            case "string":
                try:
                    min_value = str(min_value)
                    max_value = str(max_value)
                except ValueError:
                    raise Exception("`minValue` and `maxValue` should be strings")
                if not (len(min_value) == len(max_value)):
                    raise Exception("`minValue` and `maxValue` must have same length")
                if not (count >= 0):
                    raise Exception("`count` should be greater than or equal to 0")
                print(string_calculate(min_value, max_value, count))
                return True

            case "boolean":
                try:
                    min_value = bool(min_value)
                    max_value = bool(max_value)
                except ValueError:
                    raise Exception("`minValue` and `maxValue` should be strings")
                if not (count >= 0):
                    raise Exception("`count` should be greater than or equal to 0")
                boolean_print(boolean_calculate(min_value, count, (max_value - min_value) / (count - 1))
                      if count != 1 else [min_value] if min_value == max_value else ["Undefined"])
                return True

            case _:
                raise Exception(f"Unsupported type: {value_type}")
    except Exception as e:
        print(f"\033[31mError:\n    {e}\033[0m")
        return False


def integer_calculate(current: int, count: int, plus: float) -> list[int]:
    array = []
    for _ in range(count):
        array.append(round(current))
        current += plus
    return array

def color_calculate(color_min: str, color_max: str, count: int) -> tuple[list[int], list[int], list[int]]:
    r_min, g_min, b_min = color_parse(color_min)
    r_max, g_max, b_max = color_parse(color_max)
    r_list = integer_calculate(r_min, count, (r_max - r_min) / (count - 1))\
        if count != 1 else [round((r_min + r_max) / 2)]
    g_list = integer_calculate(g_min, count, (g_max - g_min) / (count - 1))\
        if count != 1 else [round((g_min + g_max) / 2)]
    b_list = integer_calculate(b_min, count, (b_max - b_min) / (count - 1))\
        if count != 1 else [round((b_min + b_max) / 2)]
    return r_list, g_list, b_list

def color_parse(color: str) -> tuple[int, int, int]:
    if color[0] != "#":
        raise Exception("Invalid color. Should start with #")
    rgb = color[1:]
    for char in rgb:
        if not ('0' <= char <= '9' or 'A' <= char <= 'F' or 'a' <= char <= 'f'):
            raise Exception("Invalid color. Should contain only symbols 0-9 and A-F or a-f")
    return int(rgb[:2], 16), int(rgb[2:4], 16), int(rgb[4:], 16)

def color_get(red: int, green: int, blue: int) -> str:
    return f"\033[38;2;{red};{green};{blue}m#{hex(red)[2:].zfill(2)}{hex(green)[2:].zfill(2)}{hex(blue)[2:].zfill(2)}\033[0m"

def color_print(color_list: list[str]) -> None:
    print("[", end="")
    for i, item in enumerate(color_list):
        print(item, end="")
        if i < len(color_list) - 1:
            print(", ", end="")
    print("]")

def string_calculate(string_min: str, string_max: str, count: int) -> list[str]:
    s_min = string_parse(string_min)
    s_max = string_parse(string_max)
    array = [integer_calculate(s_min[i], count, (s_max[i] - s_min[i]) / (count - 1))
         if count != 1 else [round((s_min[i] + s_max[i]) / 2)] for i in range(len(s_min))]
    return ["".join(chr(array[j][i]) for j in range(len(s_min))) for i in range(count)]

def string_parse(string: str) -> list[int]:
    return [ord(char) for char in string]

def boolean_calculate(current: float, count: int, plus: float) -> list[str]:
    array = []
    for _ in range(count):
        array.append("Undefined" if False < current < True else bool(current))
        current += plus
    return array

def boolean_print(boolean_list: list[str]) -> None:
    print("[", end="")
    for i, item in enumerate(boolean_list):
        print(item, end="")
        if i < len(boolean_list) - 1:
            print(", ", end="")
    print("]")
