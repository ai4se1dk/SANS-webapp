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
    """One entry of the ``parameters`` block of a sans-fitter fit result.

    sans-fitter >= 0.4 reports every model parameter, not only the varied ones.
    ``fixed`` is False only for the parameters the optimizer moved; ``linked_to``
    names the parameter a follower mirrors (``None`` for independent ones).
    """

    value: float
    stderr: float | str
    formatted: str
    fixed: bool
    linked_to: str | None


class FitResult(TypedDict, total=False):
    """Fit result dictionary returned by ``SANSFitter.fit()`` (sans-fitter >= 0.4).

    ``chisq`` is the raw weighted sum of squared residuals; ``reduced_chisq`` is
    ``chisq / dof`` (NaN when ``dof <= 0``). Before sans-fitter 0.4 the bumps
    engine stored χ²/dof under ``chisq``; the webapp displays ``reduced_chisq``.
    """

    engine: str
    method: str
    chisq: float
    reduced_chisq: float
    n_points: int
    n_free: int
    dof: int
    converged: bool | None
    message: str
    weighting_note: str
    cov: Any
    cov_labels: list[str]
    cov_source: str | None
    on_bounds: list[tuple[str, str]]
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
