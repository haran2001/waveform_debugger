"""Agent prompts for the chip design system."""

from .architect_prompt import ARCHITECT_SYSTEM_PROMPT
from .entity_prompt import ENTITY_SYSTEM_PROMPT
from .rtl_prompt import RTL_SYSTEM_PROMPT
from .dv_prompt import DV_SYSTEM_PROMPT
from .verify_prompt import VERIFY_SYSTEM_PROMPT
from .synthesis_prompt import SYNTHESIS_SYSTEM_PROMPT

__all__ = [
    "ARCHITECT_SYSTEM_PROMPT",
    "ENTITY_SYSTEM_PROMPT",
    "RTL_SYSTEM_PROMPT",
    "DV_SYSTEM_PROMPT",
    "VERIFY_SYSTEM_PROMPT",
    "SYNTHESIS_SYSTEM_PROMPT",
]
