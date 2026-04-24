from __future__ import annotations

import typing as t

import sqlalchemy as sa
import sqlalchemy.exc as sa_exc
import sqlalchemy.orm as sa_orm
from flask.globals import app_ctx

if t.TYPE_CHECKING:
    from .extension import SQLAlchemy


class Session(sa_orm.Session):
    """A SQLAlchemy :class:`~sqlalchemy.orm.Session` class that chooses what engine to
    use based on the bind key associated with the metadata associated with the thing
    being queried.

    To customize ``db.session``, subclass this and pass it as the ``class_`` key in the
    ``session_options`` to :class:`.SQLAlchemy`.

    .. versionchanged:: 3.0
        Renamed from ``SignallingSession``.
    """

    def __init__(self, db: SQLAlchemy, **kwargs: t.Any) -> None:
        super().__init__(**kwargs)
        self._db = db
        self._model_changes: dict[object, tuple[t.Any, str]] = {}

    def get_bind(
        self,
        mapper: t.Any | None = None,
        clause: t.Any | None = None,
        bind: sa.engine.Engine | sa.engine.Connection | None = None,
        **kwargs: t.Any,
    ) -> sa.engine.Engine | sa.engine.Connection:
        """Select an engine based on the ``bind_key`` of the metadata associated with
        the model or table being queried. If no bind key is set, uses the default bind.

        .. versionchanged:: 3.0.3
            Fix finding the bind for a joined inheritance model.

        .. versionchanged:: 3.0
            The implementation more closely matches the base SQLAlchemy implementation.

        .. versionchanged:: 2.1
            Support joining an external transaction.
        """
        if bind is not None:
            return bind

        engines = self._db.engines

        if mapper is not None:
            try:
                mapper = sa.inspect(mapper)
            except sa_exc.NoInspectionAvailable as e:
                if isinstance(mapper, type):
                    raise sa_orm.exc.UnmappedClassError(mapper) from e

                raise

            engine = _clause_to_engine(mapper.local_table, engines)

            if engine is not None:
                return engine

        if clause is not None:
            engine = _clause_to_engine(clause, engines)

            if engine is not None:
                return engine

        if None in engines:
            return engines[None]

        return super().get_bind(mapper=mapper, clause=clause, bind=bind, **kwargs)


def _clause_to_engine(
    clause: sa.ClauseElement | None,
    engines: t.Mapping[str | None, sa.engine.Engine],
) -> sa.engine.Engine | None:
    """If the clause is a table, return the engine associated with the table's
    metadata's bind key.
    """
    table = None

    if clause is not None:
        if isinstance(clause, sa.Table):
            table = clause
        elif isinstance(clause, sa.UpdateBase) and isinstance(clause.table, sa.Table):
            table = clause.table

    if table is not None and "bind_key" in table.metadata.info:
        key = table.metadata.info["bind_key"]

        if key not in engines:
            raise sa_exc.UnboundExecutionError(
                f"Bind key '{key}' is not in 'SQLALCHEMY_BINDS' config."
            )

        return engines[key]

    return None


def _app_ctx_id() -> int:
    """Get the id of the current Flask application context for the session scope."""
    return id(app_ctx._get_current_object())  # type: ignore[attr-defined]
