# pydantic-containers

[![License](https://img.shields.io/pypi/l/pydantic-containers.svg?color=green)](https://github.com/tlambert03/pydantic-containers/raw/main/LICENSE)
[![CI](https://github.com/tlambert03/pydantic-containers/actions/workflows/ci.yml/badge.svg)](https://github.com/tlambert03/pydantic-containers/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/tlambert03/pydantic-containers/branch/main/graph/badge.svg)](https://codecov.io/gh/tlambert03/pydantic-containers)

Type-safe generic containers for use as pydantic fields.

At the moment, these are just patterns and this package is not published.
Feel free to copy and vendor the code as needed.

```python
from pydantic import BaseModel, ConfigDict, Field

from pydantic_containers import ValidatedDict, ValidatedList, ValidatedSet

class MyModel(BaseModel):
    my_list: ValidatedList[int] = Field(default_factory=list)
    my_dict: ValidatedDict[str, list[int]] = Field(default_factory=dict)
    my_set: ValidatedSet[int] = Field(default_factory=set)
    # NOTE: it's currently critical that validate_default is used
    model_config = ConfigDict(validate_default=True)

obj = MyModel()
obj.my_list.append("1")
assert obj.my_list == [1]

obj.my_dict["key"] = ["1"]
assert obj.my_dict == {"key": [1]}

obj.my_set.add("1")
assert obj.my_set == {1}
```

These also work as bare types:

```python
x = ValidatedDict[int, list[float]]()
x.update({"1": ["7.5"]})
assert x[1] == [7.5]
```
