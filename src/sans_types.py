"""
Type definitions for SANS webapp.

Contains TypedDicts used across the application for type hinting
and IDE support.
"""

from typing import TypedDict


class ParamInfo(TypedDict):
    """Parameter information from the fitter."""

    value: float
    min: float
    max: float
    vary: bool
    description: str | None


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
