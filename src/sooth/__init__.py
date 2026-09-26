"""Sooth — verify AI-generated text against source material."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from sooth.claims import Claim, split_claims
from sooth.report import (
    exit_code,
    log_record,
    render_json,
    render_markdown,
    render_plain,
)
from sooth.verify import MODEL, Verdict, VerifyError, map_verdict, verify_claims

try:  # single source of truth: the installed distribution metadata
    __version__ = _pkg_version("sooth")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0+unknown"

__all__ = [
    "MODEL",
    "Claim",
    "Verdict",
    "VerifyError",
    "__version__",
    "exit_code",
    "log_record",
    "map_verdict",
    "render_json",
    "render_markdown",
    "render_plain",
    "split_claims",
    "verify_claims",
]
