from __future__ import annotations

import csv
import hashlib
import json
from pathlib import PurePath
from typing import Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError
from tqdm import tqdm

Color = Literal["W", "U", "B", "R", "G"]
Frame = Literal["1993", "1997", "2003", "2015", "future"]
ImageStatus = Literal["missing", "placeholder", "lowres", "highres_scan"]
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
    colors: list[Color]
    image_uris: ImageURIs

    @property
    def preferred_filename(self) -> str:
        small_image = self.image_uris.small
        url = urlparse(small_image)
        p = PurePath(url.path)
        digest = hashlib.md5(small_image.encode(), usedforsecurity=False).hexdigest()

        return f"{digest}{p.suffix}"

    @property
    def parsed_type_line(self) -> tuple[str, str]:
        lhs, rhs = set(), set()
        for part in self.type_line.lower().split("//"):
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
                raise ValueError(
                    f"type_line with more than two parts: {self.type_line!r}"
                )

        # Atinlay Igpay is a creature - pig
        # but its type line is just written with pig latin
        # https://scryfall.com/card/unh/1/atinlay-igpay
        if "eaturecray" in lhs:
            lhs.remove("eaturecray")
            lhs.add("creature")

        if "igpay" in rhs:
            rhs.remove("igpay")
            rhs.add("pig")

        if not lhs:
            lhs.add("[none]")

        if not rhs:
            rhs.add("[none]")

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

    @property
    def parsed_colors(self) -> str:
        color = "".join(sorted(self.colors))
        if not color:
            return "c"

        return color.lower()

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
            "Image Filename",
        ]

    def row(self):
        type1, type2 = self.parsed_type_line

        return [
            self.oracle_id,
            self.name,
            self.set_code,
            self.layout,
            self.frame,
            self.physical_kind(type1),
            type1,
            type2,
            self.parsed_colors,
            self.image_uris.small,
            self.preferred_filename,
        ]


class CardFace(BaseModel):
    object: Literal["card_face"]

    name: str
    printed_name: str | None

    colors: list[Color] | None
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
