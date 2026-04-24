from __future__ import annotations

import os
import types
import typing as t
import warnings
from weakref import WeakKeyDictionary

import sqlalchemy as sa
import sqlalchemy.event as sa_event
import sqlalchemy.exc as sa_exc
import sqlalchemy.orm as sa_orm
from flask import abort
from flask import current_app
from flask import Flask
from flask import has_app_context

from .model import _QueryProperty
from .model import BindMixin
from .model import DefaultMeta
from .model import DefaultMetaNoName
from .model import Model
from .model import NameMixin
from .pagination import Pagination
from .pagination import SelectPagination
from .query import Query
from .session import _app_ctx_id
from .session import Session
from .table import _Table

_O = t.TypeVar("_O", bound=object)  # Based on sqlalchemy.orm._typing.py


# Type accepted for model_class argument
_FSA_MCT = t.TypeVar(
    "_FSA_MCT",
    bound=t.Union[
        t.Type[Model],
        sa_orm.DeclarativeMeta,
        t.Type[sa_orm.DeclarativeBase],
        t.Type[sa_orm.DeclarativeBaseNoMeta],
    ],
)


# Type returned by make_declarative_base
class _FSAModel(Model):
    metadata: sa.MetaData


def _get_2x_declarative_bases(
    model_class: _FSA_MCT,
) -> list[t.Type[t.Union[sa_orm.DeclarativeBase, sa_orm.DeclarativeBaseNoMeta]]]:
    return [
        b
        for b in model_class.__bases__
        if issubclass(b, (sa_orm.DeclarativeBase, sa_orm.DeclarativeBaseNoMeta))
    ]


class SQLAlchemy:
    """Integrates SQLAlchemy with Flask. This handles setting up one or more engines,
    associating tables and models with specific engines, and cleaning up connections and
    sessions after each request.

    Only the engine configuration is specific to each application, other things like
    the model, table, metadata, and session are shared for all applications using that
    extension instance. Call :meth:`init_app` to configure the extension on an
    application.

    After creating the extension, create model classes by subclassing :attr:`Model`, and
    table classes with :attr:`Table`. These can be accessed before :meth:`init_app` is
    called, making it possible to define the models separately from the application.

    Accessing :attr:`session` and :attr:`engine` requires an active Flask application
    context. This includes methods like :meth:`create_all` which use the engine.

    This class also provides access to names in SQLAlchemy's ``sqlalchemy`` and
    ``sqlalchemy.orm`` modules. For example, you can use ``db.Column`` and
    ``db.relationship`` instead of importing ``sqlalchemy.Column`` and
    ``sqlalchemy.orm.relationship``. This can be convenient when defining models.

    :param app: Call :meth:`init_app` on this Flask application now.
    :param metadata: Use this as the default :class:`sqlalchemy.schema.MetaData`. Useful
        for setting a naming convention.
    :param session_options: Arguments used by :attr:`session` to create each session
        instance. A ``scopefunc`` key will be passed to the scoped session, not the
        session instance. See :class:`sqlalchemy.orm.sessionmaker` for a list of
        arguments.
    :param query_class: Use this as the default query class for models and dynamic
        relationships. The query interface is considered legacy in SQLAlchemy.
    :param model_class: Use this as the model base class when creating the declarative
        model class :attr:`Model`. Can also be a fully created declarative model class
        for further customization.
    :param engine_options: Default arguments used when creating every engine. These are
        lower precedence than application config. See :func:`sqlalchemy.create_engine`
        for a list of arguments.
    :param add_models_to_shell: Add the ``db`` instance and all model classes to
        ``flask shell``.

    .. versionchanged:: 3.1.0
        The ``metadata`` parameter can still be used with SQLAlchemy 1.x classes,
        but is ignored when using SQLAlchemy 2.x style of declarative classes.
        Instead, specify metadata on your Base class.

    .. versionchanged:: 3.1.0
        Added the ``disable_autonaming`` parameter.

    .. versionchanged:: 3.1.0
        Changed ``model_class`` parameter to accepta SQLAlchemy 2.x
        declarative base subclass.

    .. versionchanged:: 3.0
        An active Flask application context is always required to access ``session`` and
        ``engine``.

    .. versionchanged:: 3.0
        Separate ``metadata`` are used for each bind key.

    .. versionchanged:: 3.0
        The ``engine_options`` parameter is applied as defaults before per-engine
        configuration.

    .. versionchanged:: 3.0
        The session class can be customized in ``session_options``.

    .. versionchanged:: 3.0
        Added the ``add_models_to_shell`` parameter.

    .. versionchanged:: 3.0
        Engines are created when calling ``init_app`` rather than the first time they
        are accessed.

    .. versionchanged:: 3.0
        All parameters except ``app`` are keyword-only.

    .. versionchanged:: 3.0
        The extension instance is stored directly as ``app.extensions["sqlalchemy"]``.

    .. versionchanged:: 3.0
        Setup methods are renamed with a leading underscore. They are considered
        internal interfaces which may change at any time.

    .. versionchanged:: 3.0
        Removed the ``use_native_unicode`` parameter and config.

    .. versionchanged:: 2.4
        Added the ``engine_options`` parameter.

    .. versionchanged:: 2.1
        Added the ``metadata``, ``query_class``, and ``model_class`` parameters.

    .. versionchanged:: 2.1
        Use the same query class across ``session``, ``Model.query`` and
        ``Query``.

    .. versionchanged:: 0.16
        ``scopefunc`` is accepted in ``session_options``.

    .. versionchanged:: 0.10
        Added the ``session_options`` parameter.
    """

    def __init__(
        self,
        app: Flask | None = None,
        *,
        metadata: sa.MetaData | None = None,
        session_options: dict[str, t.Any] | None = None,
        query_class: type[Query] = Query,
        model_class: _FSA_MCT = Model,  # type: ignore[assignment]
        engine_options: dict[str, t.Any] | None = None,
        add_models_to_shell: bool = True,
        disable_autonaming: bool = False,
    ):
        if session_options is None:
            session_options = {}

        self.Query = query_class
        """The default query class used by ``Model.query`` and ``lazy="dynamic"``
        relationships.

        .. warning::
            The query interface is considered legacy in SQLAlchemy.

        Customize this by passing the ``query_class`` parameter to the extension.
        """

        self.session = self._make_scoped_session(session_options)
        """A :class:`sqlalchemy.orm.scoping.scoped_session` that creates instances of
        :class:`.Session` scoped to the current Flask application context. The session
        will be removed, returning the engine connection to the pool, when the
        application context exits.

        Customize this by passing ``session_options`` to the extension.

        This requires that a Flask application context is active.

        .. versionchanged:: 3.0
            The session is scoped to the current app context.
        """

        self.metadatas: dict[str | None, sa.MetaData] = {}
        """Map of bind keys to :class:`sqlalchemy.schema.MetaData` instances. The
        ``None`` key refers to the default metadata, and is available as
        :attr:`metadata`.

        Customize the default metadata by passing the ``metadata`` parameter to the
        extension. This can be used to set a naming convention. When metadata for
        another bind key is created, it copies the default's naming convention.

        .. versionadded:: 3.0
        """

        if metadata is not None:
            if len(_get_2x_declarative_bases(model_class)) > 0:
                warnings.warn(
                    "When using SQLAlchemy 2.x style of declarative classes,"
                    " the `metadata` should be an attribute of the base class."
                    "The metadata passed into SQLAlchemy() is ignored.",
                    DeprecationWarning,
                    stacklevel=2,
                )
            else:
                metadata.info["bind_key"] = None
                self.metadatas[None] = metadata

        self.Table = self._make_table_class()
        """A :class:`sqlalchemy.schema.Table` class that chooses a metadata
        automatically.

        Unlike the base ``Table``, the ``metadata`` argument is not required. If it is
        not given, it is selected based on the ``bind_key`` argument.

        :param bind_key: Used to select a different metadata.
        :param args: Arguments passed to the base class. These are typically the table's
            name, columns, and constraints.
        :param kwargs: Arguments passed to the base class.

        .. versionchanged:: 3.0
            This is a subclass of SQLAlchemy's ``Table`` rather than a function.
        """

        self.Model = self._make_declarative_base(
            model_class, disable_autonaming=disable_autonaming
        )
        """A SQLAlchemy declarative model class. Subclass this to define database
        models.

        If a model does not set ``__tablename__``, it will be generated by converting
        the class name from ``CamelCase`` to ``snake_case``. It will not be generated
        if the model looks like it uses single-table inheritance.

        If a model or parent class sets ``__bind_key__``, it will use that metadata and
        database engine. Otherwise, it will use the default :attr:`metadata` and
        :attr:`engine`. This is ignored if the model sets ``metadata`` or ``__table__``.

        For code using the SQLAlchemy 1.x API, customize this model by subclassing
        :class:`.Model` and passing the ``model_class`` parameter to the extension.
        A fully created declarative model class can be
        passed as well, to use a custom metaclass.

        For code using the SQLAlchemy 2.x API, customize this model by subclassing
        :class:`sqlalchemy.orm.DeclarativeBase` or
        :class:`sqlalchemy.orm.DeclarativeBaseNoMeta`
        and passing the ``model_class`` parameter to the extension.
        """

        if engine_options is None:
            engine_options = {}

        self._engine_options = engine_options
        self._app_engines: WeakKeyDictionary[Flask, dict[str | None, sa.engine.Engine]]
        self._app_engines = WeakKeyDictionary()
        self._add_models_to_shell = add_models_to_shell

        if app is not None:
            self.init_app(app)

    def __repr__(self) -> str:
        if not has_app_context():
            return f"<{type(self).__name__}>"

        message = f"{type(self).__name__} {self.engine.url}"

        if len(self.engines) > 1:
            message = f"{message} +{len(self.engines) - 1}"

        return f"<{message}>"

    def init_app(self, app: Flask) -> None:
        """Initialize a Flask application for use with this extension instance. This
        must be called before accessing the database engine or session with the app.

        This sets default configuration values, then configures the extension on the
        application and creates the engines for each bind key. Therefore, this must be
        called after the application has been configured. Changes to application config
        after this call will not be reflected.

        The following keys from ``app.config`` are used:

        - :data:`.SQLALCHEMY_DATABASE_URI`
        - :data:`.SQLALCHEMY_ENGINE_OPTIONS`
        - :data:`.SQLALCHEMY_ECHO`
        - :data:`.SQLALCHEMY_BINDS`
        - :data:`.SQLALCHEMY_RECORD_QUERIES`
        - :data:`.SQLALCHEMY_TRACK_MODIFICATIONS`

        :param app: The Flask application to initialize.
        """
        if "sqlalchemy" in app.extensions:
            raise RuntimeError(
                "A 'SQLAlchemy' instance has already been registered on this Flask app."
                " Import and use that instance instead."
            )

        app.extensions["sqlalchemy"] = self
        app.teardown_appcontext(self._teardown_session)

        if self._add_models_to_shell:
            from .cli import add_models_to_shell

            app.shell_context_processor(add_models_to_shell)

        basic_uri: str | sa.engine.URL | None = app.config.setdefault(
            "SQLALCHEMY_DATABASE_URI", None
        )
        basic_engine_options = self._engine_options.copy()
        basic_engine_options.update(
            app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {})
        )
        echo: bool = app.config.setdefault("SQLALCHEMY_ECHO", False)
        config_binds: dict[
            str | None, str | sa.engine.URL | dict[str, t.Any]
        ] = app.config.setdefault("SQLALCHEMY_BINDS", {})
        engine_options: dict[str | None, dict[str, t.Any]] = {}

        # Build the engine config for each bind key.
        for key, value in config_binds.items():
            engine_options[key] = self._engine_options.copy()

            if isinstance(value, (str, sa.engine.URL)):
                engine_options[key]["url"] = value
            else:
                engine_options[key].update(value)

        # Build the engine config for the default bind key.
        if basic_uri is not None:
            basic_engine_options["url"] = basic_uri

        if "url" in basic_engine_options:
            engine_options.setdefault(None, {}).update(basic_engine_options)

        if not engine_options:
            raise RuntimeError(
                "Either 'SQLALCHEMY_DATABASE_URI' or 'SQLALCHEMY_BINDS' must be set."
            )

        engines = self._app_engines.setdefault(app, {})

        # Dispose existing engines in case init_app is called again.
        if engines:
            for engine in engines.values():
                engine.dispose()

            engines.clear()

        # Create the metadata and engine for each bind key.
        for key, options in engine_options.items():
            self._make_metadata(key)
            options.setdefault("echo", echo)
            options.setdefault("echo_pool", echo)
            self._apply_driver_defaults(options, app)
            engines[key] = self._make_engine(key, options, app)

        if app.config.setdefault("SQLALCHEMY_RECORD_QUERIES", False):
            from . import record_queries

            for engine in engines.values():
                record_queries._listen(engine)

        if app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False):
            from . import track_modifications

            track_modifications._listen(self.session)

    def _make_scoped_session(
        self, options: dict[str, t.Any]
    ) -> sa_orm.scoped_session[Session]:
        """Create a :class:`sqlalchemy.orm.scoping.scoped_session` around the factory
        from :meth:`_make_session_factory`. The result is available as :attr:`session`.

        The scope function can be customized using the ``scopefunc`` key in the
        ``session_options`` parameter to the extension. By default it uses the current
        thread or greenlet id.

        This method is used for internal setup. Its signature may change at any time.

        :meta private:

        :param options: The ``session_options`` parameter from ``__init__``. Keyword
            arguments passed to the session factory. A ``scopefunc`` key is popped.

        .. versionchanged:: 3.0
            The session is scoped to the current app context.

        .. versionchanged:: 3.0
            Renamed from ``create_scoped_session``, this method is internal.
        """
        scope = options.pop("scopefunc", _app_ctx_id)
        factory = self._make_session_factory(options)
        return sa_orm.scoped_session(factory, scope)

    def _make_session_factory(
        self, options: dict[str, t.Any]
    ) -> sa_orm.sessionmaker[Session]:
        """Create the SQLAlchemy :class:`sqlalchemy.orm.sessionmaker` used by
        :meth:`_make_scoped_session`.

        To customize, pass the ``session_options`` parameter to :class:`SQLAlchemy`. To
        customize the session class, subclass :class:`.Session` and pass it as the
        ``class_`` key.

        This method is used for internal setup. Its signature may change at any time.

        :meta private:

        :param options: The ``session_options`` parameter from ``__init__``. Keyword
            arguments passed to the session factory.

        .. versionchanged:: 3.0
            The session class can be customized.

        .. versionchanged:: 3.0
            Renamed from ``create_session``, this method is internal.
        """
        options.setdefault("class_", Session)
        options.setdefault("query_cls", self.Query)
        return sa_orm.sessionmaker(db=self, **options)

    def _teardown_session(self, exc: BaseException | None) -> None:
        """Remove the current session at the end of the request.

        :meta private:

        .. versionadded:: 3.0
        """
        self.session.remove()

    def _make_metadata(self, bind_key: str | None) -> sa.MetaData:
        """Get or create a :class:`sqlalchemy.schema.MetaData` for the given bind key.

        This method is used for internal setup. Its signature may change at any time.

        :meta private:

        :param bind_key: The name of the metadata being created.

        .. versionadded:: 3.0
        """
        if bind_key in self.metadatas:
            return self.metadatas[bind_key]

        if bind_key is not None:
            # Copy the naming convention from the default metadata.
            naming_convention = self._make_metadata(None).naming_convention
        else:
            naming_convention = None

        # Set the bind key in info to be used by session.get_bind.
        metadata = sa.MetaData(
            naming_convention=naming_convention, info={"bind_key": bind_key}
        )
        self.metadatas[bind_key] = metadata
        return metadata

    def _make_table_class(self) -> type[_Table]:
        """Create a SQLAlchemy :class:`sqlalchemy.schema.Table` class that chooses a
        metadata automatically based on the ``bind_key``. The result is available as
        :attr:`Table`.

        This method is used for internal setup. Its signature may change at any time.

        :meta private:

        .. versionadded:: 3.0
        """

        class Table(_Table):
            def __new__(
                cls, *args: t.Any, bind_key: str | None = None, **kwargs: t.Any
            ) -> Table:
                # If a metadata arg is passed, go directly to the base Table. Also do
                # this for no args so the correct error is shown.
                if not args or (len(args) >= 2 and isinstance(args[1], sa.MetaData)):
                    return super().__new__(cls, *args, **kwargs)

                metadata = self._make_metadata(bind_key)
                return super().__new__(cls, *[args[0], metadata, *args[1:]], **kwargs)

        return Table

    def _make_declarative_base(
        self,
        model_class: _FSA_MCT,
        disable_autonaming: bool = False,
    ) -> t.Type[_FSAModel]:
        """Create a SQLAlchemy declarative model class. The result is available as
        :attr:`Model`.

        To customize, subclass :class:`.Model` and pass it as ``model_class`` to
        :class:`SQLAlchemy`. To customize at the metaclass level, pass an already
        created declarative model class as ``model_class``.

        This method is used for internal setup. Its signature may change at any time.

        :meta private:

        :param model_class: A model base class, or an already created declarative model
        class.

        :param disable_autonaming: Turns off automatic tablename generation in models.

        .. versionchanged:: 3.1.0
            Added support for passing SQLAlchemy 2.x base class as model class.
            Added optional ``disable_autonaming`` parameter.

        .. versionchanged:: 3.0
            Renamed with a leading underscore, this method is internal.

        .. versionchanged:: 2.3
            ``model`` can be an already created declarative model class.
        """
        model: t.Type[_FSAModel]
        declarative_bases = _get_2x_declarative_bases(model_class)
        if len(declarative_bases) > 1:
            # raise error if more than one declarative base is found
            raise ValueError(
                "Only one declarative base can be passed to SQLAlchemy."
                " Got: {}".format(model_class.__bases__)
            )
        elif len(declarative_bases) == 1:
            body = dict(model_class.__dict__)
            body["__fsa__"] = self
            mixin_classes = [BindMixin, NameMixin, Model]
            if disable_autonaming:
                mixin_classes.remove(NameMixin)
            model = types.new_class(
                "FlaskSQLAlchemyBase",
                (*mixin_classes, *model_class.__bases__),
                {"metaclass": type(declarative_bases[0])},
                lambda ns: ns.update(body),
            )
        elif not isinstance(model_class, sa_orm.DeclarativeMeta):
            metadata = self._make_metadata(None)
            metaclass = DefaultMetaNoName if disable_autonaming else DefaultMeta
            model = sa_orm.declarative_base(
                metadata=metadata, cls=model_class, name="Model", metaclass=metaclass
            )
        else:
            model = model_class  # type: ignore[assignment]

        if None not in self.metadatas:
            # Use the model's metadata as the default metadata.
            model.metadata.info["bind_key"] = None
            self.metadatas[None] = model.metadata
        else:
            # Use the passed in default metadata as the model's metadata.
            model.metadata = self.metadatas[None]

        model.query_class = self.Query
        model.query = _QueryProperty()  # type: ignore[assignment]
        model.__fsa__ = self
        return model

    def _apply_driver_defaults(self, options: dict[str, t.Any], app: Flask) -> None:
        """Apply driver-specific configuration to an engine.

        SQLite in-memory databases use ``StaticPool`` and disable ``check_same_thread``.
        File paths are relative to the app's :attr:`~flask.Flask.instance_path`,
        which is created if it doesn't exist.

        MySQL sets ``charset="utf8mb4"``, and ``pool_timeout`` defaults to 2 hours.

        This method is used for internal setup. Its signature may change at any time.

        :meta private:

        :param options: Arguments passed to the engine.
        :param app: The application that the engine configuration belongs to.

        .. versionchanged:: 3.0
            SQLite paths are relative to ``app.instance_path``. It does not use
            ``NullPool`` if ``pool_size`` is 0. Driver-level URIs are supported.

        .. versionchanged:: 3.0
            MySQL sets ``charset="utf8mb4". It does not set ``pool_size`` to 10. It
            does not set ``pool_recycle`` if not using a queue pool.

        .. versionchanged:: 3.0
            Renamed from ``apply_driver_hacks``, this method is internal. It does not
            return anything.

        .. versionchanged:: 2.5
            Returns ``(sa_url, options)``.
        """
        url = sa.engine.make_url(options["url"])

        if url.drivername in {"sqlite", "sqlite+pysqlite"}:
            if url.database is None or url.database in {"", ":memory:"}:
                options["poolclass"] = sa.pool.StaticPool

                if "connect_args" not in options:
                    options["connect_args"] = {}

                options["connect_args"]["check_same_thread"] = False
            else:
                # the url might look like sqlite:///file:path?uri=true
                is_uri = url.query.get("uri", False)

                if is_uri:
                    db_str = url.database[5:]
                else:
                    db_str = url.database

                if not os.path.isabs(db_str):
                    os.makedirs(app.instance_path, exist_ok=True)
                    db_str = os.path.join(app.instance_path, db_str)

                    if is_uri:
                        db_str = f"file:{db_str}"

                    options["url"] = url.set(database=db_str)
        elif url.drivername.startswith("mysql"):
            # set queue defaults only when using queue pool
            if (
                "pool_class" not in options
                or options["pool_class"] is sa.pool.QueuePool
            ):
                options.setdefault("pool_recycle", 7200)

            if "charset" not in url.query:
                options["url"] = url.update_query_dict({"charset": "utf8mb4"})

    def _make_engine(
        self, bind_key: str | None, options: dict[str, t.Any], app: Flask
    ) -> sa.engine.Engine:
        """Create the :class:`sqlalchemy.engine.Engine` for the given bind key and app.

        To customize, use :data:`.SQLALCHEMY_ENGINE_OPTIONS` or
        :data:`.SQLALCHEMY_BINDS` config. Pass ``engine_options`` to :class:`SQLAlchemy`
        to set defaults for all engines.

        This method is used for internal setup. Its signature may change at any time.

        :meta private:

        :param bind_key: The name of the engine being created.
        :param options: Arguments passed to the engine.
        :param app: The application that the engine configuration belongs to.

        .. versionchanged:: 3.0
            Renamed from ``create_engine``, this method is internal.
        """
        return sa.engine_from_config(options, prefix="")

    @property
    def metadata(self) -> sa.MetaData:
        """The default metadata used by :attr:`Model` and :attr:`Table` if no bind key
        is set.
        """
        return self.metadatas[None]

    @property
    def engines(self) -> t.Mapping[str | None, sa.engine.Engine]:
        """Map of bind keys to :class:`sqlalchemy.engine.Engine` instances for current
        application. The ``None`` key refers to the default engine, and is available as
        :attr:`engine`.

        To customize, set the :data:`.SQLALCHEMY_BINDS` config, and set defaults by
        passing the ``engine_options`` parameter to the extension.

        This requires that a Flask application context is active.

        .. versionadded:: 3.0
        """
        app = current_app._get_current_object()  # type: ignore[attr-defined]

        if app not in self._app_engines:
            raise RuntimeError(
                "The current Flask app is not registered with this 'SQLAlchemy'"
                " instance. Did you forget to call 'init_app', or did you create"
                " multiple 'SQLAlchemy' instances?"
            )

        return self._app_engines[app]

    @property
    def engine(self) -> sa.engine.Engine:
        """The default :class:`~sqlalchemy.engine.Engine` for the current application,
        used by :attr:`session` if the :attr:`Model` or :attr:`Table` being queried does
        not set a bind key.

        To customize, set the :data:`.SQLALCHEMY_ENGINE_OPTIONS` config, and set
        defaults by passing the ``engine_options`` parameter to the extension.

        This requires that a Flask application context is active.
        """
        return self.engines[None]

    def get_engine(
        self, bind_key: str | None = None, **kwargs: t.Any
    ) -> sa.engine.Engine:
        """Get the engine for the given bind key for the current application.
        This requires that a Flask application context is active.

        :param bind_key: The name of the engine.

        .. deprecated:: 3.0
            Will be removed in Flask-SQLAlchemy 3.2. Use ``engines[key]`` instead.

        .. versionchanged:: 3.0
            Renamed the ``bind`` parameter to ``bind_key``. Removed the ``app``
            parameter.
        """
        warnings.warn(
            "'get_engine' is deprecated and will be removed in Flask-SQLAlchemy"
            " 3.2. Use 'engine' or 'engines[key]' instead. If you're using"
            " Flask-Migrate or Alembic, you'll need to update your 'env.py' file.",
            DeprecationWarning,
            stacklevel=2,
        )

        if "bind" in kwargs:
            bind_key = kwargs.pop("bind")

        return self.engines[bind_key]

    def get_or_404(
        self,
        entity: type[_O],
        ident: t.Any,
        *,
        description: str | None = None,
        **kwargs: t.Any,
    ) -> _O:
        """Like :meth:`session.get() <sqlalchemy.orm.Session.get>` but aborts with a
        ``404 Not Found`` error instead of returning ``None``.

        :param entity: The model class to query.
        :param ident: The primary key to query.
        :param description: A custom message to show on the error page.
        :param kwargs: Extra arguments passed to ``session.get()``.

        .. versionchanged:: 3.1
            Pass extra keyword arguments to ``session.get()``.

        .. versionadded:: 3.0
        """
        value = self.session.get(entity, ident, **kwargs)

        if value is None:
            abort(404, description=description)

        return value

    def first_or_404(
        self, statement: sa.sql.Select[t.Any], *, description: str | None = None
    ) -> t.Any:
        """Like :meth:`Result.scalar() <sqlalchemy.engine.Result.scalar>`, but aborts
        with a ``404 Not Found`` error instead of returning ``None``.

        :param statement: The ``select`` statement to execute.
        :param description: A custom message to show on the error page.

        .. versionadded:: 3.0
        """
        value = self.session.execute(statement).scalar()

        if value is None:
            abort(404, description=description)

        return value

    def one_or_404(
        self, statement: sa.sql.Select[t.Any], *, description: str | None = None
    ) -> t.Any:
        """Like :meth:`Result.scalar_one() <sqlalchemy.engine.Result.scalar_one>`,
        but aborts with a ``404 Not Found`` error instead of raising ``NoResultFound``
        or ``MultipleResultsFound``.

        :param statement: The ``select`` statement to execute.
        :param description: A custom message to show on the error page.

        .. versionadded:: 3.0
        """
        try:
            return self.session.execute(statement).scalar_one()
        except (sa_exc.NoResultFound, sa_exc.MultipleResultsFound):
            abort(404, description=description)

    def paginate(
        self,
        select: sa.sql.Select[t.Any],
        *,
        page: int | None = None,
        per_page: int | None = None,
        max_per_page: int | None = None,
        error_out: bool = True,
        count: bool = True,
    ) -> Pagination:
        """Apply an offset and limit to a select statment based on the current page and
        number of items per page, returning a :class:`.Pagination` object.

        The statement should select a model class, like ``select(User)``. This applies
        ``unique()`` and ``scalars()`` modifiers to the result, so compound selects will
        not return the expected results.

        :param select: The ``select`` statement to paginate.
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
            The ``count`` query is more efficient.

        .. versionadded:: 3.0
        """
        return SelectPagination(
            select=select,
            session=self.session(),
            page=page,
            per_page=per_page,
            max_per_page=max_per_page,
            error_out=error_out,
            count=count,
        )

    def _call_for_binds(
        self, bind_key: str | None | list[str | None], op_name: str
    ) -> None:
        """Call a method on each metadata.

        :meta private:

        :param bind_key: A bind key or list of keys. Defaults to all binds.
        :param op_name: The name of the method to call.

        .. versionchanged:: 3.0
            Renamed from ``_execute_for_all_tables``.
        """
        if bind_key == "__all__":
            keys: list[str | None] = list(self.metadatas)
        elif bind_key is None or isinstance(bind_key, str):
            keys = [bind_key]
        else:
            keys = bind_key

        for key in keys:
            try:
                engine = self.engines[key]
            except KeyError:
                message = f"Bind key '{key}' is not in 'SQLALCHEMY_BINDS' config."

                if key is None:
                    message = f"'SQLALCHEMY_DATABASE_URI' config is not set. {message}"

                raise sa_exc.UnboundExecutionError(message) from None

            metadata = self.metadatas[key]
            getattr(metadata, op_name)(bind=engine)

    def create_all(self, bind_key: str | None | list[str | None] = "__all__") -> None:
        """Create tables that do not exist in the database by calling
        ``metadata.create_all()`` for all or some bind keys. This does not
        update existing tables, use a migration library for that.

        This requires that a Flask application context is active.

        :param bind_key: A bind key or list of keys to create the tables for. Defaults
            to all binds.

        .. versionchanged:: 3.0
            Renamed the ``bind`` parameter to ``bind_key``. Removed the ``app``
            parameter.

        .. versionchanged:: 0.12
            Added the ``bind`` and ``app`` parameters.
        """
        self._call_for_binds(bind_key, "create_all")

    def drop_all(self, bind_key: str | None | list[str | None] = "__all__") -> None:
        """Drop tables by calling ``metadata.drop_all()`` for all or some bind keys.

        This requires that a Flask application context is active.

        :param bind_key: A bind key or list of keys to drop the tables from. Defaults to
            all binds.

        .. versionchanged:: 3.0
            Renamed the ``bind`` parameter to ``bind_key``. Removed the ``app``
            parameter.

        .. versionchanged:: 0.12
            Added the ``bind`` and ``app`` parameters.
        """
        self._call_for_binds(bind_key, "drop_all")

    def reflect(self, bind_key: str | None | list[str | None] = "__all__") -> None:
        """Load table definitions from the database by calling ``metadata.reflect()``
        for all or some bind keys.

        This requires that a Flask application context is active.

        :param bind_key: A bind key or list of keys to reflect the tables from. Defaults
            to all binds.

        .. versionchanged:: 3.0
            Renamed the ``bind`` parameter to ``bind_key``. Removed the ``app``
            parameter.

        .. versionchanged:: 0.12
            Added the ``bind`` and ``app`` parameters.
        """
        self._call_for_binds(bind_key, "reflect")

    def _set_rel_query(self, kwargs: dict[str, t.Any]) -> None:
        """Apply the extension's :attr:`Query` class as the default for relationships
        and backrefs.

        :meta private:
        """
        kwargs.setdefault("query_class", self.Query)

        if "backref" in kwargs:
            backref = kwargs["backref"]

            if isinstance(backref, str):
                backref = (backref, {})

            backref[1].setdefault("query_class", self.Query)

    def relationship(
        self, *args: t.Any, **kwargs: t.Any
    ) -> sa_orm.RelationshipProperty[t.Any]:
        """A :func:`sqlalchemy.orm.relationship` that applies this extension's
        :attr:`Query` class for dynamic relationships and backrefs.

        .. versionchanged:: 3.0
            The :attr:`Query` class is set on ``backref``.
        """
        self._set_rel_query(kwargs)
        return sa_orm.relationship(*args, **kwargs)

    def dynamic_loader(
        self, argument: t.Any, **kwargs: t.Any
    ) -> sa_orm.RelationshipProperty[t.Any]:
        """A :func:`sqlalchemy.orm.dynamic_loader` that applies this extension's
        :attr:`Query` class for relationships and backrefs.

        .. versionchanged:: 3.0
            The :attr:`Query` class is set on ``backref``.
        """
        self._set_rel_query(kwargs)
        return sa_orm.dynamic_loader(argument, **kwargs)

    def _relation(
        self, *args: t.Any, **kwargs: t.Any
    ) -> sa_orm.RelationshipProperty[t.Any]:
        """A :func:`sqlalchemy.orm.relationship` that applies this extension's
        :attr:`Query` class for dynamic relationships and backrefs.

        SQLAlchemy 2.0 removes this name, use ``relationship`` instead.

        :meta private:

        .. versionchanged:: 3.0
            The :attr:`Query` class is set on ``backref``.
        """
        self._set_rel_query(kwargs)
        f = sa_orm.relationship
        return f(*args, **kwargs)

    def __getattr__(self, name: str) -> t.Any:
        if name == "relation":
            return self._relation

        if name == "event":
            return sa_event

        if name.startswith("_"):
            raise AttributeError(name)

        for mod in (sa, sa_orm):
            if hasattr(mod, name):
                return getattr(mod, name)

        raise AttributeError(name)
