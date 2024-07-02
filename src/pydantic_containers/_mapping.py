from __future__ import annotations

from collections import UserDict, defaultdict
from functools import cached_property
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Mapping,
    TypeVar,
    get_args,
    get_origin,
)

from pydantic import TypeAdapter
from pydantic_core import SchemaValidator, core_schema

if TYPE_CHECKING:
    from pydantic import GetCoreSchemaHandler

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class ValidatedDict(UserDict[_KT, _VT]):
    # Start by filling-out the abstract methods
    def __init__(
        self,
        m: Mapping[_KT, _VT] | Iterable[tuple[_KT, _VT]] | None = None,
        /,
        key_validator: Callable[[Any], _KT] | None = None,
        value_validator: Callable[[Any], _VT] | None = None,
        **kwargs: _VT,
    ) -> None:
        self._key_validator = key_validator
        self._value_validator = value_validator
        self.data = {}
        if m is not None:
            self.update(m)
        if kwargs:
            self.update(kwargs)  # type: ignore

    # ---------------- abstract interface ----------------

    def __setitem__(self, key: Any, value: Any) -> None:
        key = self._validate_key(key)
        value = self._validate_value(value)
        self.data[key] = value

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
        return f"{type(self).__name__}({self.data!r})"

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
            kwargs["key_validator"] = validate_key
            kwargs["value_validator"] = validate_value
            return cls(val_type, *args, **kwargs)

        schema = core_schema.dict_schema(
            keys_schema=keys_schema, values_schema=values_schema
        )
        return core_schema.no_info_after_validator_function(
            function=_new,
            schema=schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: x.data, return_schema=schema
            ),
        )


class ValidatedDefaultDict(ValidatedDict[_KT, _VT]):
    def __init__(
        self,
        default_factory: Callable[[], _VT] | None = None,
        m: Mapping[_KT, _VT] | Iterable[tuple[_KT, _VT]] | None = None,
        /,
        key_validator: Callable[[Any], _KT] | None = None,
        value_validator: Callable[[Any], _VT] | None = None,
        **kwargs: _VT,
    ) -> None:
        super().__init__(m, key_validator, value_validator, **kwargs)
        self.default_factory = default_factory

    def __getitem__(self, key: _KT) -> _VT:
        if key in self:
            return super().__getitem__(key)
        value = self.default_factory() if self.default_factory else None
        self[key] = value
        return value
