from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableSequence
from functools import cached_property
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    SupportsIndex,
    TypeVar,
    get_args,
    overload,
)

from pydantic import TypeAdapter
from pydantic_core import SchemaValidator, core_schema

if TYPE_CHECKING:
    from pydantic import GetCoreSchemaHandler

_T = TypeVar("_T")


class ValidatedList(MutableSequence[_T]):
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
        self._list = list(iterable)

    # ---------------- abstract interface ----------------

    @overload
    def __getitem__(self, i: SupportsIndex) -> _T: ...
    @overload
    def __getitem__(self, i: slice) -> list[_T]: ...
    def __getitem__(self, i: SupportsIndex | slice) -> _T | list[_T]:
        return self._list[i]

    @overload
    def __setitem__(self, key: SupportsIndex, value: _T) -> None: ...
    @overload
    def __setitem__(self, key: slice, value: Iterable[_T]) -> None: ...
    def __setitem__(self, key: slice | SupportsIndex, value: _T | Iterable[_T]) -> None:
        if isinstance(value, Iterable):
            value = (self._validate_item(v) for v in value)
        else:
            value = self._validate_item(value)
        self._list[key] = value  # type: ignore [index,assignment]

    def __delitem__(self, key: SupportsIndex | slice) -> None:
        del self._list[key]

    def insert(self, index: SupportsIndex, obj: _T) -> None:
        obj = self._validate_item(obj)
        self._list.insert(index, obj)

    def __len__(self) -> int:
        return len(self._list)

    def __eq__(self, value: object) -> bool:
        return self._list == value

    # -----------------------------------------------------

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._list!r})"

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
        def _new(*args: Any, **kwargs: Any) -> ValidatedList[_T]:
            return cls(
                *args,
                item_validator=validate_item,
                **kwargs,
            )

        schema = core_schema.list_schema(items_schema=items_schema)
        return core_schema.no_info_after_validator_function(
            function=_new,
            schema=schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: x._list, return_schema=schema
            ),
        )
