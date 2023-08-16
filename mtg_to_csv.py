from __future__ import annotations

import csv
import json
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError
from tqdm import tqdm

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

NormalizedLayout = Literal[
    "adventure",
    "art_series",
    "augment",
    "class",
    "token",  # combines token and double_faced_token
]

Frame = Literal["1993", "1997", "2003", "2015", "future"]

ImageStatus = Literal["missing", "placeholder", "lowres", "highres_scan"]


class ImageURIs(BaseModel):
    small: str
    normal: str
    large: str
    png: str
    art_crop: str
    border_crop: str


PhysicalKind = Literal[
    "creature",
    "token",
    "land",
    "artifact",
    "enchantment",
    "planeswalker",
    "instant",
    "sorcery",
    "battle",
    # layouts
    "conspiracy",
    "adventure",
    "saga-like",  # saga or class
    "split",
    "flip",
    "playtest",  # cards in cmb1 or cmb2, which have a visually distinct look
    "planar",
    "scheme",
    "emblem",
    "vanguard",
    "scheme",
    # other
    "other",
]


class PhysicalCard(BaseModel):
    oracle_id: UUID
    name: str
    set_code: str
    layout: Layout
    frame: Frame
    type_line: str
    colors: list[str]
    image_uris: ImageURIs

    @staticmethod
    def parse_type_line(type_line: str) -> tuple[str, str]:
        lhs, rhs = set(), set()
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

        # Atinlay Igpay is a creature - pig
        # but its type line is just written with pig latin
        # https://scryfall.com/card/unh/1/atinlay-igpay
        if "eaturecray" in lhs:
            lhs.remove("eaturecray")
            lhs.add("creature")

        if "igpay" in rhs:
            rhs.remove("igpay")
            rhs.add("pig")

        return " ".join(sorted(lhs)), " ".join(sorted(rhs))

    def physical_kind(self, type1: str) -> PhysicalKind:
        t = set(type1.split())

        if self.set_code in {"cmb1", "cmb2"}:
            return "playtest"

        if self.layout in {"saga", "class"}:
            return "saga-like"

        if self.layout in {
            "adventure",
            "vanguard",
            "scheme",
            "emblem",
            "split",
            "flip",
            "planar",
            "scheme",
        }:
            return self.layout  # type: ignore

        if self.layout in {"token", "double_faced_token"}:
            return "token"

        if t & {"creature", "summon"}:
            return "creature"

        if "land" in t:
            return "land"

        if "artifact" in t:
            return "artifact"

        if "enchantment" in t:
            return "enchantment"

        if "planeswalker" in t or "universewalker" in t:
            return "planeswalker"

        if "instant" in t:
            return "instant"

        if "sorcery" in t:
            return "sorcery"

        if "battle" in t:
            return "battle"

        if "conspiracy" in t:
            return "conspiracy"

        if t & {"stickers", "card", "hero", "dungeon"}:
            return "other"

        raise RuntimeError(f"unknown physical kind: {self!r} {type1!r}")

    @classmethod
    def header(cls):
        return [
            "Oracle ID",
            "Name",
            "Set",
            "Layout",
            "Frame",
            "Kind",
            "Type1",
            "Type2",
            "Colors",
            "Image URL",
        ]

    def row(self):
        type1, type2 = self.parse_type_line(self.type_line)

        return [
            self.oracle_id,
            self.name,
            self.set_code,
            self.layout,
            self.frame,
            self.physical_kind(type1),
            type1,
            type2,
            parse_colors(self.colors),
            self.image_uris.small,
        ]


Color = Literal["W", "U", "B", "R", "G"]


class CardFace(BaseModel):
    object: Literal["card_face"]

    name: str
    printed_name: str | None

    colors: list[str] | None
    layout: Layout | None
    type_line: str | None

    image_uris: ImageURIs | None

    def physical_card(
        self,
        card: Card,
    ) -> PhysicalCard:
        layout = self.layout or card.layout
        if layout is None:
            raise RuntimeError(f"card face {self.name!r} has no layout")

        if not self.image_uris:
            raise RuntimeError(f"card face {self.name!r} has no image_uris")

        if self.colors is None:
            raise RuntimeError(f"card face {self.name!r} has no colors")

        return PhysicalCard(
            oracle_id=card.oracle_id,
            name=self.printed_name or self.name,
            set_code=card.set_code,
            layout=layout,
            frame=card.frame,
            type_line=self.type_line or card.type_line,
            colors=self.colors,
            image_uris=self.image_uris,
        )


class Card(BaseModel):
    object: Literal["card"]

    oracle_id: UUID
    lang: str

    digital: bool

    image_status: ImageStatus
    image_uris: ImageURIs | None

    name: str
    flavor_name: str | None
    printed_name: str | None

    set_code: str = Field(alias="set")
    set_type: str

    layout: Layout
    frame: Frame

    type_line: str
    colors: list[Color] | None

    card_faces: list[CardFace] | None

    def coalesce_name(self) -> str:
        return self.printed_name or self.flavor_name or self.name

    def physical_cards(self) -> list[PhysicalCard]:
        if self.digital:
            return []

        if self.image_status in {"missing", "placeholder"}:
            return []

        if self.image_uris is None and self.card_faces:
            return [c.physical_card(self) for c in self.card_faces]

        return [PhysicalCard(**self.dict())]


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


with (
    open("data/mtg-all_cards.jsonl") as in_fp,
    open("data/mtg.csv", "w") as out_fp,
    tqdm(desc="Processing cards") as pbar,
):
    out = csv.writer(out_fp)
    out.writerow(PhysicalCard.header())

    for line in in_fp:
        try:
            data = json.loads(line)
            card = Card(**data)
            physical_cards = card.physical_cards()
            out.writerows(c.row() for c in physical_cards)

        except ValidationError as e:
            if any(
                v["loc"] == ("oracle_id",) and v["type"] == "value_error.missing"
                for v in e.errors()
            ):
                pbar.write("skipping card without oracle_id")
                continue

            data = locals().get("data", {})
            name = data.get("name")
            id_ = data.get("id")
            url = f"https://api.scryfall.com/cards/{id_}?pretty=true"

            pbar.write(f"failed to validate card {name!r} ({url}): {e!r}")
            continue
        finally:
            pbar.update()
