import itertools
from collections import OrderedDict

from wtforms.meta import DefaultMeta
from wtforms.utils import unset_value

__all__ = ("BaseForm", "Form")

_default_meta = DefaultMeta()


class BaseForm:
    """
    Base Form Class.  Provides core behaviour like field construction,
    validation, and data and error proxying.
    """

    def __init__(self, fields, prefix="", meta=_default_meta):
        """
        :param fields:
            A dict or sequence of 2-tuples of partially-constructed fields.
        :param prefix:
            If provided, all fields will have their name prefixed with the
            value.
        :param meta:
            A meta instance which is used for configuration and customization
            of WTForms behaviors.
        """
        if prefix and prefix[-1] not in "-_;:/.":
            prefix += "-"

        self.meta = meta
        self._form_error_key = ""
        self._prefix = prefix
        self._fields = OrderedDict()

        if hasattr(fields, "items"):
            fields = fields.items()

        translations = self.meta.get_translations(self)
        extra_fields = []
        if meta.csrf:
            self._csrf = meta.build_csrf(self)
            extra_fields.extend(self._csrf.setup_form(self))

        for name, unbound_field in itertools.chain(fields, extra_fields):
            field_name = unbound_field.name or name
            options = dict(name=field_name, prefix=prefix, translations=translations)
            field = meta.bind_field(self, unbound_field, options)
            self._fields[name] = field

        self.form_errors = []

    def __iter__(self):
        """Iterate form fields in creation order."""
        return iter(self._fields.values())

    def __contains__(self, name):
        """Returns `True` if the named field is a member of this form."""
        return name in self._fields

    def __getitem__(self, name):
        """Dict-style access to this form's fields."""
        return self._fields[name]

    def __setitem__(self, name, value):
        """Bind a field to this form."""
        self._fields[name] = value.bind(form=self, name=name, prefix=self._prefix)

    def __delitem__(self, name):
        """Remove a field from this form."""
        del self._fields[name]

    def populate_obj(self, obj):
        """
        Populates the attributes of the passed `obj` with data from the form's
        fields.

        :note: This is a destructive operation; Any attribute with the same name
               as a field will be overridden. Use with caution.
        """
        for name, field in self._fields.items():
            field.populate_obj(obj, name)

    def process(self, formdata=None, obj=None, data=None, extra_filters=None, **kwargs):
        """Process default and input data with each field.

        :param formdata: Input data coming from the client, usually
            ``request.form`` or equivalent. Should provide a "multi
            dict" interface to get a list of values for a given key,
            such as what Werkzeug, Django, and WebOb provide.
        :param obj: Take existing data from attributes on this object
            matching form field attributes. Only used if ``formdata`` is
            not passed.
        :param data: Take existing data from keys in this dict matching
            form field attributes. ``obj`` takes precedence if it also
            has a matching attribute. Only used if ``formdata`` is not
            passed.
        :param extra_filters: A dict mapping field attribute names to
            lists of extra filter functions to run. Extra filters run
            after filters passed when creating the field. If the form
            has ``filter_<fieldname>``, it is the last extra filter.
        :param kwargs: Merged with ``data`` to allow passing existing
            data as parameters. Overwrites any duplicate keys in
            ``data``. Only used if ``formdata`` is not passed.
        """
        formdata = self.meta.wrap_formdata(self, formdata)

        if data is not None:
            kwargs = dict(data, **kwargs)

        filters = extra_filters.copy() if extra_filters is not None else {}

        for name, field in self._fields.items():
            field_extra_filters = filters.get(name, [])

            inline_filter = getattr(self, f"filter_{name}", None)
            if inline_filter is not None:
                field_extra_filters.append(inline_filter)

            if obj is not None and hasattr(obj, name):
                data = getattr(obj, name)
            elif name in kwargs:
                data = kwargs[name]
            else:
                data = unset_value

            field.process(formdata, data, extra_filters=field_extra_filters)

    def validate(self, extra_validators=None):
        """
        Validates the form by calling `validate` on each field.

        :param extra_validators:
            If provided, is a dict mapping field names to a sequence of
            callables which will be passed as extra validators to the field's
            `validate` method.

        Returns `True` if no errors occur.
        """
        success = True
        for name, field in self._fields.items():
            if extra_validators is not None and name in extra_validators:
                extra = extra_validators[name]
            else:
                extra = tuple()
            if not field.validate(self, extra):
                success = False
        return success

    @property
    def data(self):
        return {name: f.data for name, f in self._fields.items()}

    @property
    def errors(self):
        errors = {name: f.errors for name, f in self._fields.items() if f.errors}
        if self.form_errors:
            errors[self._form_error_key] = self.form_errors
        return errors


class FormMeta(type):
    """
    The metaclass for `Form` and any subclasses of `Form`.

    `FormMeta`'s responsibility is to create the `_unbound_fields` list, which
    is a list of `UnboundField` instances sorted by their order of
    instantiation.  The list is created at the first instantiation of the form.
    If any fields are added/removed from the form, the list is cleared to be
    re-generated on the next instantiation.

    Any properties which begin with an underscore or are not `UnboundField`
    instances are ignored by the metaclass.
    """

    def __init__(cls, name, bases, attrs):
        type.__init__(cls, name, bases, attrs)
        cls._unbound_fields = None
        cls._wtforms_meta = None

    def __call__(cls, *args, **kwargs):
        """
        Construct a new `Form` instance.

        Creates the `_unbound_fields` list and the internal `_wtforms_meta`
        subclass of the class Meta in order to allow a proper inheritance
        hierarchy.
        """
        if cls._unbound_fields is None:
            fields = []
            for name in dir(cls):
                if not name.startswith("_"):
                    unbound_field = getattr(cls, name)
                    if hasattr(unbound_field, "_formfield"):
                        fields.append((name, unbound_field))
            # We keep the name as the second element of the sort
            # to ensure a stable sort.
            fields.sort(key=lambda x: (x[1].creation_counter, x[0]))
            cls._unbound_fields = fields

        # Create a subclass of the 'class Meta' using all the ancestors.
        if cls._wtforms_meta is None:
            bases = []
            for mro_class in cls.__mro__:
                if "Meta" in mro_class.__dict__:
                    bases.append(mro_class.Meta)
            cls._wtforms_meta = type("Meta", tuple(bases), {})
        return type.__call__(cls, *args, **kwargs)

    def __setattr__(cls, name, value):
        """
        Add an attribute to the class, clearing `_unbound_fields` if needed.
        """
        if name == "Meta":
            cls._wtforms_meta = None
        elif not name.startswith("_") and hasattr(value, "_formfield"):
            cls._unbound_fields = None
        type.__setattr__(cls, name, value)

    def __delattr__(cls, name):
        """
        Remove an attribute from the class, clearing `_unbound_fields` if
        needed.
        """
        if not name.startswith("_"):
            cls._unbound_fields = None
        type.__delattr__(cls, name)


class Form(BaseForm, metaclass=FormMeta):
    """
    Declarative Form base class. Extends BaseForm's core behaviour allowing
    fields to be defined on Form subclasses as class attributes.

    In addition, form and instance input data are taken at construction time
    and passed to `process()`.
    """

    Meta = DefaultMeta

    def __init__(
        self,
        formdata=None,
        obj=None,
        prefix="",
        data=None,
        meta=None,
        **kwargs,
    ):
        """
        :param formdata: Input data coming from the client, usually
            ``request.form`` or equivalent. Should provide a "multi
            dict" interface to get a list of values for a given key,
            such as what Werkzeug, Django, and WebOb provide.
        :param obj: Take existing data from attributes on this object
            matching form field attributes. Only used if ``formdata`` is
            not passed.
        :param prefix: If provided, all fields will have their name
            prefixed with the value. This is for distinguishing multiple
            forms on a single page. This only affects the HTML name for
            matching input data, not the Python name for matching
            existing data.
        :param data: Take existing data from keys in this dict matching
            form field attributes. ``obj`` takes precedence if it also
            has a matching attribute. Only used if ``formdata`` is not
            passed.
        :param meta: A dict of attributes to override on this form's
            :attr:`meta` instance.
        :param extra_filters: A dict mapping field attribute names to
            lists of extra filter functions to run. Extra filters run
            after filters passed when creating the field. If the form
            has ``filter_<fieldname>``, it is the last extra filter.
        :param kwargs: Merged with ``data`` to allow passing existing
            data as parameters. Overwrites any duplicate keys in
            ``data``. Only used if ``formdata`` is not passed.
        """
        meta_obj = self._wtforms_meta()
        if meta is not None and isinstance(meta, dict):
            meta_obj.update_values(meta)
        super().__init__(self._unbound_fields, meta=meta_obj, prefix=prefix)

        for name, field in self._fields.items():
            # Set all the fields to attributes so that they obscure the class
            # attributes with the same names.
            setattr(self, name, field)
        self.process(formdata, obj, data=data, **kwargs)

    def __setitem__(self, name, value):
        raise TypeError("Fields may not be added to Form instances, only classes.")

    def __delitem__(self, name):
        del self._fields[name]
        setattr(self, name, None)

    def __delattr__(self, name):
        if name in self._fields:
            self.__delitem__(name)
        else:
            # This is done for idempotency, if we have a name which is a field,
            # we want to mask it by setting the value to None.
            unbound_field = getattr(self.__class__, name, None)
            if unbound_field is not None and hasattr(unbound_field, "_formfield"):
                setattr(self, name, None)
            else:
                super().__delattr__(name)

    def validate(self, extra_validators=None):
        """Validate the form by calling ``validate`` on each field.
        Returns ``True`` if validation passes.

        If the form defines a ``validate_<fieldname>`` method, it is
        appended as an extra validator for the field's ``validate``.

        :param extra_validators: A dict mapping field names to lists of
            extra validator methods to run. Extra validators run after
            validators passed when creating the field. If the form has
            ``validate_<fieldname>``, it is the last extra validator.
        """
        if extra_validators is not None:
            extra = extra_validators.copy()
        else:
            extra = {}

        for name in self._fields:
            inline = getattr(self.__class__, f"validate_{name}", None)
            if inline is not None:
                extra.setdefault(name, []).append(inline)

        return super().validate(extra)
