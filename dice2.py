from itertools import product


def at_least_n_successes(tosses: int, n: int, chance: float = 0.5) -> float:
    total_ways = 2**tosses

    possible_tosses = product([1, 0], repeat=tosses)
    total_successes_per_toss = map(sum, possible_tosses)
    tosses_with_at_least_n_successes = filter(
        lambda successes: successes >= n, total_successes_per_toss
    )
    ways_to_succeed = len(list(tosses_with_at_least_n_successes))

    # ways_to_succeed = len(
    #     list(filter(lambda v: v >= n, map(sum, product([1, 0], repeat=tosses))))
    # )

    print(f"{total_ways=}")

    print(chance**n, (1 - chance) ** (tosses - n))
    _, __ = total_ways, ways_to_succeed

    return 1


if __name__ == "__main__":
    print(at_least_n_successes(2, 1, 0.5))
