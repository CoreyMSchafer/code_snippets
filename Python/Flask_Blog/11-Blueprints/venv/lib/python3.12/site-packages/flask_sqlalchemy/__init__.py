from __future__ import annotations

import typing as t

from .extension import SQLAlchemy

__all__ = [
    "SQLAlchemy",
]


def __getattr__(name: str) -> t.Any:
    if name == "__version__":
        import importlib.metadata
        import warnings

        warnings.warn(
            "The '__version__' attribute is deprecated and will be removed in"
            " Flask-SQLAlchemy 3.2. Use feature detection or"
            " 'importlib.metadata.version(\"flask-sqlalchemy\")' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return importlib.metadata.version("flask-sqlalchemy")

    raise AttributeError(name)
