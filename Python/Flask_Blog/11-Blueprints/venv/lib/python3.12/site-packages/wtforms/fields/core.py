import inspect
import itertools

from markupsafe import escape
from markupsafe import Markup

from wtforms import widgets
from wtforms.i18n import DummyTranslations
from wtforms.utils import unset_value
from wtforms.validators import StopValidation
from wtforms.validators import ValidationError


class Field:
    """
    Field base class
    """

    errors = tuple()
    process_errors = tuple()
    raw_data = None
    validators = tuple()
    widget = None
    _formfield = True
    _translations = DummyTranslations()
    do_not_call_in_templates = True  # Allow Django 1.4 traversal

    def __new__(cls, *args, **kwargs):
        if "_form" in kwargs:
            return super().__new__(cls)
        else:
            return UnboundField(cls, *args, **kwargs)

    def __init__(
        self,
        label=None,
        validators=None,
        filters=(),
        description="",
        id=None,
        default=None,
        widget=None,
        render_kw=None,
        name=None,
        _form=None,
        _prefix="",
        _translations=None,
        _meta=None,
    ):
        """
        Construct a new field.

        :param label:
            The label of the field.
        :param validators:
            A sequence of validators to call when `validate` is called.
        :param filters:
            A sequence of callable which are run by :meth:`~Field.process`
            to filter or transform the input data. For example
            ``StringForm(filters=[str.strip, str.upper])``.
            Note that filters are applied after processing the default and
            incoming data, but before validation.
        :param description:
            A description for the field, typically used for help text.
        :param id:
            An id to use for the field. A reasonable default is set by the form,
            and you shouldn't need to set this manually.
        :param default:
            The default value to assign to the field, if no form or object
            input is provided. May be a callable.
        :param widget:
            If provided, overrides the widget used to render the field.
        :param dict render_kw:
            If provided, a dictionary which provides default keywords that
            will be given to the widget at render time.
        :param name:
            The HTML name of this field. The default value is the Python
            attribute name.
        :param _form:
            The form holding this field. It is passed by the form itself during
            construction. You should never pass this value yourself.
        :param _prefix:
            The prefix to prepend to the form name of this field, passed by
            the enclosing form during construction.
        :param _translations:
            A translations object providing message translations. Usually
            passed by the enclosing form during construction. See
            :doc:`I18n docs <i18n>` for information on message translations.
        :param _meta:
            If provided, this is the 'meta' instance from the form. You usually
            don't pass this yourself.

        If `_form` isn't provided, an :class:`UnboundField` will be
        returned instead. Call its :func:`bind` method with a form instance and
        a name to construct the field.
        """
        if _translations is not None:
            self._translations = _translations

        if _meta is not None:
            self.meta = _meta
        elif _form is not None:
            self.meta = _form.meta
        else:
            raise TypeError("Must provide one of _form or _meta")

        self.default = default
        self.description = description
        self.render_kw = render_kw
        self.filters = filters
        self.flags = Flags()
        self.name = _prefix + name
        self.short_name = name
        self.type = type(self).__name__

        self.check_validators(validators)
        self.validators = validators or self.validators

        self.id = id or self.name
        self.label = Label(
            self.id,
            label
            if label is not None
            else self.gettext(name.replace("_", " ").title()),
        )

        if widget is not None:
            self.widget = widget

        for v in itertools.chain(self.validators, [self.widget]):
            flags = getattr(v, "field_flags", {})

            for k, v in flags.items():
                setattr(self.flags, k, v)

    def __str__(self):
        """
        Returns a HTML representation of the field. For more powerful rendering,
        see the `__call__` method.
        """
        return self()

    def __html__(self):
        """
        Returns a HTML representation of the field. For more powerful rendering,
        see the :meth:`__call__` method.
        """
        return self()

    def __call__(self, **kwargs):
        """
        Render this field as HTML, using keyword args as additional attributes.

        This delegates rendering to
        :meth:`meta.render_field <wtforms.meta.DefaultMeta.render_field>`
        whose default behavior is to call the field's widget, passing any
        keyword arguments from this call along to the widget.

        In all of the WTForms HTML widgets, keyword arguments are turned to
        HTML attributes, though in theory a widget is free to do anything it
        wants with the supplied keyword arguments, and widgets don't have to
        even do anything related to HTML.
        """
        return self.meta.render_field(self, kwargs)

    @classmethod
    def check_validators(cls, validators):
        if validators is not None:
            for validator in validators:
                if not callable(validator):
                    raise TypeError(
                        f"{validator} is not a valid validator because it is not "
                        "callable"
                    )

                if inspect.isclass(validator):
                    raise TypeError(
                        f"{validator} is not a valid validator because it is a class, "
                        "it should be an instance"
                    )

    def gettext(self, string):
        """
        Get a translation for the given message.

        This proxies for the internal translations object.

        :param string: A string to be translated.
        :return: A string which is the translated output.
        """
        return self._translations.gettext(string)

    def ngettext(self, singular, plural, n):
        """
        Get a translation for a message which can be pluralized.

        :param str singular: The singular form of the message.
        :param str plural: The plural form of the message.
        :param int n: The number of elements this message is referring to
        """
        return self._translations.ngettext(singular, plural, n)

    def validate(self, form, extra_validators=()):
        """
        Validates the field and returns True or False. `self.errors` will
        contain any errors raised during validation. This is usually only
        called by `Form.validate`.

        Subfields shouldn't override this, but rather override either
        `pre_validate`, `post_validate` or both, depending on needs.

        :param form: The form the field belongs to.
        :param extra_validators: A sequence of extra validators to run.
        """
        self.errors = list(self.process_errors)
        stop_validation = False

        # Check the type of extra_validators
        self.check_validators(extra_validators)

        # Call pre_validate
        try:
            self.pre_validate(form)
        except StopValidation as e:
            if e.args and e.args[0]:
                self.errors.append(e.args[0])
            stop_validation = True
        except ValidationError as e:
            self.errors.append(e.args[0])

        # Run validators
        if not stop_validation:
            chain = itertools.chain(self.validators, extra_validators)
            stop_validation = self._run_validation_chain(form, chain)

        # Call post_validate
        try:
            self.post_validate(form, stop_validation)
        except ValidationError as e:
            self.errors.append(e.args[0])

        return len(self.errors) == 0

    def _run_validation_chain(self, form, validators):
        """
        Run a validation chain, stopping if any validator raises StopValidation.

        :param form: The Form instance this field belongs to.
        :param validators: a sequence or iterable of validator callables.
        :return: True if validation was stopped, False otherwise.
        """
        for validator in validators:
            try:
                validator(form, self)
            except StopValidation as e:
                if e.args and e.args[0]:
                    self.errors.append(e.args[0])
                return True
            except ValidationError as e:
                self.errors.append(e.args[0])

        return False

    def pre_validate(self, form):
        """
        Override if you need field-level validation. Runs before any other
        validators.

        :param form: The form the field belongs to.
        """
        pass

    def post_validate(self, form, validation_stopped):
        """
        Override if you need to run any field-level validation tasks after
        normal validation. This shouldn't be needed in most cases.

        :param form: The form the field belongs to.
        :param validation_stopped:
            `True` if any validator raised StopValidation.
        """
        pass

    def process(self, formdata, data=unset_value, extra_filters=None):
        """
        Process incoming data, calling process_data, process_formdata as needed,
        and run filters.

        If `data` is not provided, process_data will be called on the field's
        default.

        Field subclasses usually won't override this, instead overriding the
        process_formdata and process_data methods. Only override this for
        special advanced processing, such as when a field encapsulates many
        inputs.

        :param extra_filters: A sequence of extra filters to run.
        """
        self.process_errors = []
        if data is unset_value:
            try:
                data = self.default()
            except TypeError:
                data = self.default

        self.object_data = data

        try:
            self.process_data(data)
        except ValueError as e:
            self.process_errors.append(e.args[0])

        if formdata is not None:
            if self.name in formdata:
                self.raw_data = formdata.getlist(self.name)
            else:
                self.raw_data = []

            try:
                self.process_formdata(self.raw_data)
            except ValueError as e:
                self.process_errors.append(e.args[0])

        try:
            for filter in itertools.chain(self.filters, extra_filters or []):
                self.data = filter(self.data)
        except ValueError as e:
            self.process_errors.append(e.args[0])

    def process_data(self, value):
        """
        Process the Python data applied to this field and store the result.

        This will be called during form construction by the form's `kwargs` or
        `obj` argument.

        :param value: The python object containing the value to process.
        """
        self.data = value

    def process_formdata(self, valuelist):
        """
        Process data received over the wire from a form.

        This will be called during form construction with data supplied
        through the `formdata` argument.

        :param valuelist: A list of strings to process.
        """
        if valuelist:
            self.data = valuelist[0]

    def populate_obj(self, obj, name):
        """
        Populates `obj.<name>` with the field's data.

        :note: This is a destructive operation. If `obj.<name>` already exists,
               it will be overridden. Use with caution.
        """
        setattr(obj, name, self.data)


class UnboundField:
    _formfield = True
    creation_counter = 0

    def __init__(self, field_class, *args, name=None, **kwargs):
        UnboundField.creation_counter += 1
        self.field_class = field_class
        self.args = args
        self.name = name
        self.kwargs = kwargs
        self.creation_counter = UnboundField.creation_counter
        validators = kwargs.get("validators")
        if validators:
            self.field_class.check_validators(validators)

    def bind(self, form, name, prefix="", translations=None, **kwargs):
        kw = dict(
            self.kwargs,
            name=name,
            _form=form,
            _prefix=prefix,
            _translations=translations,
            **kwargs,
        )
        return self.field_class(*self.args, **kw)

    def __repr__(self):
        return (
            "<UnboundField("
            f"{self.field_class.__name__}, {self.args!r}, {self.kwargs!r}"
            ")>"
        )


class Flags:
    """
    Holds a set of flags as attributes.

    Accessing a non-existing attribute returns None for its value.
    """

    def __getattr__(self, name):
        if name.startswith("_"):
            return super().__getattr__(name)
        return None

    def __contains__(self, name):
        return getattr(self, name)

    def __repr__(self):
        flags = (
            f"{name}={getattr(self, name)}"
            for name in dir(self)
            if not name.startswith("_")
        )
        flags = ", ".join(flags)
        return f"<wtforms.fields.Flags: {{{flags}}}>"


class Label:
    """
    An HTML form label.
    """

    def __init__(self, field_id, text):
        self.field_id = field_id
        self.text = text

    def __str__(self):
        return self()

    def __html__(self):
        return self()

    def __call__(self, text=None, **kwargs):
        if "for_" in kwargs:
            kwargs["for"] = kwargs.pop("for_")
        else:
            kwargs.setdefault("for", self.field_id)

        attributes = widgets.html_params(**kwargs)
        text = escape(text or self.text)
        return Markup(f"<label {attributes}>{text}</label>")

    def __repr__(self):
        return f"Label({self.field_id!r}, {self.text!r})"
