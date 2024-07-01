def test_readme() -> None:
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
