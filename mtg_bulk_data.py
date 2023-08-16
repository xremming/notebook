import json
from typing import Any, Callable, Iterable, Literal

import requests
from tqdm import tqdm


def bulk_data(
    type: Literal["oracle_cards", "all_cards"],
    decode_error_cb: Callable[[str], None] | None = None,
) -> Iterable[Any]:
    with requests.get(
        f"https://api.scryfall.com/bulk-data/{type}",
        params={"format": "file"},
        stream=True,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            assert isinstance(line, str)
            cleaned_line = line.strip().removesuffix(",")

            try:
                yield json.loads(cleaned_line)
            except json.JSONDecodeError:
                if decode_error_cb:
                    decode_error_cb(cleaned_line)
                continue


def dl_bulk_data(type: Literal["oracle_cards", "all_cards"]):
    with open(f"data/mtg-{type}.jsonl", "w") as fp, tqdm(
        desc=f"Downloading {type}"
    ) as pbar:
        for card in bulk_data(
            type, lambda line: pbar.write(f"failed to decode: {line!r}")
        ):
            fp.write(json.dumps(card, ensure_ascii=False) + "\n")
            pbar.update()


if __name__ == "__main__":
    dl_bulk_data("oracle_cards")
    dl_bulk_data("all_cards")
