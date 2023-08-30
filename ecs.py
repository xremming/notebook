from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    NewType,
    Optional,
    TypeVar,
    TypeVarTuple,
)

Entity = NewType("Entity", int)
Component = Any
System = Callable[..., None]

T = TypeVar("T")
Cs = TypeVarTuple("Cs")
R = TypeVar("R")


class Commands:
    def add_resource(self, resource: Component) -> None:
        ...

    def remove_resource(self, resource_type: type) -> None:
        ...

    def add_entity(self, *components: Component) -> None:
        ...

    def remove_entity(self, entity: Entity) -> None:
        ...

    def add_component(self, entity: Entity, component: Component) -> None:
        ...

    def remove_component(self, entity: Entity, component_type: type) -> None:
        ...


# class Resource(Generic[R]):
#     def __init__(self, resource: R):
#         self.resource = resource

#     def __call__(self) -> R:
#         return self.resource


class Query(Generic[*Cs]):
    def __init__(self, world: World, query: list[QueryArg]) -> None:
        self._world = world
        self._query = query

    def __call__(self) -> Iterable[tuple[Entity, tuple[*Cs]]]:
        for entity in self._world.entities:
            components = []
            for arg in self._query:
                component = self._world.components.get(arg.component, {}).get(entity)
                if component is None and not arg.optional:
                    break
                components.append(component)
            else:
                yield entity, tuple(components)  # type: ignore


@dataclass
class ParameterCommands:
    name: str


@dataclass
class ParameterResource:
    name: str
    component: type
    optional: bool = False


@dataclass
class QueryArg:
    component: type
    optional: bool = False


@dataclass
class ParameterQuery:
    name: str
    args: list[QueryArg]


Parameter = ParameterCommands | ParameterResource | ParameterQuery


def unwrap_optional(t) -> tuple[type, bool]:
    optional = str(t).startswith("typing.Optional")
    if optional:
        return t.__args__[0], True

    return t, False


def inspect_system(system: Callable[..., None]):
    out: list[Parameter] = []

    signature = inspect.signature(system, eval_str=True)
    for name, parameter in signature.parameters.items():
        annotation = parameter.annotation
        print(f"{name}: {annotation}")

        if annotation is Commands:
            out.append(ParameterCommands(name))
        elif hasattr(annotation, "__origin__") and annotation.__origin__ is Query:
            args = []
            for arg in annotation.__args__:
                component, optional = unwrap_optional(arg)
                args.append(QueryArg(component, optional))
            out.append(ParameterQuery(name, args))
        else:
            component, optional = unwrap_optional(annotation)
            out.append(ParameterResource(name, component, optional))

    return out


class World:
    def __init__(self, *systems: System):
        self.entities: list[Entity] = []
        self._next_entity_id = 0

        self.components: dict[type, dict[Entity, Any]] = {}
        self.resources: dict[type, Any] = {}

        self.systems: list[System] = list(systems)

    def run(self) -> None:
        for system in self.systems:
            parameters = inspect_system(system)

            args: dict[str, Any] = {}
            for parameter in parameters:
                if isinstance(parameter, ParameterCommands):
                    args[parameter.name] = self

                elif isinstance(parameter, ParameterResource):
                    resource = self.get_resource(parameter.component)
                    if resource is None and not parameter.optional:
                        # systems which require a resource which is not present
                        # are skipped
                        break

                    args[parameter.name] = resource

                elif isinstance(parameter, ParameterQuery):
                    args[parameter.name] = Query(self, parameter.args)

                else:
                    raise ValueError(f"Invalid parameter: {parameter}")

            system(**args)

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


# ---


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


class AirDrag(float):
    pass


class MasterVolume(float):
    pass


class Volume(float):
    pass


class PlayVolume(float):
    pass


def apply_velocity(query: Query[Optional[Name], Position, Velocity]) -> None:
    for _, (name, position, velocity) in query():
        if name is not None:
            print(f"Updating position of {name!r}.")
        position.x += velocity.x
        position.y += velocity.y


def apply_air_drag(air_drag: AirDrag, query: Query[Velocity]) -> None:
    for _, (velocity,) in query():
        velocity.x *= air_drag
        velocity.y *= air_drag


def apply_volume(
    master_volume: Optional[MasterVolume], query: Query[Optional[Volume], PlayVolume]
) -> None:
    for _, (volume, play_volume) in query():
        play_volume += (volume or 1) * (master_volume or 1)


if __name__ == "__main__":
    w = World(apply_velocity, apply_air_drag, apply_volume)

    w.add_resource(AirDrag(0.9))
    # w.add_resource(MasterVolume(0.5))

    w.create_entity(Name("Max"), Position(), Velocity(1, 1), Volume(0.5), PlayVolume())
    w.create_entity(Position(), Velocity(-1, -1))
    w.create_entity(Name("Other"), Position())

    from pprint import pprint

    for _ in range(10):
        w.run()
        pprint(w.components[PlayVolume])
