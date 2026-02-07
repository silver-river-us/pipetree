"""Tests for the capability system."""

from pipetree.capability import Capability


class TestCapability:
    def test_capability_creation(self) -> None:
        cap = Capability(
            name="test_cap",
            requires={"a", "b"},
            provides={"c", "d"},
        )
        assert cap.name == "test_cap"
        assert cap.requires == frozenset({"a", "b"})
        assert cap.provides == frozenset({"c", "d"})

    def test_capability_immutable(self) -> None:
        cap = Capability(name="test", requires={"a"}, provides={"b"})
        # frozenset is immutable
        assert isinstance(cap.requires, frozenset)
        assert isinstance(cap.provides, frozenset)

    def test_validate_preconditions_satisfied(self) -> None:
        cap = Capability(name="test", requires={"a", "b"}, provides={"c"})
        assert cap.validate_preconditions({"a", "b", "x"}) is True

    def test_validate_preconditions_missing(self) -> None:
        cap = Capability(name="test", requires={"a", "b"}, provides={"c"})
        assert cap.validate_preconditions({"a"}) is False

    def test_validate_preconditions_empty_requires(self) -> None:
        cap = Capability(name="test", requires=set(), provides={"c"})
        assert cap.validate_preconditions(set()) is True

    def test_missing_requirements(self) -> None:
        cap = Capability(name="test", requires={"a", "b", "c"}, provides={"d"})
        missing = cap.missing_requirements({"a", "x"})
        assert missing == {"b", "c"}

    def test_missing_requirements_none_missing(self) -> None:
        cap = Capability(name="test", requires={"a", "b"}, provides={"c"})
        missing = cap.missing_requirements({"a", "b", "c"})
        assert missing == set()
