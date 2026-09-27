"""Custom exception classes for the tasklist evaluation framework."""


class TasklistEvalError(Exception):
    """Base exception for all tasklist-eval errors."""


class ConfigError(TasklistEvalError):
    """Raised when configuration is missing, invalid, or cannot be resolved."""


class TasklistParseError(TasklistEvalError):
    """Raised when a tasklist file cannot be read or is empty/unparseable."""


class PluginError(TasklistEvalError):
    """Raised when evaluator plugins cannot be discovered, imported, or registered."""
