import re


def extract_games(input_path: str = ".\\_games.html", output_path: str = ".\\_games.txt"):
    link_pattern = re.compile(
        r'<a\s[^>]*href="(https://store\.steampowered\.com/app/\d+(?:/[^"]*)?)"[^>]*>([^<]+)</a>',
        re.IGNORECASE,
    )

    with open(input_path, "r", encoding="utf-8") as f:
        html = f.read()

    seen_pairs = set()
    games = []

    for m in link_pattern.finditer(html):
        url = m.group(1)
        name = " ".join(m.group(2).strip().split())
        if name == "Store Page":
            continue
        if (url, name) not in seen_pairs:
            seen_pairs.add((url, name))
            games.append((name, url))

    max_len = max(len(name) for name, _ in games) if games else 0

    with open(output_path, "w", encoding="utf-8") as out:
        for name, url in games:
            out.write(f"{name.ljust(max_len)} | {url}\n")

    print(f"Список игр с ссылками сохранён в {output_path}")


if __name__ == "__main__":
    extract_games()
