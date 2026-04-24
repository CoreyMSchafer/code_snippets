import ipaddress
import math
import re
import uuid

__all__ = (
    "DataRequired",
    "data_required",
    "Email",
    "email",
    "EqualTo",
    "equal_to",
    "IPAddress",
    "ip_address",
    "InputRequired",
    "input_required",
    "Length",
    "length",
    "NumberRange",
    "number_range",
    "Optional",
    "optional",
    "Regexp",
    "regexp",
    "URL",
    "url",
    "AnyOf",
    "any_of",
    "NoneOf",
    "none_of",
    "MacAddress",
    "mac_address",
    "UUID",
    "ValidationError",
    "StopValidation",
    "readonly",
    "ReadOnly",
    "disabled",
    "Disabled",
)


class ValidationError(ValueError):
    """
    Raised when a validator fails to validate its input.
    """

    def __init__(self, message="", *args, **kwargs):
        ValueError.__init__(self, message, *args, **kwargs)


class StopValidation(Exception):
    """
    Causes the validation chain to stop.

    If StopValidation is raised, no more validators in the validation chain are
    called. If raised with a message, the message will be added to the errors
    list.
    """

    def __init__(self, message="", *args, **kwargs):
        Exception.__init__(self, message, *args, **kwargs)


class EqualTo:
    """
    Compares the values of two fields.

    :param fieldname:
        The name of the other field to compare to.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated with `%(other_label)s` and `%(other_name)s` to provide a
        more helpful error.
    """

    def __init__(self, fieldname, message=None):
        self.fieldname = fieldname
        self.message = message

    def __call__(self, form, field):
        try:
            other = form[self.fieldname]
        except KeyError as exc:
            raise ValidationError(
                field.gettext("Invalid field name '%s'.") % self.fieldname
            ) from exc
        if field.data == other.data:
            return

        d = {
            "other_label": hasattr(other, "label")
            and other.label.text
            or self.fieldname,
            "other_name": self.fieldname,
        }
        message = self.message
        if message is None:
            message = field.gettext("Field must be equal to %(other_name)s.")

        raise ValidationError(message % d)


class Length:
    """
    Validates the length of a string.

    :param min:
        The minimum required length of the string. If not provided, minimum
        length will not be checked.
    :param max:
        The maximum length of the string. If not provided, maximum length
        will not be checked.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated using `%(min)d` and `%(max)d` if desired. Useful defaults
        are provided depending on the existence of min and max.

    When supported, sets the `minlength` and `maxlength` attributes on widgets.
    """

    def __init__(self, min=-1, max=-1, message=None):
        assert (
            min != -1 or max != -1
        ), "At least one of `min` or `max` must be specified."
        assert max == -1 or min <= max, "`min` cannot be more than `max`."
        self.min = min
        self.max = max
        self.message = message
        self.field_flags = {}
        if self.min != -1:
            self.field_flags["minlength"] = self.min
        if self.max != -1:
            self.field_flags["maxlength"] = self.max

    def __call__(self, form, field):
        length = field.data and len(field.data) or 0
        if length >= self.min and (self.max == -1 or length <= self.max):
            return

        if self.message is not None:
            message = self.message

        elif self.max == -1:
            message = field.ngettext(
                "Field must be at least %(min)d character long.",
                "Field must be at least %(min)d characters long.",
                self.min,
            )
        elif self.min == -1:
            message = field.ngettext(
                "Field cannot be longer than %(max)d character.",
                "Field cannot be longer than %(max)d characters.",
                self.max,
            )
        elif self.min == self.max:
            message = field.ngettext(
                "Field must be exactly %(max)d character long.",
                "Field must be exactly %(max)d characters long.",
                self.max,
            )
        else:
            message = field.gettext(
                "Field must be between %(min)d and %(max)d characters long."
            )

        raise ValidationError(message % dict(min=self.min, max=self.max, length=length))


class NumberRange:
    """
    Validates that a number is of a minimum and/or maximum value, inclusive.
    This will work with any comparable number type, such as floats and
    decimals, not just integers.

    :param min:
        The minimum required value of the number. If not provided, minimum
        value will not be checked.
    :param max:
        The maximum value of the number. If not provided, maximum value
        will not be checked.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated using `%(min)s` and `%(max)s` if desired. Useful defaults
        are provided depending on the existence of min and max.

    When supported, sets the `min` and `max` attributes on widgets.
    """

    def __init__(self, min=None, max=None, message=None):
        self.min = min
        self.max = max
        self.message = message
        self.field_flags = {}
        if self.min is not None:
            self.field_flags["min"] = self.min
        if self.max is not None:
            self.field_flags["max"] = self.max

    def __call__(self, form, field):
        data = field.data
        if (
            data is not None
            and not math.isnan(data)
            and (self.min is None or data >= self.min)
            and (self.max is None or data <= self.max)
        ):
            return

        if self.message is not None:
            message = self.message

        # we use %(min)s interpolation to support floats, None, and
        # Decimals without throwing a formatting exception.
        elif self.max is None:
            message = field.gettext("Number must be at least %(min)s.")

        elif self.min is None:
            message = field.gettext("Number must be at most %(max)s.")

        else:
            message = field.gettext("Number must be between %(min)s and %(max)s.")

        raise ValidationError(message % dict(min=self.min, max=self.max))


class Optional:
    """
    Allows empty input and stops the validation chain from continuing.

    If input is empty, also removes prior errors (such as processing errors)
    from the field.

    :param strip_whitespace:
        If True (the default) also stop the validation chain on input which
        consists of only whitespace.

    Sets the `optional` attribute on widgets.
    """

    def __init__(self, strip_whitespace=True):
        if strip_whitespace:
            self.string_check = lambda s: s.strip()
        else:
            self.string_check = lambda s: s

        self.field_flags = {"optional": True}

    def __call__(self, form, field):
        if (
            not field.raw_data
            or isinstance(field.raw_data[0], str)
            and not self.string_check(field.raw_data[0])
        ):
            field.errors[:] = []
            raise StopValidation()


class DataRequired:
    """
    Checks the field's data is 'truthy' otherwise stops the validation chain.

    This validator checks that the ``data`` attribute on the field is a 'true'
    value (effectively, it does ``if field.data``.) Furthermore, if the data
    is a string type, a string containing only whitespace characters is
    considered false.

    If the data is empty, also removes prior errors (such as processing errors)
    from the field.

    **NOTE** this validator used to be called `Required` but the way it behaved
    (requiring coerced data, not input data) meant it functioned in a way
    which was not symmetric to the `Optional` validator and furthermore caused
    confusion with certain fields which coerced data to 'falsey' values like
    ``0``, ``Decimal(0)``, ``time(0)`` etc. Unless a very specific reason
    exists, we recommend using the :class:`InputRequired` instead.

    :param message:
        Error message to raise in case of a validation error.

    Sets the `required` attribute on widgets.
    """

    def __init__(self, message=None):
        self.message = message
        self.field_flags = {"required": True}

    def __call__(self, form, field):
        if field.data and (not isinstance(field.data, str) or field.data.strip()):
            return

        if self.message is None:
            message = field.gettext("This field is required.")
        else:
            message = self.message

        field.errors[:] = []
        raise StopValidation(message)


class InputRequired:
    """
    Validates that input was provided for this field.

    Note there is a distinction between this and DataRequired in that
    InputRequired looks that form-input data was provided, and DataRequired
    looks at the post-coercion data. This means that this validator only checks
    whether non-empty data was sent, not whether non-empty data was coerced
    from that data. Initially populated data is not considered sent.

    Sets the `required` attribute on widgets.
    """

    def __init__(self, message=None):
        self.message = message
        self.field_flags = {"required": True}

    def __call__(self, form, field):
        if field.raw_data and field.raw_data[0]:
            return

        if self.message is None:
            message = field.gettext("This field is required.")
        else:
            message = self.message

        field.errors[:] = []
        raise StopValidation(message)


class Regexp:
    """
    Validates the field against a user provided regexp.

    :param regex:
        The regular expression string to use. Can also be a compiled regular
        expression pattern.
    :param flags:
        The regexp flags to use, for example re.IGNORECASE. Ignored if
        `regex` is not a string.
    :param message:
        Error message to raise in case of a validation error.
    """

    def __init__(self, regex, flags=0, message=None):
        if isinstance(regex, str):
            regex = re.compile(regex, flags)
        self.regex = regex
        self.message = message

    def __call__(self, form, field, message=None):
        match = self.regex.match(field.data or "")
        if match:
            return match

        if message is None:
            if self.message is None:
                message = field.gettext("Invalid input.")
            else:
                message = self.message

        raise ValidationError(message)


class Email:
    """
    Validates an email address. Requires email_validator package to be
    installed. For ex: pip install wtforms[email].

    :param message:
        Error message to raise in case of a validation error.
    :param granular_message:
        Use validation failed message from email_validator library
        (Default False).
    :param check_deliverability:
        Perform domain name resolution check (Default False).
    :param allow_smtputf8:
        Fail validation for addresses that would require SMTPUTF8
        (Default True).
    :param allow_empty_local:
        Allow an empty local part (i.e. @example.com), e.g. for validating
        Postfix aliases (Default False).
    """

    def __init__(
        self,
        message=None,
        granular_message=False,
        check_deliverability=False,
        allow_smtputf8=True,
        allow_empty_local=False,
    ):
        self.message = message
        self.granular_message = granular_message
        self.check_deliverability = check_deliverability
        self.allow_smtputf8 = allow_smtputf8
        self.allow_empty_local = allow_empty_local

    def __call__(self, form, field):
        try:
            import email_validator
        except ImportError as exc:  # pragma: no cover
            raise Exception(
                "Install 'email_validator' for email validation support."
            ) from exc

        try:
            if field.data is None:
                raise email_validator.EmailNotValidError()
            email_validator.validate_email(
                field.data,
                check_deliverability=self.check_deliverability,
                allow_smtputf8=self.allow_smtputf8,
                allow_empty_local=self.allow_empty_local,
            )
        except email_validator.EmailNotValidError as e:
            message = self.message
            if message is None:
                if self.granular_message:
                    message = field.gettext(e)
                else:
                    message = field.gettext("Invalid email address.")
            raise ValidationError(message) from e


class IPAddress:
    """
    Validates an IP address.

    :param ipv4:
        If True, accept IPv4 addresses as valid (default True)
    :param ipv6:
        If True, accept IPv6 addresses as valid (default False)
    :param message:
        Error message to raise in case of a validation error.
    """

    def __init__(self, ipv4=True, ipv6=False, message=None):
        if not ipv4 and not ipv6:
            raise ValueError(
                "IP Address Validator must have at least one of ipv4 or ipv6 enabled."
            )
        self.ipv4 = ipv4
        self.ipv6 = ipv6
        self.message = message

    def __call__(self, form, field):
        value = field.data
        valid = False
        if value:
            valid = (self.ipv4 and self.check_ipv4(value)) or (
                self.ipv6 and self.check_ipv6(value)
            )

        if valid:
            return

        message = self.message
        if message is None:
            message = field.gettext("Invalid IP address.")
        raise ValidationError(message)

    @classmethod
    def check_ipv4(cls, value):
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            return False

        if not isinstance(address, ipaddress.IPv4Address):
            return False

        return True

    @classmethod
    def check_ipv6(cls, value):
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            return False

        if not isinstance(address, ipaddress.IPv6Address):
            return False

        return True


class MacAddress(Regexp):
    """
    Validates a MAC address.

    :param message:
        Error message to raise in case of a validation error.
    """

    def __init__(self, message=None):
        pattern = r"^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$"
        super().__init__(pattern, message=message)

    def __call__(self, form, field):
        message = self.message
        if message is None:
            message = field.gettext("Invalid Mac address.")

        super().__call__(form, field, message)


class URL(Regexp):
    """
    Simple regexp based url validation. Much like the email validator, you
    probably want to validate the url later by other means if the url must
    resolve.

    :param require_tld:
        If true, then the domain-name portion of the URL must contain a .tld
        suffix.  Set this to false if you want to allow domains like
        `localhost`.
    :param allow_ip:
        If false, then give ip as host will fail validation
    :param message:
        Error message to raise in case of a validation error.
    """

    def __init__(self, require_tld=True, allow_ip=True, message=None):
        regex = (
            r"^[a-z]+://"
            r"(?P<host>[^\/\?:]+)"
            r"(?P<port>:[0-9]+)?"
            r"(?P<path>\/.*?)?"
            r"(?P<query>\?.*)?$"
        )
        super().__init__(regex, re.IGNORECASE, message)
        self.validate_hostname = HostnameValidation(
            require_tld=require_tld, allow_ip=allow_ip
        )

    def __call__(self, form, field):
        message = self.message
        if message is None:
            message = field.gettext("Invalid URL.")

        match = super().__call__(form, field, message)
        if not self.validate_hostname(match.group("host")):
            raise ValidationError(message)


class UUID:
    """
    Validates a UUID.

    :param message:
        Error message to raise in case of a validation error.
    """

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        message = self.message
        if message is None:
            message = field.gettext("Invalid UUID.")
        try:
            uuid.UUID(field.data)
        except ValueError as exc:
            raise ValidationError(message) from exc


class AnyOf:
    """
    Compares the incoming data to a sequence of valid inputs.

    :param values:
        A sequence of valid inputs.
    :param message:
        Error message to raise in case of a validation error. `%(values)s`
        contains the list of values.
    :param values_formatter:
        Function used to format the list of values in the error message.
    """

    def __init__(self, values, message=None, values_formatter=None):
        self.values = values
        self.message = message
        if values_formatter is None:
            values_formatter = self.default_values_formatter
        self.values_formatter = values_formatter

    def __call__(self, form, field):
        data = field.data if isinstance(field.data, list) else [field.data]
        if any(d in self.values for d in data):
            return

        message = self.message
        if message is None:
            message = field.gettext("Invalid value, must be one of: %(values)s.")

        raise ValidationError(message % dict(values=self.values_formatter(self.values)))

    @staticmethod
    def default_values_formatter(values):
        return ", ".join(str(x) for x in values)


class NoneOf:
    """
    Compares the incoming data to a sequence of invalid inputs.

    :param values:
        A sequence of invalid inputs.
    :param message:
        Error message to raise in case of a validation error. `%(values)s`
        contains the list of values.
    :param values_formatter:
        Function used to format the list of values in the error message.
    """

    def __init__(self, values, message=None, values_formatter=None):
        self.values = values
        self.message = message
        if values_formatter is None:
            values_formatter = self.default_values_formatter
        self.values_formatter = values_formatter

    def __call__(self, form, field):
        data = field.data if isinstance(field.data, list) else [field.data]
        if not any(d in self.values for d in data):
            return

        message = self.message
        if message is None:
            message = field.gettext("Invalid value, can't be any of: %(values)s.")

        raise ValidationError(message % dict(values=self.values_formatter(self.values)))

    @staticmethod
    def default_values_formatter(v):
        return ", ".join(str(x) for x in v)


class HostnameValidation:
    """
    Helper class for checking hostnames for validation.

    This is not a validator in and of itself, and as such is not exported.
    """

    hostname_part = re.compile(r"^(xn-|[a-z0-9_]+)(-[a-z0-9_-]+)*$", re.IGNORECASE)
    tld_part = re.compile(r"^([a-z]{2,20}|xn--([a-z0-9]+-)*[a-z0-9]+)$", re.IGNORECASE)

    def __init__(self, require_tld=True, allow_ip=False):
        self.require_tld = require_tld
        self.allow_ip = allow_ip

    def __call__(self, hostname):
        if self.allow_ip and (
            IPAddress.check_ipv4(hostname) or IPAddress.check_ipv6(hostname)
        ):
            return True

        # Encode out IDNA hostnames. This makes further validation easier.
        try:
            hostname = hostname.encode("idna")
        except UnicodeError:
            pass

        # Turn back into a string in Python 3x
        if not isinstance(hostname, str):
            hostname = hostname.decode("ascii")

        if len(hostname) > 253:
            return False

        # Check that all labels in the hostname are valid
        parts = hostname.split(".")
        for part in parts:
            if not part or len(part) > 63:
                return False
            if not self.hostname_part.match(part):
                return False

        if self.require_tld and (len(parts) < 2 or not self.tld_part.match(parts[-1])):
            return False

        return True


class ReadOnly:
    """
    Set a field readonly.

    Validation fails if the form data is different than the
    field object data, or if unset, from the field default data.
    """

    def __init__(self):
        self.field_flags = {"readonly": True}

    def __call__(self, form, field):
        if field.data != field.object_data:
            raise ValidationError(field.gettext("This field cannot be edited."))


class Disabled:
    """
    Set a field disabled.

    Validation fails if the form data has any value.
    """

    def __init__(self):
        self.field_flags = {"disabled": True}

    def __call__(self, form, field):
        if field.raw_data is not None:
            raise ValidationError(
                field.gettext("This field is disabled and cannot have a value.")
            )


email = Email
equal_to = EqualTo
ip_address = IPAddress
mac_address = MacAddress
length = Length
number_range = NumberRange
optional = Optional
input_required = InputRequired
data_required = DataRequired
regexp = Regexp
url = URL
any_of = AnyOf
none_of = NoneOf
readonly = ReadOnly
disabled = Disabled
