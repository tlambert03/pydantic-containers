from pydantic import BaseModel, ConfigDict, Field

from pydantic_containers import ValidatedSet


def test_sequence() -> None:
    class T(BaseModel):
        x: ValidatedSet[int] = Field(default_factory=list)
        # NOTE: it's currently critical that validate_default is used
        model_config = ConfigDict(validate_default=True)

    t = T()
    t.x.add("1")  # type: ignore
    assert 1 in t.x
    assert tuple(t.x) == (1,)

    js = t.model_dump_json()
    assert isinstance(js, str)
    t2 = T.model_validate_json(js)
    assert isinstance(t2, T)
    assert isinstance(t2.x, ValidatedSet)
    assert t2 == t

    t2.x.add("2")  # type: ignore
    assert tuple(t2.x) == (1, 2)
    assert t2 != t
