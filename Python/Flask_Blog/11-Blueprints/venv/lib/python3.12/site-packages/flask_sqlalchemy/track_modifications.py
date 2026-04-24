from __future__ import annotations

import typing as t

import sqlalchemy as sa
import sqlalchemy.event as sa_event
import sqlalchemy.orm as sa_orm
from flask import current_app
from flask import has_app_context
from flask.signals import Namespace  # type: ignore[attr-defined]

if t.TYPE_CHECKING:
    from .session import Session

_signals = Namespace()

models_committed = _signals.signal("models-committed")
"""This Blinker signal is sent after the session is committed if there were changed
models in the session.

The sender is the application that emitted the changes. The receiver is passed the
``changes`` argument with a list of tuples in the form ``(instance, operation)``.
The operations are ``"insert"``, ``"update"``, and ``"delete"``.
"""

before_models_committed = _signals.signal("before-models-committed")
"""This signal works exactly like :data:`models_committed` but is emitted before the
commit takes place.
"""


def _listen(session: sa_orm.scoped_session[Session]) -> None:
    sa_event.listen(session, "before_flush", _record_ops, named=True)
    sa_event.listen(session, "before_commit", _record_ops, named=True)
    sa_event.listen(session, "before_commit", _before_commit)
    sa_event.listen(session, "after_commit", _after_commit)
    sa_event.listen(session, "after_rollback", _after_rollback)


def _record_ops(session: Session, **kwargs: t.Any) -> None:
    if not has_app_context():
        return

    if not current_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]:
        return

    for targets, operation in (
        (session.new, "insert"),
        (session.dirty, "update"),
        (session.deleted, "delete"),
    ):
        for target in targets:
            state = sa.inspect(target)
            key = state.identity_key if state.has_identity else id(target)
            session._model_changes[key] = (target, operation)


def _before_commit(session: Session) -> None:
    if not has_app_context():
        return

    app = current_app._get_current_object()  # type: ignore[attr-defined]

    if not app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]:
        return

    if session._model_changes:
        changes = list(session._model_changes.values())
        before_models_committed.send(app, changes=changes)


def _after_commit(session: Session) -> None:
    if not has_app_context():
        return

    app = current_app._get_current_object()  # type: ignore[attr-defined]

    if not app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]:
        return

    if session._model_changes:
        changes = list(session._model_changes.values())
        models_committed.send(app, changes=changes)
        session._model_changes.clear()


def _after_rollback(session: Session) -> None:
    session._model_changes.clear()
