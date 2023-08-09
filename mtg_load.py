import json
from pathlib import Path
from typing import Any, Callable

import requests


def download(path: str, url: str) -> Callable[[], Any]:
    p = Path(path)

    def load() -> Any:
        with open(p) as f:
            return json.load(f)

    if not p.exists():
        res = requests.get(url)
        res.raise_for_status()
        with open(p, "wb") as f:
            f.write(res.content)

    return load


load_mtg_oracle = download(
    "data/oracle-cards.json",
    "https://data.scryfall.io/oracle-cards/oracle-cards-20230809090236.json",
)
load_mtg_oracle_all = download(
    "data/oracle-cards-all.json",
    "https://data.scryfall.io/all-cards/all-cards-20230809091733.json",
)
