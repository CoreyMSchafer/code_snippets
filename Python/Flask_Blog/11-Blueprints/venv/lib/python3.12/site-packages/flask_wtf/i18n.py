from babel import support
from flask import current_app
from flask import request
from flask_babel import get_locale
from wtforms.i18n import messages_path

__all__ = ("Translations", "translations")


def _get_translations():
    """Returns the correct gettext translations.
    Copy from flask-babel with some modifications.
    """

    if not request:
        return None

    # babel should be in extensions for get_locale
    if "babel" not in current_app.extensions:
        return None

    translations = getattr(request, "wtforms_translations", None)

    if translations is None:
        translations = support.Translations.load(
            messages_path(), [get_locale()], domain="wtforms"
        )
        request.wtforms_translations = translations

    return translations


class Translations:
    def gettext(self, string):
        t = _get_translations()
        return string if t is None else t.ugettext(string)

    def ngettext(self, singular, plural, n):
        t = _get_translations()

        if t is None:
            return singular if n == 1 else plural

        return t.ungettext(singular, plural, n)


translations = Translations()
