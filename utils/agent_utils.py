"""Compatibility imports for the original utility module.

New code should import from :mod:`agent_governance.prompt`.
"""

from agent_governance.prompt import Section, generate_prompt, parse_system_prompt

__all__ = ["Section", "generate_prompt", "parse_system_prompt"]
