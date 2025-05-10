from typing import TypeVar

T = TypeVar("T")


def unwrap(v: T | None, /) -> T:
    if v is None:
        raise ValueError("value must not be None")
    return v


def snake_to_camel(s: str) -> str:
    return "".join(x.capitalize() for x in s.split("_"))
