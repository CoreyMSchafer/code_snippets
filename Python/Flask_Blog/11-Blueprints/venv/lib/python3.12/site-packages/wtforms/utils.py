import os
import re

_LEADING_SYMBOL = "#" if os.name == "nt" else "-"

# https://docs.python.org/3/library/datetime.html#technical-detail (see NOTE #9)
_DATETIME_STRIP_ZERO_PADDING_FORMATS_RE = re.compile(
    f"%{_LEADING_SYMBOL}["
    "d"  # day of month
    "m"  # month
    "H"  # hour (24-hour)
    "I"  # hour (12-hour)
    "M"  # minutes
    "S"  # seconds
    "U"  # week of year (Sunday first day of week)
    "W"  # week of year (Monday first day of week)
    "V"  # week of year (ISO 8601)
    "]",
    re.MULTILINE,
)


def clean_datetime_format_for_strptime(formats):
    """
    Remove dashes used to disable zero-padding with strftime formats (for
    compatibility with strptime).
    """
    return [
        re.sub(
            _DATETIME_STRIP_ZERO_PADDING_FORMATS_RE,
            lambda m: m[0].replace(_LEADING_SYMBOL, ""),
            format,
        )
        for format in formats
    ]


class UnsetValue:
    """
    An unset value.

    This is used in situations where a blank value like `None` is acceptable
    usually as the default value of a class variable or function parameter
    (iow, usually when `None` is a valid value.)
    """

    def __str__(self):
        return "<unset value>"

    def __repr__(self):
        return "<unset value>"

    def __bool__(self):
        return False

    def __nonzero__(self):
        return False


unset_value = UnsetValue()


class WebobInputWrapper:
    """
    Wrap a webob MultiDict for use as passing as `formdata` to Field.

    Since for consistency, we have decided in WTForms to support as input a
    small subset of the API provided in common between cgi.FieldStorage,
    Django's QueryDict, and Werkzeug's MultiDict, we need to wrap Webob, the
    only supported framework whose multidict does not fit this API, but is
    nevertheless used by a lot of frameworks.

    While we could write a full wrapper to support all the methods, this will
    undoubtedly result in bugs due to some subtle differences between the
    various wrappers. So we will keep it simple.
    """

    def __init__(self, multidict):
        self._wrapped = multidict

    def __iter__(self):
        return iter(self._wrapped)

    def __len__(self):
        return len(self._wrapped)

    def __contains__(self, name):
        return name in self._wrapped

    def getlist(self, name):
        return self._wrapped.getall(name)
