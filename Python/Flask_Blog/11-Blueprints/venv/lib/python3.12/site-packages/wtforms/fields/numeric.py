import decimal

from wtforms import widgets
from wtforms.fields.core import Field
from wtforms.utils import unset_value

__all__ = (
    "IntegerField",
    "DecimalField",
    "FloatField",
    "IntegerRangeField",
    "DecimalRangeField",
)


class LocaleAwareNumberField(Field):
    """
    Base class for implementing locale-aware number parsing.

    Locale-aware numbers require the 'babel' package to be present.
    """

    def __init__(
        self,
        label=None,
        validators=None,
        use_locale=False,
        number_format=None,
        **kwargs,
    ):
        super().__init__(label, validators, **kwargs)
        self.use_locale = use_locale
        if use_locale:
            self.number_format = number_format
            self.locale = kwargs["_form"].meta.locales[0]
            self._init_babel()

    def _init_babel(self):
        try:
            from babel import numbers

            self.babel_numbers = numbers
        except ImportError as exc:
            raise ImportError(
                "Using locale-aware decimals requires the babel library."
            ) from exc

    def _parse_decimal(self, value):
        return self.babel_numbers.parse_decimal(value, self.locale)

    def _format_decimal(self, value):
        return self.babel_numbers.format_decimal(value, self.number_format, self.locale)


class IntegerField(Field):
    """
    A text field, except all input is coerced to an integer.  Erroneous input
    is ignored and will not be accepted as a value.
    """

    widget = widgets.NumberInput()

    def __init__(self, label=None, validators=None, **kwargs):
        super().__init__(label, validators, **kwargs)

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        if self.data is not None:
            return str(self.data)
        return ""

    def process_data(self, value):
        if value is None or value is unset_value:
            self.data = None
            return

        try:
            self.data = int(value)
        except (ValueError, TypeError) as exc:
            self.data = None
            raise ValueError(self.gettext("Not a valid integer value.")) from exc

    def process_formdata(self, valuelist):
        if not valuelist:
            return

        try:
            self.data = int(valuelist[0])
        except ValueError as exc:
            self.data = None
            raise ValueError(self.gettext("Not a valid integer value.")) from exc


class DecimalField(LocaleAwareNumberField):
    """
    A text field which displays and coerces data of the `decimal.Decimal` type.

    :param places:
        How many decimal places to quantize the value to for display on form.
        If unset, use 2 decimal places.
        If explicitely set to `None`, does not quantize value.
    :param rounding:
        How to round the value during quantize, for example
        `decimal.ROUND_UP`. If unset, uses the rounding value from the
        current thread's context.
    :param use_locale:
        If True, use locale-based number formatting. Locale-based number
        formatting requires the 'babel' package.
    :param number_format:
        Optional number format for locale. If omitted, use the default decimal
        format for the locale.
    """

    widget = widgets.NumberInput(step="any")

    def __init__(
        self, label=None, validators=None, places=unset_value, rounding=None, **kwargs
    ):
        super().__init__(label, validators, **kwargs)
        if self.use_locale and (places is not unset_value or rounding is not None):
            raise TypeError(
                "When using locale-aware numbers, 'places' and 'rounding' are ignored."
            )

        if places is unset_value:
            places = 2
        self.places = places
        self.rounding = rounding

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]

        if self.data is None:
            return ""

        if self.use_locale:
            return str(self._format_decimal(self.data))

        if self.places is None:
            return str(self.data)

        if not hasattr(self.data, "quantize"):
            # If for some reason, data is a float or int, then format
            # as we would for floats using string formatting.
            format = "%%0.%df" % self.places
            return format % self.data

        exp = decimal.Decimal(".1") ** self.places
        if self.rounding is None:
            quantized = self.data.quantize(exp)
        else:
            quantized = self.data.quantize(exp, rounding=self.rounding)
        return str(quantized)

    def process_formdata(self, valuelist):
        if not valuelist:
            return

        try:
            if self.use_locale:
                self.data = self._parse_decimal(valuelist[0])
            else:
                self.data = decimal.Decimal(valuelist[0])
        except (decimal.InvalidOperation, ValueError) as exc:
            self.data = None
            raise ValueError(self.gettext("Not a valid decimal value.")) from exc


class FloatField(Field):
    """
    A text field, except all input is coerced to an float.  Erroneous input
    is ignored and will not be accepted as a value.
    """

    widget = widgets.TextInput()

    def __init__(self, label=None, validators=None, **kwargs):
        super().__init__(label, validators, **kwargs)

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        if self.data is not None:
            return str(self.data)
        return ""

    def process_formdata(self, valuelist):
        if not valuelist:
            return

        try:
            self.data = float(valuelist[0])
        except ValueError as exc:
            self.data = None
            raise ValueError(self.gettext("Not a valid float value.")) from exc


class IntegerRangeField(IntegerField):
    """
    Represents an ``<input type="range">``.
    """

    widget = widgets.RangeInput()


class DecimalRangeField(DecimalField):
    """
    Represents an ``<input type="range">``.
    """

    widget = widgets.RangeInput(step="any")
