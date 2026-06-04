import re
from json import loads, JSONDecodeError


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
    with open(input_path, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("\r", "").replace("\n", "")
    html = re.sub(r">\s*<", ">\n<", html)
    html = re.sub(r"<!--", "\n<!--", html)
    html = re.sub(r"-->", "-->\n", html)

    lines = html.split("\n")
    indent = 0
    with open(output_path, "w", encoding="utf-8") as out:
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("</") or stripped.startswith("-->"):
                indent = max(0, indent - 1)
            out.write("  " * indent + stripped + "\n")
            if (
                stripped.startswith("<")
                and not stripped.startswith("</")
                and not stripped.startswith("<!--")
                and not stripped.endswith("/>")
                and not stripped.endswith("-->")
            ):
                indent += 1

    print(f"Форматированный HTML сохранён в {output_path}")


def html_add_newlines(input_path: str = ".\\_games.html", output_path: str = ".\\_games_copy.html"):
    with open(input_path, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("\r", "").replace("\n", "")
    html = html.replace(">", ">\n")

    with open(output_path, "w", encoding="utf-8") as out:
        out.write(html)

    print(f"Файл с переносами сохранён в {output_path}")


def html_blocks(input_path: str = ".\\_games.html", output_path: str = ".\\_games_copy.html"):
    with open(input_path, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("\r", "").replace("\n", "")

    block_tags = {
        "div", "table", "tr", "td", "th", "section", "article", "header", "footer", "nav",
        "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6", "p", "form", "fieldset",
        "pre", "blockquote", "aside", "main", "details", "summary", "figure", "figcaption",
    }

    for tag in block_tags:
        html = html.replace(f"<{tag}", f"\n<{tag}")
        html = html.replace(f"</{tag}>", f"</{tag}>\n")

    html = re.sub(r"\n\s*\n", "\n", html)

    with open(output_path, "w", encoding="utf-8") as out:
        out.write(html)

    print(f"Файл с переносами сохранён в {output_path}")


def pdf_hard_parse(input_path: str = ".\\_games.html", output_path: str = ".\\report.txt"):
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    report_entries = []

    line1 = lines[0].strip()
    m = re.search(r"<!DOCTYPE\s+(\w+)", line1, re.IGNORECASE)
    doc_type = m.group(1) if m else "неизвестно"
    report_entries.append(f"Тип документа: {doc_type}")

    line2 = lines[1].strip()
    m = re.search(r"url=\(\d+\)(.*?)\s*-->", line2)
    url = m.group(1).strip()
    report_entries.append(f"Загружено с сайта: {url}")

    line4 = lines[3].strip()
    start_tag = '<script nonce="">'
    end_tag = "</script>"
    start_idx = line4.find(start_tag)
    end_idx = line4.find(end_tag, start_idx)
    script_block = line4[start_idx + len(start_tag) : end_idx]

    data = parse_fourth_string(script_block)

    loader = data["SSR.loaderData"]
    if isinstance(loader, list) and len(loader) > 0:
        first = loader[0]
        profile_lines = ["Профиль:"]
        if "currentUserLinkDetails" in first and "public_data" in first["currentUserLinkDetails"]:
            pub = first["currentUserLinkDetails"]["public_data"]
            steamid = pub.get("steamid", "")
            persona = pub.get("persona_name", "")
            profile_url = pub.get("profile_url", "")
            profile_lines.append(f"Steam ID: {steamid}")
            profile_lines.append(f"Имя: {persona}")
            profile_lines.append(f"URL профиля: {profile_url}")
        else:
            profile_lines.append("(нет данных public_data)")
        if "storeBrowseContext" in first:
            ctx = first["storeBrowseContext"]
            country = ctx.get("country", "")
            language = ctx.get("language", "")
            profile_lines.append(f"Страна: {country}")
            profile_lines.append(f"Язык: {language}")
        else:
            profile_lines.append("Страна/язык: не найдены")
        report_entries.append("\n".join(profile_lines))
    ctx = data["SSR.renderContext"]
    if "queryData" in ctx and "queries" in ctx["queryData"]:
        queries = ctx["queryData"]["queries"]
        if len(queries) > 1:
            wallet_query = queries[1]
            if "state" in wallet_query and "data" in wallet_query["state"]:
                wdata = wallet_query["state"]["data"]
                wallet_lines = ["Кошелёк:"]
                for field in ['has_wallet', 'user_country_code', 'wallet_country_code',
                              'balance', 'delayed_balance', 'has_wallet_in_other_regions',
                              'other_regions', 'formatted_balance', 'formatted_delayed_balance']:
                    val = wdata.get(field, "")
                    wallet_lines.append(f"{field}: {val}")
                report_entries.append("\n".join(wallet_lines))
        if len(queries) >= 10:
            games = []
            for q in queries[9:-1]:
                if "state" in q and "data" in q["state"]:
                    g = q["state"]["data"]
                    if g is not None and isinstance(g, dict):
                        if all(k in g for k in ('id', 'visible', 'name', 'store_url_path', 'appid')):
                            games.append(g)
            if games:
                game_lines = [f"Игры (всего {len(games)}):"]
                for i, g in enumerate(games):
                    num = f"{i + 1:>5}. "
                    game_lines.append(f"{num}{g['name']} (id={g['id']}, appid={g['appid']}, visible={g['visible']})")
                    game_lines.append(f"       URL: https://store.steampowered.com/{g['store_url_path']}")
                report_entries.append("\n".join(game_lines))

    separator = "\n\n" + "—" * 85 + "\n\n"
    report_text = separator.join(report_entries)

    with open(output_path, "w", encoding="utf-8") as out:
        out.write(report_text + "\n")

    print(f"Отчёт сохранён в {output_path}")


def json_extract_value(text, start):
    while start < len(text) and text[start] in " \t\n\r":
        start += 1
    if start >= len(text):
        raise ValueError("Неожиданный конец текста")

    prefix = "JSON.parse("
    if text.startswith(prefix, start):
        inner_start = start + len(prefix)
        while inner_start < len(text) and text[inner_start] in " \t\n\r":
            inner_start += 1
        if inner_start >= len(text) or text[inner_start] != '"':
            raise ValueError("Ожидалась строка в JSON.parse")
        i = inner_start + 1
        while i < len(text):
            if text[i] == "\\":
                i += 2
                continue
            if text[i] == '"':
                json_str = text[inner_start + 1 : i]
                obj = loads('"' + json_str + '"')
                i += 1
                while i < len(text) and text[i] != ")":
                    i += 1
                return obj, i + 1
            i += 1
        raise ValueError("Не найдена закрывающая кавычка в JSON.parse")

    if text[start] not in "[{":
        raise ValueError(f"Ожидался JSON или JSON.parse в позиции {start}")

    open_bracket = text[start]
    close_bracket = "]" if open_bracket == "[" else "}"
    bracket_level = 0
    in_string = False
    escape = False
    i = start
    while i < len(text):
        ch = text[i]
        if escape:
            escape = False
            i += 1
            continue
        if ch == "\\":
            escape = True
            i += 1
            continue
        if ch == '"':
            in_string = not in_string
        elif not in_string:
            if ch == open_bracket:
                bracket_level += 1
            elif ch == close_bracket:
                bracket_level -= 1
                if bracket_level == 0:
                    json_str = text[start : i + 1]
                    obj = loads(json_str)
                    return obj, i + 1
        i += 1
    raise ValueError("Не удалось найти закрывающую скобку для JSON")


def json_deep_parse(obj):
    if isinstance(obj, dict):
        return {k: json_deep_parse(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [json_deep_parse(item) for item in obj]
    elif isinstance(obj, str):
        try:
            parsed = loads(obj)
            return json_deep_parse(parsed)
        except (JSONDecodeError, TypeError):
            return obj
    else:
        return obj


def parse_fourth_string(script_text):
    pattern = re.compile(r"window\.([\w.]+)\s*=\s*")
    parsed = {}
    pos = 0
    while True:
        match = pattern.search(script_text, pos)
        if not match:
            break
        name = match.group(1)
        value_start = match.end()
        try:
            value, new_pos = json_extract_value(script_text, value_start)
        except Exception as e:
            print(f"Ошибка при извлечении {name}: {e}")
            pos = match.end()
            continue

        if name == "SSR.loaderData" and isinstance(value, list):
            try:
                value = [
                    loads(item) if isinstance(item, str) else item for item in value
                ]
            except Exception:
                pass

        value = json_deep_parse(value)
        parsed[name] = value
        pos = new_pos
    return parsed
