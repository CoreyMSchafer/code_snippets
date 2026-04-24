from flask import current_app
from flask import request
from flask import session
from markupsafe import Markup
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.utils import cached_property
from wtforms import Form
from wtforms.meta import DefaultMeta
from wtforms.widgets import HiddenInput

from .csrf import _FlaskFormCSRF

try:
    from .i18n import translations
except ImportError:
    translations = None  # babel not installed


SUBMIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_Auto = object()


class FlaskForm(Form):
    """Flask-specific subclass of WTForms :class:`~wtforms.form.Form`.

    If ``formdata`` is not specified, this will use :attr:`flask.request.form`
    and :attr:`flask.request.files`.  Explicitly pass ``formdata=None`` to
    prevent this.
    """

    class Meta(DefaultMeta):
        csrf_class = _FlaskFormCSRF
        csrf_context = session  # not used, provided for custom csrf_class

        @cached_property
        def csrf(self):
            return current_app.config.get("WTF_CSRF_ENABLED", True)

        @cached_property
        def csrf_secret(self):
            return current_app.config.get("WTF_CSRF_SECRET_KEY", current_app.secret_key)

        @cached_property
        def csrf_field_name(self):
            return current_app.config.get("WTF_CSRF_FIELD_NAME", "csrf_token")

        @cached_property
        def csrf_time_limit(self):
            return current_app.config.get("WTF_CSRF_TIME_LIMIT", 3600)

        def wrap_formdata(self, form, formdata):
            if formdata is _Auto:
                if _is_submitted():
                    if request.files:
                        return CombinedMultiDict((request.files, request.form))
                    elif request.form:
                        return request.form
                    elif request.is_json:
                        return ImmutableMultiDict(request.get_json())

                return None

            return formdata

        def get_translations(self, form):
            if not current_app.config.get("WTF_I18N_ENABLED", True):
                return super().get_translations(form)

            return translations

    def __init__(self, formdata=_Auto, **kwargs):
        super().__init__(formdata=formdata, **kwargs)

    def is_submitted(self):
        """Consider the form submitted if there is an active request and
        the method is ``POST``, ``PUT``, ``PATCH``, or ``DELETE``.
        """

        return _is_submitted()

    def validate_on_submit(self, extra_validators=None):
        """Call :meth:`validate` only if the form is submitted.
        This is a shortcut for ``form.is_submitted() and form.validate()``.
        """
        return self.is_submitted() and self.validate(extra_validators=extra_validators)

    def hidden_tag(self, *fields):
        """Render the form's hidden fields in one call.

        A field is considered hidden if it uses the
        :class:`~wtforms.widgets.HiddenInput` widget.

        If ``fields`` are given, only render the given fields that
        are hidden.  If a string is passed, render the field with that
        name if it exists.

        .. versionchanged:: 0.13

           No longer wraps inputs in hidden div.
           This is valid HTML 5.

        .. versionchanged:: 0.13

           Skip passed fields that aren't hidden.
           Skip passed names that don't exist.
        """

        def hidden_fields(fields):
            for f in fields:
                if isinstance(f, str):
                    f = getattr(self, f, None)

                if f is None or not isinstance(f.widget, HiddenInput):
                    continue

                yield f

        return Markup("\n".join(str(f) for f in hidden_fields(fields or self)))


def _is_submitted():
    """Consider the form submitted if there is an active request and
    the method is ``POST``, ``PUT``, ``PATCH``, or ``DELETE``.
    """

    return bool(request) and request.method in SUBMIT_METHODS
