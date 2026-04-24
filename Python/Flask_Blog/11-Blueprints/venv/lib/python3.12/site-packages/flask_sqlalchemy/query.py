from __future__ import annotations

import typing as t

import sqlalchemy.exc as sa_exc
import sqlalchemy.orm as sa_orm
from flask import abort

from .pagination import Pagination
from .pagination import QueryPagination


class Query(sa_orm.Query):  # type: ignore[type-arg]
    """SQLAlchemy :class:`~sqlalchemy.orm.query.Query` subclass with some extra methods
    useful for querying in a web application.

    This is the default query class for :attr:`.Model.query`.

    .. versionchanged:: 3.0
        Renamed to ``Query`` from ``BaseQuery``.
    """

    def get_or_404(self, ident: t.Any, description: str | None = None) -> t.Any:
        """Like :meth:`~sqlalchemy.orm.Query.get` but aborts with a ``404 Not Found``
        error instead of returning ``None``.

        :param ident: The primary key to query.
        :param description: A custom message to show on the error page.
        """
        rv = self.get(ident)

        if rv is None:
            abort(404, description=description)

        return rv

    def first_or_404(self, description: str | None = None) -> t.Any:
        """Like :meth:`~sqlalchemy.orm.Query.first` but aborts with a ``404 Not Found``
        error instead of returning ``None``.

        :param description: A custom message to show on the error page.
        """
        rv = self.first()

        if rv is None:
            abort(404, description=description)

        return rv

    def one_or_404(self, description: str | None = None) -> t.Any:
        """Like :meth:`~sqlalchemy.orm.Query.one` but aborts with a ``404 Not Found``
        error instead of raising ``NoResultFound`` or ``MultipleResultsFound``.

        :param description: A custom message to show on the error page.

        .. versionadded:: 3.0
        """
        try:
            return self.one()
        except (sa_exc.NoResultFound, sa_exc.MultipleResultsFound):
            abort(404, description=description)

    def paginate(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        max_per_page: int | None = None,
        error_out: bool = True,
        count: bool = True,
    ) -> Pagination:
        """Apply an offset and limit to the query based on the current page and number
        of items per page, returning a :class:`.Pagination` object.

        :param page: The current page, used to calculate the offset. Defaults to the
            ``page`` query arg during a request, or 1 otherwise.
        :param per_page: The maximum number of items on a page, used to calculate the
            offset and limit. Defaults to the ``per_page`` query arg during a request,
            or 20 otherwise.
        :param max_per_page: The maximum allowed value for ``per_page``, to limit a
            user-provided value. Use ``None`` for no limit. Defaults to 100.
        :param error_out: Abort with a ``404 Not Found`` error if no items are returned
            and ``page`` is not 1, or if ``page`` or ``per_page`` is less than 1, or if
            either are not ints.
        :param count: Calculate the total number of values by issuing an extra count
            query. For very complex queries this may be inaccurate or slow, so it can be
            disabled and set manually if necessary.

        .. versionchanged:: 3.0
            All parameters are keyword-only.

        .. versionchanged:: 3.0
            The ``count`` query is more efficient.

        .. versionchanged:: 3.0
            ``max_per_page`` defaults to 100.
        """
        return QueryPagination(
            query=self,
            page=page,
            per_page=per_page,
            max_per_page=max_per_page,
            error_out=error_out,
            count=count,
        )
