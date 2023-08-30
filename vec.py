from __future__ import annotations

import abc
from dataclasses import dataclass
from decimal import Decimal
from typing import Generic, Literal, TypeVar

VecT = TypeVar("VecT", float, int, Decimal)

XY = Literal["x", "y"]
XYZ = Literal["x", "y", "z", "r", "g", "b"]
XYZW = Literal["x", "y", "z", "w", "r", "g", "b", "a"]


class Swizzle2Base(Generic[VecT], abc.ABC):
    @property
    @abc.abstractmethod
    def x(self) -> VecT:
        ...

    @x.setter
    @abc.abstractmethod
    def x(self, value: VecT) -> None:
        ...

    @property
    @abc.abstractmethod
    def y(self) -> VecT:
        ...

    @y.setter
    @abc.abstractmethod
    def y(self, value: VecT) -> None:
        ...


class Swizzle2(Generic[VecT], Swizzle2Base[VecT], abc.ABC):
    def swizzle2(self, x: XY, y: XY) -> tuple[VecT, VecT]:
        return getattr(self, x), getattr(self, y)

    def swizzle3(self, x: XY, y: XY, z: VecT) -> tuple[VecT, VecT, VecT]:
        return getattr(self, x), getattr(self, y), z

    def swizzle4(self, x: XY, y: XY, z: VecT, w: VecT) -> tuple[VecT, VecT, VecT, VecT]:
        return getattr(self, x), getattr(self, y), z, w


class Swizzle3Base(Generic[VecT], Swizzle2Base[VecT], abc.ABC):
    @property
    @abc.abstractmethod
    def z(self) -> VecT:
        ...

    @z.setter
    @abc.abstractmethod
    def z(self, value: VecT) -> None:
        ...


class Swizzle3(Generic[VecT], Swizzle3Base[VecT], abc.ABC):
    @property
    def r(self) -> VecT:
        return self.x

    @r.setter
    def r(self, value: VecT) -> None:
        self.x = value

    @property
    def g(self) -> VecT:
        return self.y

    @g.setter
    def g(self, value: VecT) -> None:
        self.y = value

    @property
    def b(self) -> VecT:
        return self.z

    @b.setter
    def b(self, value: VecT) -> None:
        self.z = value

    def swizzle2(self, x: XYZ, y: XYZ) -> tuple[VecT, VecT]:
        return getattr(self, x), getattr(self, y)

    def swizzle3(self, x: XYZ, y: XYZ, z: XYZ) -> tuple[VecT, VecT, VecT]:
        return getattr(self, x), getattr(self, y), getattr(self, z)

    def swizzle4(
        self, x: XYZ, y: XYZ, z: XYZ, w: VecT
    ) -> tuple[VecT, VecT, VecT, VecT]:
        return getattr(self, x), getattr(self, y), getattr(self, z), w


@dataclass
class Vec2(Swizzle2):
    x: float = 0.0
    y: float = 0.0

    def is_zero(self) -> bool:
        return self.x == 0.0 and self.y == 0.0

    def length(self) -> float:
        return (self.x**2 + self.y**2) ** 0.5

    def normalize(self) -> Vec2:
        length = self.length()
        return Vec2(self.x / length, self.y / length)


@dataclass
class Vec3(Generic[VecT], Swizzle3[VecT]):
    x: VecT
    y: VecT
    z: VecT

    def is_zero(self) -> bool:
        return self.x == 0.0 and self.y == 0.0 and self.z == 0.0

    # def length(self) -> VecT:
    #     return (self.x**2 + self.y**2 + self.z**2) ** 0.5

    # def normalize(self) -> Vec3:
    #     length = self.length()
    #     return Vec3(self.x / length, self.y / length, self.z / length)


if __name__ == "__main__":
    v = Vec2(1, 2)
    print(v.swizzle2("x", "y"))

    v2 = Vec3[int](1, 2, 3)
    print(v2.swizzle3("x", "y", "z"))
