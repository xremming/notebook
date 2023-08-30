from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol, TypeVar, overload

Entity = int


class System(Protocol):
    def update(self, world: World) -> None:
        ...


T = TypeVar("T")
R = TypeVar("R")
C1 = TypeVar("C1")
C2 = TypeVar("C2")
C3 = TypeVar("C3")
C4 = TypeVar("C4")


class World:
    def __init__(self, *systems: System):
        self.entities: list[Entity] = []
        self._next_entity_id = 0

        self.components: dict[type, dict[Entity, Any]] = {}
        self.resources: dict[type, Any] = {}

        self.systems: list[System] = list(systems)

    def run(self) -> None:
        for system in self.systems:
            system.update(self)

    def create_entity(self, *components: Any) -> Entity:
        entity = Entity(self._next_entity_id)
        self._next_entity_id += 1
        self.entities.append(entity)

        for component in components:
            self.add_component(entity, component)

        return entity

    def add_component(self, entity: Entity, component: Any) -> None:
        component_type = type(component)
        if component_type not in self.components:
            self.components[component_type] = {}
        self.components[component_type][entity] = component

    def add_resource(self, resource: Any) -> None:
        self.resources[type(resource)] = resource

    def get_resource(self, resource_type: type[R], default: T = None) -> R | T:
        return self.resources.get(resource_type, default)

    @overload
    def query(self, c1: type[C1]) -> Iterable[tuple[Entity, tuple[C1]]]:
        ...

    @overload
    def query(
        self, c1: type[C1], c2: type[C2]
    ) -> Iterable[tuple[Entity, tuple[C1, C2]]]:
        ...

    @overload
    def query(
        self, c1: type[C1], c2: type[C2], c3: type[C3]
    ) -> Iterable[tuple[Entity, tuple[C1, C2, C3]]]:
        ...

    @overload
    def query(
        self,
        c1: type[C1],
        c2: type[C2],
        c3: type[C3],
        c4: type[C4],
    ) -> Iterable[tuple[Entity, tuple[C1, C2, C3, C4]]]:
        ...

    def query(
        self,
        c1: type[C1],
        c2: type[C2] | None = None,
        c3: type[C3] | None = None,
        c4: type[C4] | None = None,
    ) -> Iterable[
        tuple[
            Entity,
            tuple[C1] | tuple[C1, C2] | tuple[C1, C2, C3] | tuple[C1, C2, C3, C4],
        ]
    ]:
        components = list(filter(None, (c1, c2, c3, c4)))
        for entity in self.entities:
            if all(
                component_type in self.components
                and entity in self.components[component_type]
                for component_type in components
            ):
                yield entity, tuple(
                    self.components[component][entity] for component in components
                )


class Name(str):
    pass


@dataclass
class Position:
    x: float = 0.0
    y: float = 0.0


@dataclass
class Velocity:
    x: float = 0.0
    y: float = 0.0


@dataclass
class PhysicsConstants:
    gravity: float = 9.81
    air_drag: float = 0.1


class MovementSystem:
    def update(self, world: World) -> None:
        for entity, (position, velocity) in world.query(Position, Velocity):
            position.x += velocity.x
            position.y += velocity.y


if __name__ == "__main__":
    w = World(MovementSystem())

    w.add_resource(PhysicsConstants())

    w.create_entity(Name("Max"), Position(), Velocity(1, 1))
    w.create_entity(Name("Min"), Position(), Velocity(-1, -1))
    w.create_entity(Name("Other"), Position())

    from pprint import pprint

    for _ in range(10):
        w.run()
        pprint(list(w.query(Name, Position, Velocity)))
