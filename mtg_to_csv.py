import csv
import fileinput
import json
import logging
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError
from tqdm import tqdm

# these layouts always have the `card_faces` property
LayoutCardFaces = Literal["split", "flip", "transform", "double_faced_token"]

Layout = Literal[
    "adventure",
    "art_series",
    "augment",
    # documentation is wrong about battles
    # "battle",
    "class",
    "double_faced_token",
    "emblem",
    "flip",
    "host",
    "leveler",
    "meld",
    "modal_dfc",
    "mutate",
    "normal",
    "planar",
    "prototype",
    "reversible_card",
    "saga",
    "scheme",
    "split",
    "token",
    "transform",
    "vanguard",
]

# TODO: get each "side" of a card from a Card object
# TODO: get "visually distinct layouts" from CardSide
# TODO: get "type1" and "type2" from CardSide


class CardFace(BaseModel):
    object: Literal["card_face"]

    name: str
    printed_name: str | None

    colors: list[str] | None
    layout: Layout | None
    type_line: str | None


class Card(BaseModel):
    object: Literal["card"]

    oracle_id: UUID
    lang: str

    name: str
    flavor_name: str | None
    printed_name: str | None

    set_code: str = Field(alias="set")
    set_type: str

    layout: Layout

    card_faces: list[CardFace] | None


def parse_colors(colors: list[str]) -> str:
    color = "".join(sorted(colors))
    if not color:
        return "C"

    return color


# playtest sets have a visually very distinct look and
# some cards there have other weird types
playtest_sets = {"cmb1", "cmb2"}


type1 = Literal[
    "artifact",
    "conspiracy",
    "creature",
    "dungeon",
    "enchantment",
    "instant",
    "land",
    "planeswalker",
    "sorcery",
    # layouts
    "token",
    "adventure",
    "emblem",
]

type1_mapping: dict[frozenset[str], type1] = {
    frozenset(["creature", "enchantment"]): "creature"
}


def get_types(type_line: str) -> tuple[set[str], set[str]]:
    """
    Parse type line into two sets, first one containing the types on the left of
    `—` and the other containing the types on the right side of it.
    """

    lhs = set()
    rhs = set()
    for part in type_line.lower().split("//"):
        part = part.strip()
        parts = part.split("—")

        # no type line
        if len(parts) == 0:
            continue

        # only lhs type
        elif len(parts) == 1:
            lhs.update(parts[0].split())

        # lhs and rhs types
        elif len(parts) == 2:
            lhs.update(parts[0].split())
            rhs.update(parts[1].split())

        else:
            raise ValueError(f"type_line with more than two parts: {type_line!r}")

    return lhs, rhs


types = {
    "artifact",
    "conspiracy",
    "creature",
    "dungeon",
    "enchantment",
    "instant",
    "land",
    "planeswalker",
    "sorcery",
}

# types which should never be combined with other types
loner_types = {"creature", "planeswalker", "land"}

# layouts which are clearly visually distinct and
# the layout is more important than the type line
special_layouts = {
    "split",
    "flip",
    "leveler",
    "class",
    "saga",
    "adventure",
    "vanguard",
    "scheme",
    "emblem",
    # the type line can either be plane or phenomenon but the cards look almost the same
    # so it is better to combine these
    "planar",
}

skip_layouts = {"token", "double_faced_token"}


def parse_type(data: dict, set_: str) -> str | None:
    if set_ in playtest_sets:
        return "playtest"

    layout = data.get("layout")

    if layout in special_layouts:
        return layout

    if layout in skip_layouts:
        return None

    type_line = data.get("type_line")
    if not type_line:
        return None

    type_line_types = set()
    for part in type_line.lower().split("//"):
        part = part.strip()
        parts = part.split("—")

        # no type line
        if len(parts) == 0:
            continue

        # only lhs type
        elif len(parts) == 1:
            type_line_types.update(parts[0].split())

        # lhs and rhs types
        elif len(parts) == 2:
            type_line_types.update(parts[0].split())

        else:
            raise RuntimeError(f"type_line with more than three parts: {type_line!r}")

    type_line_types = types & type_line_types
    if not type_line_types:
        return None

    only_loners = type_line_types & loner_types
    if only_loners:
        if len(only_loners) != 1:
            raise RuntimeError(
                f"type_line with more than one loner type: {type_line!r}"
            )
        return only_loners.pop()

    # planeswalkers type should always be just planeswalker
    # if "planeswalker" in type_line_types:
    #     return "planeswalker"

    return " ".join(type_line_types)


def get_rows(data: dict):
    id_ = data["id"]
    set_ = data["set"]

    digital = data["digital"]
    if digital:
        return

    # set_type = data["set_type"]
    # if set_type == "funny":
    #     return

    image_status = data["image_status"]
    if image_status in {"missing", "placeholder"}:
        return

    def get_name(v):
        return v.get("printed_name") or v.get("flavor_name") or v["name"]

    try:
        name = get_name(data)
        color = parse_colors(data["colors"])
        type_ = parse_type(data, set_)
        image_url = data.get("image_uris", {})["small"]

        if type_:
            yield [id_, name, color, type_, set_, image_url]

    except KeyError:
        if "card_faces" not in data:
            raise

        for card_face in data["card_faces"]:
            name = get_name(card_face)
            color = parse_colors(card_face["colors"])
            type_ = parse_type(card_face, set_)
            image_url = card_face.get("image_uris", {})["small"]

            if type_:
                yield [id_, name, color, type_, set_, image_url]


with open("data/mtg.csv", "w") as fp:
    out = csv.writer(fp)
    out.writerow(["ID", "Name", "Color", "Type", "Set", "Image URL"])

    for line in tqdm(fileinput.input()):
        line = line.strip().removesuffix(",")
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            logging.info(f"failed to decode line as JSON document: {line!r}")
            continue

        try:
            card = Card(**data)
        except ValidationError:
            id_ = data.get("id")
            name = data.get("name")
            logging.error(f"failed to validate card: {name!r} ({id_})")
            continue
