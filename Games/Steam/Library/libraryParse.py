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


# DO NOT USE THIS!!!
# THIS CAN CONVERT 26.5 MB TO 8.47 GB
def html_reformat(input_path: str = ".\\_games.html", output_path: str = ".\\_games_copy.html"):
    with open(input_path, 'r', encoding='utf-8') as f:
        html = f.read()

    html = html.replace('\r', '').replace('\n', '')
    html = re.sub(r'>\s*<', '>\n<', html)
    html = re.sub(r'<!--', '\n<!--', html)
    html = re.sub(r'-->', '-->\n', html)

    lines = html.split('\n')
    indent = 0
    with open(output_path, 'w', encoding='utf-8') as out:
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('</') or stripped.startswith('-->'):
                indent = max(0, indent - 1)
            out.write('  ' * indent + stripped + '\n')
            if (stripped.startswith('<') and
                not stripped.startswith('</') and
                not stripped.startswith('<!--') and
                not stripped.endswith('/>') and
                not stripped.endswith('-->')):
                indent += 1

    print(f'Форматированный HTML сохранён в {output_path}')


if __name__ == "__main__":
    extract_games()
