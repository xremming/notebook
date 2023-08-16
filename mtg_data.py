import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from random import shuffle
from uuid import UUID

import requests
from tqdm import tqdm


def iter_cards():
    with open("data/oracle-cards-all.json") as f:
        while True:
            line = f.readline()
            if not line:
                break
            if not line.startswith("{"):
                continue
            yield json.loads(line.removesuffix(",\n"))


def colors_str(colors: list[str]) -> str:
    return "".join(sorted(colors))


types = {
    "artifact",
    "conspiracy",
    "creature",
    "dungeon",
    "enchantment",
    "instant",
    "land",
    "phenomenon",
    "plane",
    "planeswalker",
    "scheme",
    "sorcery",
    "tribal",
    "vanguard",
}


def types_str(type_line: str) -> str:
    type_line_types = set(type_.lower() for type_ in type_line.split())
    return " ".join(sorted(types & type_line_types))


@dataclass
class Card:
    uuid: str
    name: str
    image_uri: str
    colors: str
    types: str
    set: str

    def drop(self) -> bool:
        if not self.types:
            return True

        return False


def get_name(card) -> str:
    return card.get("printed_name") or card.get("flavor_name") or card["name"]


def get_card_data(card) -> tuple[UUID, list[Card]] | None:
    # digital cards are not interesting
    if card.get("digital", False):
        return None

    if card.get("image_status") in {"missing", "placeholder"}:
        return None

    if "type_line" in card:
        type_line = card["type_line"].lower()
        if "token" in type_line:
            return None

        types = types_str(card["type_line"])
        if len(types) == 0:
            return None

    if "oracle_id" not in card:
        if "card_faces" not in card:
            raise ValueError(f"Card has no oracle_id: {card['id']}")

        oracle_ids_in_card_faces: set[str] = set()
        for card_face in card["card_faces"]:
            if "oracle_id" in card_face:
                oracle_ids_in_card_faces.add(card_face["oracle_id"])

        if len(oracle_ids_in_card_faces) != 1:
            raise ValueError(f"Card has no oracle_id: {card['id']}")

        key = UUID(oracle_ids_in_card_faces.pop())
    else:
        key = UUID(card["oracle_id"])

    if "card_faces" in card:
        try:
            data: list[Card] = []
            for i, card_face in enumerate(card["card_faces"]):
                data.append(
                    Card(
                        uuid=f"{card['id']}-{i}",
                        name=get_name(card_face),
                        image_uri=card_face["image_uris"]["normal"],
                        colors=colors_str(card_face["colors"]),
                        types=types_str(card_face["type_line"]),
                        set=card["set"],
                    )
                )
        except KeyError:
            # means that the cards data is not in card_faces
            # will fallback to getting the data from the top-level card object
            pass
        else:
            return key, data

    data = [
        Card(
            uuid=card["id"],
            name=get_name(card),
            image_uri=card["image_uris"]["small"],
            colors=colors_str(card["colors"]),
            types=types_str(card["type_line"]),
            set=card["set"],
        )
    ]

    return key, data


oracle_id_to_card: dict[UUID, list[Card]] = defaultdict(list)
for card in tqdm(iter_cards(), "Loading cards"):
    v = get_card_data(card)
    if v is None:
        continue
    key, data = v
    oracle_id_to_card[key].extend([card for card in data if not card.drop()])

to_save = [(key, cards) for key, cards in oracle_id_to_card.items()]
shuffle(to_save)
to_save = to_save[:1000]

download: list[tuple[Path, str]] = []
for key, cards in tqdm(to_save, "Saving cards"):
    p = Path("data", "cards", str(key))
    p.mkdir(parents=True, exist_ok=True)

    p_data = p / "data.json"
    with open(p_data, "w") as f:
        json.dump(
            {
                "id": str(key),
                "cards": [
                    {
                        "image": f"{card.uuid}.jpg",
                        "name": card.name,
                        "colors": card.colors,
                        "types": card.types,
                        "set": card.set,
                    }
                    for card in cards
                ],
            },
            f,
        )

    download.extend((p / f"{card.uuid}.jpg", card.image_uri) for card in cards)

sess = requests.session()


def dl(v):
    p, url = v
    if p.exists():
        return

    res = sess.get(url)
    res.raise_for_status()
    with open(p, "wb") as f:
        f.write(res.content)


with ThreadPoolExecutor(max_workers=4) as pool:
    for _ in tqdm(
        pool.map(dl, ((p, url) for p, url in download)),
        desc="Downloading images",
        total=len(download),
    ):
        pass
