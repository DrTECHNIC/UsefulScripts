import sys
import argparse
from typing import List, Tuple
from math import inf as infinity
import math


class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class CurrencyPack:
    def __init__(self, rub: int, vp: int, count: int):
        self.rub = rub
        self.vp = vp
        self.count = count

    def __repr__(self):
        return f"({self.rub} руб -> {self.vp} VP)"

    def __eq__(self, other):
        return self.rub == other.rub and self.vp == other.vp

    def __hash__(self):
        return hash((self.rub, self.vp))


def parse_prices(filename: str) -> List[CurrencyPack]:
    packs = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(";")
            rub_vp_part = parts[0].strip()
            count_part = parts[1].strip() if len(parts) > 1 else "inf"
            rub_str, vp_str = rub_vp_part.split(":")
            rub = int(rub_str.strip())
            vp = int(vp_str.strip())
            if count_part == "inf":
                count = infinity
            else:
                count = int(count_part)
            packs.append(CurrencyPack(rub, vp, count))
    return packs


def rp_to_vp(rp_needed: int) -> int:
    conversion_options = [(1600, 20), (2800, 40), (4800, 80)]
    dp = [float("inf")] * (rp_needed + 1)
    dp[0] = 0
    for i in range(1, rp_needed + 1):
        for vp_cost, rp_gain in conversion_options:
            if i - rp_gain >= 0:
                dp[i] = min(dp[i], dp[i - rp_gain] + vp_cost)
            else:
                dp[i] = min(dp[i], vp_cost)
    return math.ceil(dp[rp_needed])


def find_optimal_combinations(
    packs: List[CurrencyPack],
    target_vp: int,
    existing_vp: int = 0,
    existing_rp: int = 0,
) -> List[Tuple[int, int, List[CurrencyPack]]]:
    adjusted_target = max(0, target_vp - existing_vp)
    if adjusted_target == 0:
        return [(0, 0, [])]
    finite_packs = [p for p in packs if p.count != infinity]
    infinite_packs = [p for p in packs if p.count == infinity]
    max_rub = 50000
    visited = {}
    queue = []
    queue.append((0, 0, []))
    visited[(0, tuple())] = True
    for pack in finite_packs:
        new_queue = []
        for rub, vp, used_packs in queue:
            max_copies = min(pack.count, (max_rub - rub) // pack.rub)
            for copies in range(max_copies + 1):
                if copies == 0:
                    continue
                new_rub = rub + pack.rub * copies
                new_vp = vp + pack.vp * copies
                new_used = used_packs + [pack] * copies
                sorted_used = sorted(new_used, key=lambda x: (x.rub, x.vp))
                state_key = (new_rub, tuple((p.rub, p.vp) for p in sorted_used))
                if state_key not in visited and new_rub <= max_rub:
                    visited[state_key] = True
                    new_queue.append((new_rub, new_vp, sorted_used))
        queue.extend(new_queue)
    if infinite_packs:
        new_queue = []
        for rub, vp, used_packs in queue:
            for pack in infinite_packs:
                copies = 1
                while True:
                    new_rub = rub + pack.rub * copies
                    new_vp = vp + pack.vp * copies
                    if new_rub > max_rub:
                        break
                    new_used = used_packs + [pack] * copies
                    sorted_used = sorted(new_used, key=lambda x: (x.rub, x.vp))
                    state_key = (new_rub, tuple((p.rub, p.vp) for p in sorted_used))
                    if state_key not in visited:
                        visited[state_key] = True
                        new_queue.append((new_rub, new_vp, sorted_used))
                    if new_vp >= adjusted_target:
                        break
                    copies += 1
        queue.extend(new_queue)
    valid_combinations = [
        (rub, vp, packs)
        for rub, vp, packs in queue
        if vp >= adjusted_target and rub <= max_rub
    ]
    return valid_combinations


def filter_top_combinations(
    combinations: List[Tuple[int, int, List[CurrencyPack]]],
) -> List[Tuple[int, int, List[CurrencyPack]]]:
    if not combinations:
        return []
    min_rub = min(rub for rub, _, _ in combinations)
    threshold = max(min_rub + 100, min_rub * 1.1)
    filtered = [(rub, vp, packs) for rub, vp, packs in combinations if rub <= threshold]
    unique_combinations = []
    seen = set()
    for rub, vp, packs in filtered:
        pack_key = tuple(sorted((p.rub, p.vp) for p in packs))
        if (rub, vp, pack_key) not in seen:
            seen.add((rub, vp, pack_key))
            unique_combinations.append((rub, vp, packs))
    unique_combinations.sort(key=lambda x: (x[0], -x[1]))
    filtered_combinations = []
    current_max_vp = -1
    for rub, vp, packs in unique_combinations:
        if vp >= current_max_vp:
            filtered_combinations.append((rub, vp, packs))
            current_max_vp = vp
    return filtered_combinations[:10]


def main():
    if len(sys.argv) >= 3 and not any(arg.startswith("--") for arg in sys.argv[1:3]):
        price_file = sys.argv[1]
        try:
            target_vp = int(sys.argv[2])
        except ValueError:
            print("Ошибка: количество VP должно быть числом")
            return
        try:
            packs = parse_prices(price_file)
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            return
        combinations = find_optimal_combinations(packs, target_vp)
        top_combinations = filter_top_combinations(combinations)
        if not top_combinations:
            print("Не удалось найти подходящие комбинации")
            return
        print(f"Топ-{len(top_combinations)} оптимальных вариантов:")
        print("=" * 50)
        for i, (rub, vp, used_packs) in enumerate(top_combinations, 1):
            print(f"{Colors.CYAN}{Colors.BOLD}Вариант №{i}:{Colors.RESET}")
            print(f"Потрачено рублей: {Colors.RED}{rub}{Colors.RESET}")
            print(f"Получено поинтов: {Colors.GREEN}{vp}{Colors.RESET}")
            sorted_packs = sorted(used_packs, key=lambda p: p.vp)
            vp_list = [pack.vp for pack in sorted_packs]
            print(f"Используемые поинты: {Colors.YELLOW}{vp_list}{Colors.RESET}")
            print("-" * 30)
        return
    parser = argparse.ArgumentParser(description="Оптимальный калькулятор для VALORANT")
    parser.add_argument("--price", required=True, help="Файл с ценами на Valorant Points")
    parser.add_argument("--vp", type=int, help="Требуемое количество VP")
    parser.add_argument("--rp", type=int, help="Требуемое количество RP")
    parser.add_argument("--have-vp", type=int, default=0, help="Уже имеющиеся VP")
    parser.add_argument("--have-rp", type=int, default=0, help="Уже имеющиеся RP")
    args = parser.parse_args()
    target_vp = 0
    if args.vp is not None:
        target_vp += args.vp
    if args.rp is not None:
        rp_needed = max(0, args.rp - args.have_rp)
        if rp_needed > 0:
            vp_for_rp = rp_to_vp(rp_needed)
            target_vp += vp_for_rp
    if target_vp == 0 and args.vp is None and args.rp is None:
        print("Ошибка: необходимо указать либо количество VP, либо количество RP")
        return
    target_vp = max(0, target_vp - args.have_vp)
    if target_vp == 0:
        print("Целевое количество VP уже достигнуто!")
        return
    try:
        packs = parse_prices(args.price)
    except FileNotFoundError:
        print(f"Ошибка: Файл {args.price} не найден")
        return
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        return
    combinations = find_optimal_combinations(packs, target_vp, args.have_vp, args.have_rp)
    top_combinations = filter_top_combinations(combinations)
    if not top_combinations:
        print("Не удалось найти подходящие комбинации")
        return
    print(f"Топ-{len(top_combinations)} оптимальных вариантов:")
    print("=" * 50)
    for i, (rub, vp, used_packs) in enumerate(top_combinations, 1):
        print(f"{Colors.CYAN}{Colors.BOLD}Вариант №{i}:{Colors.RESET}")
        print(f"Потрачено рублей: {Colors.RED}{rub}{Colors.RESET}")
        print(f"Получено поинтов: {Colors.GREEN}{vp}{Colors.RESET}")
        sorted_packs = sorted(used_packs, key=lambda p: p.vp)
        vp_list = [pack.vp for pack in sorted_packs]
        print(f"Используемые поинты: {Colors.YELLOW}{vp_list}{Colors.RESET}")
        print("-" * 30)


if __name__ == "__main__":
    main()
