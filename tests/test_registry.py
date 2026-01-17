"""Tests for the registry system."""

import pytest

from ingestion.capability import Capability
from ingestion.registry import Registry, global_registry, register
from ingestion.step import BaseStep
from ingestion.types import Ctx


class TestRegistry:
    def test_register_and_make(self) -> None:
        registry = Registry()
        cap = Capability(name="test", requires=set(), provides={"result"})

        class TestStep(BaseStep):
            def __init__(self, value: int) -> None:
                super().__init__(cap, "test_step")
                self.value = value

            def run(self, ctx: Ctx) -> Ctx:
                ctx["result"] = self.value
                return ctx

        registry.register("test", "impl_a", lambda value=10: TestStep(value))

        step = registry.make("test", "impl_a", value=42)
        assert isinstance(step, TestStep)
        assert step.value == 42

    def test_list_capabilities(self) -> None:
        registry = Registry()

        def factory() -> BaseStep:
            raise NotImplementedError

        registry.register("cap1", "impl1", factory)
        registry.register("cap2", "impl1", factory)

        caps = registry.list_capabilities()
        assert set(caps) == {"cap1", "cap2"}

    def test_list_impls(self) -> None:
        registry = Registry()

        def factory() -> BaseStep:
            raise NotImplementedError

        registry.register("cap1", "impl_a", factory)
        registry.register("cap1", "impl_b", factory)
        registry.register("cap1", "impl_c", factory)

        impls = registry.list_impls("cap1")
        assert set(impls) == {"impl_a", "impl_b", "impl_c"}

    def test_list_impls_unknown_cap(self) -> None:
        registry = Registry()
        assert registry.list_impls("unknown") == []

    def test_get_factory_unknown_cap(self) -> None:
        registry = Registry()
        with pytest.raises(KeyError, match="Unknown capability"):
            registry.get_factory("unknown", "impl")

    def test_get_factory_unknown_impl(self) -> None:
        registry = Registry()

        def factory() -> BaseStep:
            raise NotImplementedError

        registry.register("cap1", "known", factory)

        with pytest.raises(KeyError, match="Unknown implementation"):
            registry.get_factory("cap1", "unknown")

    def test_unregister(self) -> None:
        registry = Registry()

        def factory() -> BaseStep:
            raise NotImplementedError

        registry.register("cap1", "impl1", factory)
        registry.unregister("cap1", "impl1")

        assert registry.list_impls("cap1") == []

    def test_decorator(self) -> None:
        registry = Registry()
        cap = Capability(name="test", requires=set(), provides=set())

        @registry.decorator("test_cap", "decorated_impl")
        def create_step() -> BaseStep:
            class DecoratedStep(BaseStep):
                def run(self, ctx: Ctx) -> Ctx:
                    return ctx

            return DecoratedStep(cap, "decorated")

        assert "decorated_impl" in registry.list_impls("test_cap")


class TestGlobalRegistry:
    def test_global_registry_exists(self) -> None:
        assert global_registry is not None

    def test_register_decorator(self) -> None:
        cap = Capability(name="global_test", requires=set(), provides=set())

        @register("global_test_cap", "global_impl")
        def create_step() -> BaseStep:
            class GlobalStep(BaseStep):
                def run(self, ctx: Ctx) -> Ctx:
                    return ctx

            return GlobalStep(cap, "global")

        assert "global_impl" in global_registry.list_impls("global_test_cap")

        # Cleanup
        global_registry.unregister("global_test_cap", "global_impl")
