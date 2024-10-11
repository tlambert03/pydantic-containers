from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, MutableSet
from functools import cached_property
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    TypeVar,
    get_args,
    overload,
)

from pydantic import TypeAdapter
from pydantic_core import SchemaValidator, core_schema

if TYPE_CHECKING:
    from pydantic import GetCoreSchemaHandler

_T = TypeVar("_T")


class ValidatedSet(MutableSet[_T]):
    @overload
    def __init__(self) -> None: ...
    @overload
    def __init__(
        self,
        iterable: Iterable[_T],
        *,
        item_validator: Callable[[Any], _T] | None = ...,
    ) -> None: ...
    def __init__(
        self,
        iterable: Iterable[_T] = (),
        *,
        item_validator: Callable[[Any], _T] | None = None,
    ) -> None:
        self._item_validator = item_validator
        if self._item_validator is not None:
            iterable = (self._item_validator(v) for v in iterable)
        self._set = set(iterable)

    # ---------------- abstract interface ----------------

    def __contains__(self, o: object, /) -> bool:
        return o in self._set

    def __iter__(self) -> Iterator[_T]:
        yield from self._set

    def __len__(self) -> int:
        return len(self._set)

    def add(self, value: _T) -> None:
        if self._validate_item is not None:
            value = self._validate_item(value)
        self._set.add(value)

    def discard(self, value: _T) -> None:
        self._set.discard(value)

    def __eq__(self, value: object) -> bool:
        return self._set == value

    # -----------------------------------------------------

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._set!r})"

    @cached_property
    def _validate_item(self) -> Callable[[Any], _T]:
        if self._item_validator is not None:
            return self._item_validator
        # __orig_class__ is not available during __init__
        # https://discuss.python.org/t/runtime-access-to-type-parameters/37517
        cls = getattr(self, "__orig_class__", None) or type(self)
        if args := get_args(cls):
            return TypeAdapter(args[0]).validator.validate_python
        return lambda x: x

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> Mapping[str, Any]:
        """Return the Pydantic core schema for this object."""
        # get item type
        item_type = args[0] if (args := get_args(source_type)) else Any

        # get item schemas and validators
        items_schema = handler.generate_schema(item_type)
        validate_item = SchemaValidator(items_schema).validate_python

        # define function that creates new instance during assignment
        # passing in the validator functions.
        def _new(*args: Any, **kwargs: Any) -> ValidatedSet[_T]:
            return cls(
                *args,
                item_validator=validate_item,
                **kwargs,
            )

        schema = core_schema.set_schema(items_schema=items_schema)
        return core_schema.no_info_after_validator_function(
            function=_new,
            schema=schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: x._set, return_schema=schema
            ),
        )
