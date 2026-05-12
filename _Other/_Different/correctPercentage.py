def mul(numbers: list[int]) -> int:
    result = 1
    for number in numbers:
        result *= number
    return result


def percentage(iterations: list[int], restrictions: list[int]) -> tuple[int, int]:
    count = 0
    max_count = mul(iterations)
    print(f"0 / {max_count} = 0.00000%")
    count, max_count = _percentage(count, max_count, iterations, restrictions, [])
    print(f"{count} / {max_count} = 100.00000%")
    return count, max_count


def _percentage(count: int, max_count: int, iterations: list[int], restrictions: list[int], indices: list[int]) -> tuple[int, int]:
    size = iterations[0]
    inner_product = mul(iterations[1:])
    for i in range(1, size + 1):
        current_path = indices + [i]
        depth = len(current_path)
        indent = " " * (depth * 3)
        if len(iterations) == 1:
            count += 1
            print(f"{indent}{count} / {max_count} = {count / max_count * 100:.5f}%")
            if i == restrictions[0]:
                max_count -= (size - i)
                return count, max_count
        else:
            print(f"{indent}{count} / {max_count} = {count / max_count * 100:.5f}%")
            count, max_count = _percentage(count, max_count, iterations[1:], restrictions[1:], current_path)
        if i == restrictions[0]:
            max_count -= (size - i) * inner_product
            return count, max_count
    return count, max_count
