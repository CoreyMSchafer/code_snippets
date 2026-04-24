import itertools

from wtforms import widgets
from wtforms.fields.core import Field
from wtforms.validators import ValidationError

__all__ = (
    "SelectField",
    "SelectMultipleField",
    "RadioField",
)


class SelectFieldBase(Field):
    option_widget = widgets.Option()

    """
    Base class for fields which can be iterated to produce options.

    This isn't a field, but an abstract base class for fields which want to
    provide this functionality.
    """

    def __init__(self, label=None, validators=None, option_widget=None, **kwargs):
        super().__init__(label, validators, **kwargs)

        if option_widget is not None:
            self.option_widget = option_widget

    def iter_choices(self):
        """
        Provides data for choice widget rendering. Must return a sequence or
        iterable of (value, label, selected, render_kw) tuples.
        """
        raise NotImplementedError()

    def has_groups(self):
        return False

    def iter_groups(self):
        raise NotImplementedError()

    def __iter__(self):
        opts = dict(
            widget=self.option_widget,
            validators=self.validators,
            name=self.name,
            render_kw=self.render_kw,
            _form=None,
            _meta=self.meta,
        )
        for i, choice in enumerate(self.iter_choices()):
            if len(choice) == 4:
                value, label, checked, render_kw = choice
            else:
                value, label, checked = choice
                render_kw = {}

            opt = self._Option(
                label=label, id="%s-%d" % (self.id, i), **opts, **render_kw
            )
            opt.process(None, value)
            opt.checked = checked
            yield opt

    class _Option(Field):
        checked = False

        def _value(self):
            return str(self.data)


class SelectField(SelectFieldBase):
    widget = widgets.Select()

    def __init__(
        self,
        label=None,
        validators=None,
        coerce=str,
        choices=None,
        validate_choice=True,
        **kwargs,
    ):
        super().__init__(label, validators, **kwargs)
        self.coerce = coerce
        if callable(choices):
            choices = choices()
        if choices is not None:
            self.choices = choices if isinstance(choices, dict) else list(choices)
        else:
            self.choices = None
        self.validate_choice = validate_choice

    def iter_choices(self):
        if not self.choices:
            choices = []
        elif isinstance(self.choices, dict):
            choices = list(itertools.chain.from_iterable(self.choices.values()))
        else:
            choices = self.choices

        return self._choices_generator(choices)

    def has_groups(self):
        return isinstance(self.choices, dict)

    def iter_groups(self):
        if isinstance(self.choices, dict):
            for label, choices in self.choices.items():
                yield (label, self._choices_generator(choices))

    def _choices_generator(self, choices):
        if not choices:
            _choices = []

        elif isinstance(choices[0], (list, tuple)):
            _choices = choices

        else:
            _choices = zip(choices, choices)

        for value, label, *other_args in _choices:
            selected = self.coerce(value) == self.data
            render_kw = other_args[0] if len(other_args) else {}
            yield (value, label, selected, render_kw)

    def process_data(self, value):
        try:
            # If value is None, don't coerce to a value
            self.data = self.coerce(value) if value is not None else None
        except (ValueError, TypeError):
            self.data = None

    def process_formdata(self, valuelist):
        if not valuelist:
            return

        try:
            self.data = self.coerce(valuelist[0])
        except ValueError as exc:
            raise ValueError(self.gettext("Invalid Choice: could not coerce.")) from exc

    def pre_validate(self, form):
        if not self.validate_choice:
            return

        if self.choices is None:
            raise TypeError(self.gettext("Choices cannot be None."))

        for _, _, match, *_ in self.iter_choices():
            if match:
                break
        else:
            raise ValidationError(self.gettext("Not a valid choice."))


class SelectMultipleField(SelectField):
    """
    No different from a normal select field, except this one can take (and
    validate) multiple choices.  You'll need to specify the HTML `size`
    attribute to the select field when rendering.
    """

    widget = widgets.Select(multiple=True)

    def _choices_generator(self, choices):
        if not choices:
            _choices = []

        elif isinstance(choices[0], (list, tuple)):
            _choices = choices

        else:
            _choices = zip(choices, choices)

        for value, label, *other_args in _choices:
            selected = self.data is not None and self.coerce(value) in self.data
            render_kw = other_args[0] if len(other_args) else {}
            yield (value, label, selected, render_kw)

    def process_data(self, value):
        try:
            self.data = list(self.coerce(v) for v in value)
        except (ValueError, TypeError):
            self.data = None

    def process_formdata(self, valuelist):
        try:
            self.data = list(self.coerce(x) for x in valuelist)
        except ValueError as exc:
            raise ValueError(
                self.gettext(
                    "Invalid choice(s): one or more data inputs could not be coerced."
                )
            ) from exc

    def pre_validate(self, form):
        if not self.validate_choice or not self.data:
            return

        if self.choices is None:
            raise TypeError(self.gettext("Choices cannot be None."))

        acceptable = [self.coerce(choice[0]) for choice in self.iter_choices()]
        if any(data not in acceptable for data in self.data):
            unacceptable = [
                str(data) for data in set(self.data) if data not in acceptable
            ]
            raise ValidationError(
                self.ngettext(
                    "'%(value)s' is not a valid choice for this field.",
                    "'%(value)s' are not valid choices for this field.",
                    len(unacceptable),
                )
                % dict(value="', '".join(unacceptable))
            )


class RadioField(SelectField):
    """
    Like a SelectField, except displays a list of radio buttons.

    Iterating the field will produce subfields (each containing a label as
    well) in order to allow custom rendering of the individual radio fields.
    """

    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.RadioInput()
