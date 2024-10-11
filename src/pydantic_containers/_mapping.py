from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, MutableMapping
from functools import cached_property
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Protocol,
    TypeVar,
    get_args,
    overload,
)

from pydantic import TypeAdapter
from pydantic_core import SchemaValidator, core_schema

if TYPE_CHECKING:
    from pydantic import GetCoreSchemaHandler

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")
_VT_co = TypeVar("_VT_co", covariant=True)


class SupportsKeysAndGetItem(Protocol[_KT, _VT_co]):
    def keys(self) -> Iterable[_KT]: ...
    def __getitem__(self, key: _KT, /) -> _VT_co: ...


class ValidatedDict(MutableMapping[_KT, _VT]):
    @overload
    def __init__(self) -> None: ...
    @overload
    def __init__(  # type: ignore[misc]
        self: dict[str, _VT],
        key_validator: Callable[[Any], _KT] | None = None,
        value_validator: Callable[[Any], _VT] | None = None,
        **kwargs: _VT,
    ) -> None: ...
    @overload
    def __init__(
        self,
        map: SupportsKeysAndGetItem[_KT, _VT],
        /,
        key_validator: Callable[[Any], _KT] | None = None,
        value_validator: Callable[[Any], _VT] | None = None,
    ) -> None: ...
    @overload
    def __init__(  # type: ignore[misc]
        self: dict[str, _VT],
        map: SupportsKeysAndGetItem[str, _VT],
        /,
        key_validator: Callable[[Any], _KT] | None = ...,
        value_validator: Callable[[Any], _VT] | None = ...,
        validate_lookup: bool = ...,
        **kwargs: _VT,
    ) -> None: ...
    @overload
    def __init__(
        self,
        iterable: Iterable[tuple[_KT, _VT]],
        /,
        key_validator: Callable[[Any], _KT] | None = ...,
        value_validator: Callable[[Any], _VT] | None = ...,
        validate_lookup: bool = ...,
    ) -> None: ...
    @overload
    def __init__(  # type: ignore[misc]
        self: dict[str, _VT],
        iterable: Iterable[tuple[str, _VT]],
        /,
        key_validator: Callable[[Any], _KT] | None = ...,
        value_validator: Callable[[Any], _VT] | None = ...,
        validate_lookup: bool = ...,
        **kwargs: _VT,
    ) -> None: ...
    def __init__(  # type: ignore[misc] # does not accept all possible overloads
        self,
        *args: Any,
        key_validator: Callable[[Any], _KT] | None = None,
        value_validator: Callable[[Any], _VT] | None = None,
        validate_lookup: bool = False,
        **kwargs: Any,
    ) -> None:
        self._key_validator = key_validator
        self._value_validator = value_validator
        self._validate_lookup = validate_lookup
        _d = {}
        for k, v in dict(*args, **kwargs).items():
            if self._key_validator is not None:
                k = self._key_validator(k)
            if self._value_validator is not None:
                v = self._value_validator(v)
            _d[k] = v
        self._dict: dict[_KT, _VT] = _d

    # ---------------- abstract interface ----------------

    def __getitem__(self, key: _KT) -> _VT:
        if self._validate_lookup:
            key = self._validate_key(key)
        return self._dict[key]

    # def __setitem__(self, key: _KT, value: _VT) -> None:
    def __setitem__(self, key: Any, value: Any) -> None:
        key = self._validate_key(key)
        value = self._validate_value(value)
        self._dict[key] = value

    def __delitem__(self, key: _KT) -> None:
        if self._validate_lookup:
            key = self._validate_key(key)
        del self._dict[key]

    def __len__(self) -> int:
        return len(self._dict)

    def __iter__(self) -> Iterator[_KT]:
        return iter(self._dict)

    # -----------------------------------------------------

    @cached_property
    def _validate_key(self) -> Callable[[Any], _KT]:
        if self._key_validator is not None:
            return self._key_validator
        # __orig_class__ is not available during __init__
        # https://discuss.python.org/t/runtime-access-to-type-parameters/37517
        cls = getattr(self, "__orig_class__", None) or type(self)
        if args := get_args(cls):
            return TypeAdapter(args[0]).validator.validate_python
        return lambda x: x

    @cached_property
    def _validate_value(self) -> Callable[[Any], _VT]:
        if self._value_validator is not None:
            return self._value_validator
        # __orig_class__ is not available during __init__
        # https://discuss.python.org/t/runtime-access-to-type-parameters/37517
        cls = getattr(self, "__orig_class__", None) or type(self)
        if len(args := get_args(cls)) > 1:
            return TypeAdapter(args[1]).validator.validate_python
        return lambda x: x

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._dict!r})"

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> Mapping[str, Any]:
        """Return the Pydantic core schema for this object."""
        # get key/value types
        key_type = val_type = Any
        if args := get_args(source_type):
            key_type = args[0]
            if len(args) > 1:
                val_type = args[1]

        # get key/value schemas and validators
        keys_schema = handler.generate_schema(key_type)
        values_schema = handler.generate_schema(val_type)
        validate_key = SchemaValidator(keys_schema).validate_python
        validate_value = SchemaValidator(values_schema).validate_python

        # define function that creates new instance during assignment
        # passing in the validator functions.
        def _new(*args: Any, **kwargs: Any) -> ValidatedDict[_KT, _VT]:
            return cls(  # type: ignore[call-overload,no-any-return]
                *args,
                key_validator=validate_key,
                value_validator=validate_value,
                **kwargs,
            )

        schema = core_schema.dict_schema(
            keys_schema=keys_schema, values_schema=values_schema
        )
        return core_schema.no_info_after_validator_function(
            function=_new,
            schema=schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: x._dict, return_schema=schema
            ),
        )
