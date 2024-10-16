"""Type-safe generic containers for use as pydantic fields."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pydantic-containers")
except PackageNotFoundError:
    __version__ = "uninstalled"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"

from ._mapping import ValidatedDict
from ._sequence import ValidatedList
from ._set import ValidatedSet

__all__ = ["ValidatedDict", "ValidatedList", "ValidatedSet"]
