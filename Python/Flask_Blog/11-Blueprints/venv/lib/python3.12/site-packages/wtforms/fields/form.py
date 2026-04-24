from wtforms.utils import unset_value

from .. import widgets
from .core import Field

__all__ = ("FormField",)


class FormField(Field):
    """
    Encapsulate a form as a field in another form.

    :param form_class:
        A subclass of Form that will be encapsulated.
    :param separator:
        A string which will be suffixed to this field's name to create the
        prefix to enclosed fields. The default is fine for most uses.
    """

    widget = widgets.TableWidget()

    def __init__(
        self, form_class, label=None, validators=None, separator="-", **kwargs
    ):
        super().__init__(label, validators, **kwargs)
        self.form_class = form_class
        self.separator = separator
        self._obj = None
        if self.filters:
            raise TypeError(
                "FormField cannot take filters, as the encapsulated"
                " data is not mutable."
            )
        if validators:
            raise TypeError(
                "FormField does not accept any validators. Instead,"
                " define them on the enclosed form."
            )

    def process(self, formdata, data=unset_value, extra_filters=None):
        if extra_filters:
            raise TypeError(
                "FormField cannot take filters, as the encapsulated"
                "data is not mutable."
            )

        if data is unset_value:
            try:
                data = self.default()
            except TypeError:
                data = self.default
            self._obj = data

        self.object_data = data

        prefix = self.name + self.separator
        if isinstance(data, dict):
            self.form = self.form_class(formdata=formdata, prefix=prefix, **data)
        else:
            self.form = self.form_class(formdata=formdata, obj=data, prefix=prefix)

    def validate(self, form, extra_validators=()):
        if extra_validators:
            raise TypeError(
                "FormField does not accept in-line validators, as it"
                " gets errors from the enclosed form."
            )
        return self.form.validate()

    def populate_obj(self, obj, name):
        candidate = getattr(obj, name, None)
        if candidate is None:
            if self._obj is None:
                raise TypeError(
                    "populate_obj: cannot find a value to populate from"
                    " the provided obj or input data/defaults"
                )
            candidate = self._obj

        self.form.populate_obj(candidate)
        setattr(obj, name, candidate)

    def __iter__(self):
        return iter(self.form)

    def __getitem__(self, name):
        return self.form[name]

    def __getattr__(self, name):
        return getattr(self.form, name)

    @property
    def data(self):
        return self.form.data

    @property
    def errors(self):
        return self.form.errors
