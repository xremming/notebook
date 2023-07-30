from random import randint


def roll(sides: int) -> int:
    """Roll a dice with `sides` sides."""

    if sides <= 0:
        raise ValueError("Number of sides must be greater than 0")

    return randint(1, sides)


def rolln(count: int, sides: int) -> list[int]:
    """Roll `count` dice with `sides` sides each."""

    if count <= 0:
        raise ValueError("Number of dice must be greater than 0")

    return [roll(sides) for _ in range(count)]


def pool(size: int, sides: int, target: int) -> int:
    """Roll a total of `size` dice and count the number of dice
    that meet or exceed `target`."""

    return sum(i >= target for i in rolln(size, sides))
