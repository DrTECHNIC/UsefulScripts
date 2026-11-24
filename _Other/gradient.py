def gradient(value_type: str, min_value: any, max_value: any, count: int = 1, output: bool = True) -> bool:
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
                result = integer_calculate(min_value, max_value, count)\
                    if count != 1 else [round((min_value + max_value) / 2)]
                if output:
                    print(result)

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
                result = [color_get(r[i], g[i], b[i]) for i in range(count)]
                if output:
                    color_print(result)

            case "float":
                try:
                    min_value = float(min_value)
                    max_value = float(max_value)
                except ValueError:
                    raise Exception("`minValue` and `maxValue` should be floats")
                if not (count >= 0):
                    raise Exception("`count` should be greater than or equal to 0")
                result = float_calculate(min_value, max_value, count)\
                    if count != 1 else [((min_value + max_value) / 2)]
                if output:
                    print(result)

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
                result = string_calculate(min_value, max_value, count)
                if output:
                    print(result)

            case "boolean":
                try:
                    min_value = bool(min_value)
                    max_value = bool(max_value)
                except ValueError:
                    raise Exception("`minValue` and `maxValue` should be strings")
                if not (count >= 0):
                    raise Exception("`count` should be greater than or equal to 0")
                result = boolean_calculate(min_value, max_value, count)\
                    if count != 1 else [min_value] if min_value == max_value else ["Undefined"]
                if output:
                    boolean_print(result)

            case _:
                raise Exception(f"Unsupported type: {value_type}")
        return True
    except Exception as e:
        print(f"\033[31mError:\n    {e}\033[0m")
        return False


def integer_calculate(integer_min: int, integer_max: int, count: int) -> list[int]:
    array = []
    if count == 0:
        return array
    plus = (integer_max - integer_min) / (count - 1)
    for _ in range(count):
        array.append(round(integer_min))
        integer_min += plus
    if array[-1] != integer_max:
        array[-1] = integer_max
    return array


def color_calculate(color_min: str, color_max: str, count: int) -> tuple[list[int], list[int], list[int]]:
    r_min, g_min, b_min = color_parse(color_min)
    r_max, g_max, b_max = color_parse(color_max)
    r_list = integer_calculate(r_min, r_max, count)\
        if count != 1 else [round((r_min + r_max) / 2)]
    g_list = integer_calculate(g_min, g_max, count)\
        if count != 1 else [round((g_min + g_max) / 2)]
    b_list = integer_calculate(b_min, b_max, count)\
        if count != 1 else [round((b_min + b_max) / 2)]
    return r_list, g_list, b_list


def color_parse(color: str) -> tuple[int, int, int]:
    if color[0] != "#":
        raise Exception("Invalid color. Should start with #")
    rgb = color[1:]
    for char in rgb:
        if not ("0" <= char <= "9" or "A" <= char.upper() <= "F"):
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


def float_calculate(float_min: float, float_max: float, count: int) -> list[float]:
    array = []
    if count:
        plus = (float_max - float_min) / (count - 1)
        for _ in range(count):
            array.append(float_min)
            float_min += plus
        if array[-1] != float_max:
            array[-1] = float_max
    return array


def string_calculate(string_min: str, string_max: str, count: int) -> list[str]:
    s_min = string_parse(string_min)
    s_max = string_parse(string_max)
    array = [integer_calculate(s_min[i], s_max[i], count)
         if count != 1 else [round((s_min[i] + s_max[i]) / 2)] for i in range(len(s_min))]
    return ["".join(chr(array[j][i]) for j in range(len(s_min))) for i in range(count)]


def string_parse(string: str) -> list[int]:
    return [ord(char) for char in string]


def boolean_calculate(boolean_min: bool, boolean_max: bool, count: int) -> list[str]:
    array = []
    if count:
        plus = (boolean_max - boolean_min) / (count - 1)
        for _ in range(count):
            array.append("Undefined" if False < boolean_min < True else bool(boolean_min))
            boolean_min += plus
        if array[-1] != boolean_max:
            array[-1] = boolean_max
    return array


def boolean_print(boolean_list: list[str]) -> None:
    print("[", end="")
    for i, item in enumerate(boolean_list):
        print(item, end="")
        if i < len(boolean_list) - 1:
            print(", ", end="")
    print("]")
