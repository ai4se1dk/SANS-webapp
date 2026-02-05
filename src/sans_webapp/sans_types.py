"""
Type definitions for SANS webapp.

Contains TypedDicts used across the application for type hinting
and IDE support.
"""

from typing import Any, TypedDict


class ParamInfo(TypedDict):
    """Parameter information from the fitter."""

    value: float
    min: float
    max: float
    vary: bool
    description: str | None


class MCPToolResult(TypedDict, total=False):
    """Standardized MCP tool invocation result."""

    tool_name: str
    input: dict[str, Any]
    result: str
    success: bool


class ChatMessage(TypedDict, total=False):
    """Chat message structure including optional tool invocation details."""

    role: str
    content: str
    tool_invocations: list[MCPToolResult]

class FitParamInfo(TypedDict, total=False):
    """Fitted parameter information."""

    value: float
    stderr: float | str


class FitResult(TypedDict, total=False):
    """Fit result containing chi-squared and parameters."""

    chisq: float
    parameters: dict[str, FitParamInfo]


class ParamUpdate(TypedDict):
    """Parameter update to apply to the fitter."""

    value: float
    min: float
    max: float
    vary: bool


class PDUpdate(TypedDict):
    """Polydispersity update to apply to the fitter.

    Note: Uses 'pd_width' as key name for clarity in the webapp UI,
    which maps to the fitter's 'pd' parameter internally.
    """

    pd_width: float  # Maps to fitter's 'pd' parameter
    pd_n: int
    pd_type: str
    vary: bool
