"""Security package for pluggable verifiers and related utilities."""

# Entry point group name for verifiers and config prefix used in settings
ENTRY_POINT_GROUP = "genesis_core.verifiers"
VERIFIER_CONFIG_PREFIX = "verifiers."

__all__ = ["ENTRY_POINT_GROUP", "VERIFIER_CONFIG_PREFIX"]
