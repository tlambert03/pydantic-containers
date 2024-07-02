from pydantic import BaseModel, ConfigDict, Field

from pydantic_containers import ValidatedDict


def test_mapping() -> None:
    class T(BaseModel):
        d: ValidatedDict[int, list[float]] = Field(default_factory=dict)
        model_config = ConfigDict(validate_default=True)

    t = T()
    t.d.update({"1": ["7.5"]})  # type: ignore
    assert 1 in t.d
    assert t.d[1] == [7.5]

    js = t.model_dump_json()
    assert isinstance(js, str)
    t2 = T.model_validate_json(js)
    assert isinstance(t2, T)
    assert isinstance(t2.d, ValidatedDict)
    assert t2 == t

    t2.d.update({"2": [7.5, "10"]})  # type: ignore
    assert t2.d[2] == [7.5, 10.0]
    assert t2 != t


def test_bare_type() -> None:
    x = ValidatedDict[int, list[float]]()
    x.update({"1": ["7.5"]})  # type: ignore
    assert x[1] == [7.5]
