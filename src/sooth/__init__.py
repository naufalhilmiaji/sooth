"""Sooth — verify AI-generated text against source material."""

from sooth.claims import Claim, split_claims
from sooth.report import exit_code, log_record, render_markdown
from sooth.verify import MODEL, Verdict, VerifyError, map_verdict, verify_claims

__version__ = "0.1.0"

__all__ = [
    "MODEL",
    "Claim",
    "Verdict",
    "VerifyError",
    "__version__",
    "exit_code",
    "log_record",
    "map_verdict",
    "render_markdown",
    "split_claims",
    "verify_claims",
]
