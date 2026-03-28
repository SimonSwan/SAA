"""ModuleRegistry — plugin registration, discovery, and dependency management."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from saa.interfaces.base import BaseModule


class ModuleRegistry:
    """Central registry for SAA modules.

    Handles registration, dependency validation, and ordered retrieval
    for the simulation engine's tick loop.
    """

    # Canonical execution order for the tick loop
    EXECUTION_ORDER: list[str] = [
        "embodiment",
        "interoception",
        "homeostasis",
        "allostasis",
        "neuromodulation",
        "self_model",
        "memory",
        "valuation",
        "social",
        "action",
        "observability",
    ]

    def __init__(self) -> None:
        self._modules: dict[str, BaseModule] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def register(self, name: str, module: BaseModule) -> None:
        """Register a module instance under the given name."""
        self._modules[name] = module
        self._metadata[name] = {
            "version": getattr(module, "VERSION", "0.0.0"),
            "capabilities": getattr(module, "CAPABILITIES", []),
            "dependencies": getattr(module, "DEPENDENCIES", []),
        }

    def get(self, name: str) -> BaseModule:
        """Retrieve a registered module by name."""
        if name not in self._modules:
            raise KeyError(f"Module '{name}' is not registered")
        return self._modules[name]

    def has(self, name: str) -> bool:
        return name in self._modules

    def get_ordered_modules(self) -> list[tuple[str, BaseModule]]:
        """Return modules in canonical execution order.

        Modules not in EXECUTION_ORDER are appended at the end.
        """
        ordered: list[tuple[str, BaseModule]] = []
        for name in self.EXECUTION_ORDER:
            if name in self._modules:
                ordered.append((name, self._modules[name]))
        # Append any extra modules not in the canonical order
        for name, mod in self._modules.items():
            if name not in self.EXECUTION_ORDER:
                ordered.append((name, mod))
        return ordered

    def validate_dependencies(self) -> list[str]:
        """Check that all module dependencies are satisfied.

        Returns a list of error messages (empty if all OK).
        """
        errors: list[str] = []
        for name, meta in self._metadata.items():
            for dep in meta.get("dependencies", []):
                if dep not in self._modules:
                    errors.append(f"Module '{name}' depends on '{dep}' which is not registered")
        return errors

    @property
    def module_names(self) -> list[str]:
        return list(self._modules.keys())

    def get_metadata(self, name: str) -> dict[str, Any]:
        return self._metadata.get(name, {})

    def unregister(self, name: str) -> None:
        """Remove a module from the registry."""
        self._modules.pop(name, None)
        self._metadata.pop(name, None)
