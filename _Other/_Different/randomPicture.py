from random import randint


def paint(x: int, y: int):
    for _ in range(y):
        for _ in range(x):
            r = randint(0, 255)
            g = randint(0, 255)
            b = randint(0, 255)
            print(f"\033[48;2;{r};{g};{b}m\033[38;2;{r};{g};{b}m██\033[0m", end="")
        print()


if __name__ == "__main__":
    paint(8, 8)
