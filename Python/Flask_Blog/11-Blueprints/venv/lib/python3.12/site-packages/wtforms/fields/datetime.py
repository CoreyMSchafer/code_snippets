import datetime

from wtforms import widgets
from wtforms.fields.core import Field
from wtforms.utils import clean_datetime_format_for_strptime

__all__ = (
    "DateTimeField",
    "DateField",
    "TimeField",
    "MonthField",
    "DateTimeLocalField",
    "WeekField",
)


class DateTimeField(Field):
    """
    A text field which stores a :class:`datetime.datetime` matching one or
    several formats. If ``format`` is a list, any input value matching any
    format will be accepted, and the first format in the list will be used
    to produce HTML values.
    """

    widget = widgets.DateTimeInput()

    def __init__(
        self, label=None, validators=None, format="%Y-%m-%d %H:%M:%S", **kwargs
    ):
        super().__init__(label, validators, **kwargs)
        self.format = format if isinstance(format, list) else [format]
        self.strptime_format = clean_datetime_format_for_strptime(self.format)

    def _value(self):
        if self.raw_data:
            return " ".join(self.raw_data)
        format = self.format[0]
        return self.data and self.data.strftime(format) or ""

    def process_formdata(self, valuelist):
        if not valuelist:
            return

        date_str = " ".join(valuelist)
        for format in self.strptime_format:
            try:
                self.data = datetime.datetime.strptime(date_str, format)
                return
            except ValueError:
                self.data = None

        raise ValueError(self.gettext("Not a valid datetime value."))


class DateField(DateTimeField):
    """
    Same as :class:`~wtforms.fields.DateTimeField`, except stores a
    :class:`datetime.date`.
    """

    widget = widgets.DateInput()

    def __init__(self, label=None, validators=None, format="%Y-%m-%d", **kwargs):
        super().__init__(label, validators, format, **kwargs)

    def process_formdata(self, valuelist):
        if not valuelist:
            return

        date_str = " ".join(valuelist)
        for format in self.strptime_format:
            try:
                self.data = datetime.datetime.strptime(date_str, format).date()
                return
            except ValueError:
                self.data = None

        raise ValueError(self.gettext("Not a valid date value."))


class TimeField(DateTimeField):
    """
    Same as :class:`~wtforms.fields.DateTimeField`, except stores a
    :class:`datetime.time`.
    """

    widget = widgets.TimeInput()

    def __init__(self, label=None, validators=None, format="%H:%M", **kwargs):
        super().__init__(label, validators, format, **kwargs)

    def process_formdata(self, valuelist):
        if not valuelist:
            return

        time_str = " ".join(valuelist)
        for format in self.strptime_format:
            try:
                self.data = datetime.datetime.strptime(time_str, format).time()
                return
            except ValueError:
                self.data = None

        raise ValueError(self.gettext("Not a valid time value."))


class MonthField(DateField):
    """
    Same as :class:`~wtforms.fields.DateField`, except represents a month,
    stores a :class:`datetime.date` with `day = 1`.
    """

    widget = widgets.MonthInput()

    def __init__(self, label=None, validators=None, format="%Y-%m", **kwargs):
        super().__init__(label, validators, format, **kwargs)


class WeekField(DateField):
    """
    Same as :class:`~wtforms.fields.DateField`, except represents a week,
    stores a :class:`datetime.date` of the monday of the given week.
    """

    widget = widgets.WeekInput()

    def __init__(self, label=None, validators=None, format="%Y-W%W", **kwargs):
        super().__init__(label, validators, format, **kwargs)

    def process_formdata(self, valuelist):
        if not valuelist:
            return

        time_str = " ".join(valuelist)
        for format in self.strptime_format:
            try:
                if "%w" not in format:
                    # The '%w' week starting day is needed. This defaults it to monday
                    # like ISO 8601 indicates.
                    self.data = datetime.datetime.strptime(
                        f"{time_str}-1", f"{format}-%w"
                    ).date()
                else:
                    self.data = datetime.datetime.strptime(time_str, format).date()
                return
            except ValueError:
                self.data = None

        raise ValueError(self.gettext("Not a valid week value."))


class DateTimeLocalField(DateTimeField):
    """
    Same as :class:`~wtforms.fields.DateTimeField`, but represents an
    ``<input type="datetime-local">``.
    """

    widget = widgets.DateTimeLocalInput()

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "format",
            [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%dT%H:%M",
            ],
        )
        super().__init__(*args, **kwargs)
