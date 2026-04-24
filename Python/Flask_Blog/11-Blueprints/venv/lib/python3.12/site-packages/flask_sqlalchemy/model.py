from __future__ import annotations

import re
import typing as t

import sqlalchemy as sa
import sqlalchemy.orm as sa_orm

from .query import Query

if t.TYPE_CHECKING:
    from .extension import SQLAlchemy


class _QueryProperty:
    """A class property that creates a query object for a model.

    :meta private:
    """

    def __get__(self, obj: Model | None, cls: type[Model]) -> Query:
        return cls.query_class(
            cls, session=cls.__fsa__.session()  # type: ignore[arg-type]
        )


class Model:
    """The base class of the :attr:`.SQLAlchemy.Model` declarative model class.

    To define models, subclass :attr:`db.Model <.SQLAlchemy.Model>`, not this. To
    customize ``db.Model``, subclass this and pass it as ``model_class`` to
    :class:`.SQLAlchemy`. To customize ``db.Model`` at the metaclass level, pass an
    already created declarative model class as ``model_class``.
    """

    __fsa__: t.ClassVar[SQLAlchemy]
    """Internal reference to the extension object.

    :meta private:
    """

    query_class: t.ClassVar[type[Query]] = Query
    """Query class used by :attr:`query`. Defaults to :attr:`.SQLAlchemy.Query`, which
    defaults to :class:`.Query`.
    """

    query: t.ClassVar[Query] = _QueryProperty()  # type: ignore[assignment]
    """A SQLAlchemy query for a model. Equivalent to ``db.session.query(Model)``. Can be
    customized per-model by overriding :attr:`query_class`.

    .. warning::
        The query interface is considered legacy in SQLAlchemy. Prefer using
        ``session.execute(select())`` instead.
    """

    def __repr__(self) -> str:
        state = sa.inspect(self)
        assert state is not None

        if state.transient:
            pk = f"(transient {id(self)})"
        elif state.pending:
            pk = f"(pending {id(self)})"
        else:
            pk = ", ".join(map(str, state.identity))

        return f"<{type(self).__name__} {pk}>"


class BindMetaMixin(type):
    """Metaclass mixin that sets a model's ``metadata`` based on its ``__bind_key__``.

    If the model sets ``metadata`` or ``__table__`` directly, ``__bind_key__`` is
    ignored. If the ``metadata`` is the same as the parent model, it will not be set
    directly on the child model.
    """

    __fsa__: SQLAlchemy
    metadata: sa.MetaData

    def __init__(
        cls, name: str, bases: tuple[type, ...], d: dict[str, t.Any], **kwargs: t.Any
    ) -> None:
        if not ("metadata" in cls.__dict__ or "__table__" in cls.__dict__):
            bind_key = getattr(cls, "__bind_key__", None)
            parent_metadata = getattr(cls, "metadata", None)
            metadata = cls.__fsa__._make_metadata(bind_key)

            if metadata is not parent_metadata:
                cls.metadata = metadata

        super().__init__(name, bases, d, **kwargs)


class BindMixin:
    """DeclarativeBase mixin to set a model's ``metadata`` based on ``__bind_key__``.

    If no ``__bind_key__`` is specified, the model will use the default metadata
    provided by ``DeclarativeBase`` or ``DeclarativeBaseNoMeta``.
    If the model doesn't set ``metadata`` or ``__table__`` directly
    and does set ``__bind_key__``, the model will use the metadata
    for the specified bind key.
    If the ``metadata`` is the same as the parent model, it will not be set
    directly on the child model.

    .. versionchanged:: 3.1.0
    """

    __fsa__: SQLAlchemy
    metadata: sa.MetaData

    @classmethod
    def __init_subclass__(cls: t.Type[BindMixin], **kwargs: t.Dict[str, t.Any]) -> None:
        if not ("metadata" in cls.__dict__ or "__table__" in cls.__dict__) and hasattr(
            cls, "__bind_key__"
        ):
            bind_key = getattr(cls, "__bind_key__", None)
            parent_metadata = getattr(cls, "metadata", None)
            metadata = cls.__fsa__._make_metadata(bind_key)

            if metadata is not parent_metadata:
                cls.metadata = metadata

        super().__init_subclass__(**kwargs)


class NameMetaMixin(type):
    """Metaclass mixin that sets a model's ``__tablename__`` by converting the
    ``CamelCase`` class name to ``snake_case``. A name is set for non-abstract models
    that do not otherwise define ``__tablename__``. If a model does not define a primary
    key, it will not generate a name or ``__table__``, for single-table inheritance.
    """

    metadata: sa.MetaData
    __tablename__: str
    __table__: sa.Table

    def __init__(
        cls, name: str, bases: tuple[type, ...], d: dict[str, t.Any], **kwargs: t.Any
    ) -> None:
        if should_set_tablename(cls):
            cls.__tablename__ = camel_to_snake_case(cls.__name__)

        super().__init__(name, bases, d, **kwargs)

        # __table_cls__ has run. If no table was created, use the parent table.
        if (
            "__tablename__" not in cls.__dict__
            and "__table__" in cls.__dict__
            and cls.__dict__["__table__"] is None
        ):
            del cls.__table__

    def __table_cls__(cls, *args: t.Any, **kwargs: t.Any) -> sa.Table | None:
        """This is called by SQLAlchemy during mapper setup. It determines the final
        table object that the model will use.

        If no primary key is found, that indicates single-table inheritance, so no table
        will be created and ``__tablename__`` will be unset.
        """
        schema = kwargs.get("schema")

        if schema is None:
            key = args[0]
        else:
            key = f"{schema}.{args[0]}"

        # Check if a table with this name already exists. Allows reflected tables to be
        # applied to models by name.
        if key in cls.metadata.tables:
            return sa.Table(*args, **kwargs)

        # If a primary key is found, create a table for joined-table inheritance.
        for arg in args:
            if (isinstance(arg, sa.Column) and arg.primary_key) or isinstance(
                arg, sa.PrimaryKeyConstraint
            ):
                return sa.Table(*args, **kwargs)

        # If no base classes define a table, return one that's missing a primary key
        # so SQLAlchemy shows the correct error.
        for base in cls.__mro__[1:-1]:
            if "__table__" in base.__dict__:
                break
        else:
            return sa.Table(*args, **kwargs)

        # Single-table inheritance, use the parent table name. __init__ will unset
        # __table__ based on this.
        if "__tablename__" in cls.__dict__:
            del cls.__tablename__

        return None


class NameMixin:
    """DeclarativeBase mixin that sets a model's ``__tablename__`` by converting the
    ``CamelCase`` class name to ``snake_case``. A name is set for non-abstract models
    that do not otherwise define ``__tablename__``. If a model does not define a primary
    key, it will not generate a name or ``__table__``, for single-table inheritance.

    .. versionchanged:: 3.1.0
    """

    metadata: sa.MetaData
    __tablename__: str
    __table__: sa.Table

    @classmethod
    def __init_subclass__(cls: t.Type[NameMixin], **kwargs: t.Dict[str, t.Any]) -> None:
        if should_set_tablename(cls):
            cls.__tablename__ = camel_to_snake_case(cls.__name__)

        super().__init_subclass__(**kwargs)

        # __table_cls__ has run. If no table was created, use the parent table.
        if (
            "__tablename__" not in cls.__dict__
            and "__table__" in cls.__dict__
            and cls.__dict__["__table__"] is None
        ):
            del cls.__table__

    @classmethod
    def __table_cls__(cls, *args: t.Any, **kwargs: t.Any) -> sa.Table | None:
        """This is called by SQLAlchemy during mapper setup. It determines the final
        table object that the model will use.

        If no primary key is found, that indicates single-table inheritance, so no table
        will be created and ``__tablename__`` will be unset.
        """
        schema = kwargs.get("schema")

        if schema is None:
            key = args[0]
        else:
            key = f"{schema}.{args[0]}"

        # Check if a table with this name already exists. Allows reflected tables to be
        # applied to models by name.
        if key in cls.metadata.tables:
            return sa.Table(*args, **kwargs)

        # If a primary key is found, create a table for joined-table inheritance.
        for arg in args:
            if (isinstance(arg, sa.Column) and arg.primary_key) or isinstance(
                arg, sa.PrimaryKeyConstraint
            ):
                return sa.Table(*args, **kwargs)

        # If no base classes define a table, return one that's missing a primary key
        # so SQLAlchemy shows the correct error.
        for base in cls.__mro__[1:-1]:
            if "__table__" in base.__dict__:
                break
        else:
            return sa.Table(*args, **kwargs)

        # Single-table inheritance, use the parent table name. __init__ will unset
        # __table__ based on this.
        if "__tablename__" in cls.__dict__:
            del cls.__tablename__

        return None


def should_set_tablename(cls: type) -> bool:
    """Determine whether ``__tablename__`` should be generated for a model.

    -   If no class in the MRO sets a name, one should be generated.
    -   If a declared attr is found, it should be used instead.
    -   If a name is found, it should be used if the class is a mixin, otherwise one
        should be generated.
    -   Abstract models should not have one generated.

    Later, ``__table_cls__`` will determine if the model looks like single or
    joined-table inheritance. If no primary key is found, the name will be unset.
    """
    if (
        cls.__dict__.get("__abstract__", False)
        or (
            not issubclass(cls, (sa_orm.DeclarativeBase, sa_orm.DeclarativeBaseNoMeta))
            and not any(isinstance(b, sa_orm.DeclarativeMeta) for b in cls.__mro__[1:])
        )
        or any(
            (b is sa_orm.DeclarativeBase or b is sa_orm.DeclarativeBaseNoMeta)
            for b in cls.__bases__
        )
    ):
        return False

    for base in cls.__mro__:
        if "__tablename__" not in base.__dict__:
            continue

        if isinstance(base.__dict__["__tablename__"], sa_orm.declared_attr):
            return False

        return not (
            base is cls
            or base.__dict__.get("__abstract__", False)
            or not (
                # SQLAlchemy 1.x
                isinstance(base, sa_orm.DeclarativeMeta)
                # 2.x: DeclarativeBas uses this as metaclass
                or isinstance(base, sa_orm.decl_api.DeclarativeAttributeIntercept)
                # 2.x: DeclarativeBaseNoMeta doesn't use a metaclass
                or issubclass(base, sa_orm.DeclarativeBaseNoMeta)
            )
        )

    return True


def camel_to_snake_case(name: str) -> str:
    """Convert a ``CamelCase`` name to ``snake_case``."""
    name = re.sub(r"((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))", r"_\1", name)
    return name.lower().lstrip("_")


class DefaultMeta(BindMetaMixin, NameMetaMixin, sa_orm.DeclarativeMeta):
    """SQLAlchemy declarative metaclass that provides ``__bind_key__`` and
    ``__tablename__`` support.
    """


class DefaultMetaNoName(BindMetaMixin, sa_orm.DeclarativeMeta):
    """SQLAlchemy declarative metaclass that provides ``__bind_key__`` and
    ``__tablename__`` support.
    """
