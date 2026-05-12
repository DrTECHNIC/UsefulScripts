import random


def load_agents(filename: str = ".\\_agents.txt") -> list[tuple[str, str]]:
    pairs = list()
    with open(filename, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if ":" not in line:
                continue
            type_part, agents_part = line.split(":", 1)
            agent_type = type_part.strip()
            agents_list = agents_part.split(",")
            for agent in agents_list:
                agent = agent.strip()
                if agent:
                    pairs.append((agent_type, agent))
    return pairs


def random_agent(filename: str = ".\\_agents.txt") -> str:
    pairs = load_agents(filename)
    if not pairs:
        raise Exception("Список агентов пуст. Проверьте файл.")
    agent_type, agent_name = random.choice(pairs)
    return f"{agent_type}: {agent_name}"


if __name__ == "__main__":
    try:
        result = random_agent()
        print(result)
    except Exception as e:
        print(e)
