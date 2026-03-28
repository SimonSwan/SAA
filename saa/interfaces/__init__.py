"""Abstract interfaces for all SAA modules."""

from saa.interfaces.action import ActionSelectionInterface
from saa.interfaces.allostasis import AllostasisInterface
from saa.interfaces.base import BaseConfig, BaseModule, BaseState
from saa.interfaces.embodiment import EmbodimentInterface
from saa.interfaces.homeostasis import HomeostasisInterface
from saa.interfaces.interoception import InteroceptionInterface
from saa.interfaces.memory import MemoryInterface
from saa.interfaces.neuromodulation import NeuromodulationInterface
from saa.interfaces.observability import ObservabilityInterface
from saa.interfaces.self_model import SelfModelInterface
from saa.interfaces.social import SocialInterface
from saa.interfaces.valuation import ValuationInterface

__all__ = [
    "ActionSelectionInterface",
    "AllostasisInterface",
    "BaseConfig",
    "BaseModule",
    "BaseState",
    "EmbodimentInterface",
    "HomeostasisInterface",
    "InteroceptionInterface",
    "MemoryInterface",
    "NeuromodulationInterface",
    "ObservabilityInterface",
    "SelfModelInterface",
    "SocialInterface",
    "ValuationInterface",
]
