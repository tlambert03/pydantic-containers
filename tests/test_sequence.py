from pydantic import BaseModel, ConfigDict, Field

from pydantic_containers import ValidatedList


def test_sequence() -> None:
    class T(BaseModel):
        x: ValidatedList[int] = Field(default_factory=list)
        # NOTE: it's currently critical that validate_default is used
        model_config = ConfigDict(validate_default=True)

    t = T()
    t.x.append("1")  # type: ignore
    assert 1 in t.x
    assert t.x[0] == 1

    js = t.model_dump_json()
    assert isinstance(js, str)
    t2 = T.model_validate_json(js)
    assert isinstance(t2, T)
    assert isinstance(t2.x, ValidatedList)
    assert t2 == t

    t2.x.append("2")  # type: ignore
    assert t2.x[1] == 2
    assert t2 != t
