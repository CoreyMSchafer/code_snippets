'''
    flaskext.bcrypt
    ---------------

    A Flask extension providing bcrypt hashing and comparison facilities.

    :copyright: (c) 2011 by Max Countryman.
    :license: BSD, see LICENSE for more details.
'''

from __future__ import absolute_import
from __future__ import print_function

__version_info__ = ('1', '0', '1')
__version__ = '.'.join(__version_info__)
__author__ = 'Max Countryman'
__license__ = 'BSD'
__copyright__ = '(c) 2011 by Max Countryman'
__all__ = ['Bcrypt', 'check_password_hash', 'generate_password_hash']

import hmac

try:
    import bcrypt
except ImportError as e:
    print('bcrypt is required to use Flask-Bcrypt')
    raise e

import hashlib


def generate_password_hash(password, rounds=None):
    '''This helper function wraps the eponymous method of :class:`Bcrypt`. It
    is intended to be used as a helper function at the expense of the
    configuration variable provided when passing back the app object. In other
    words this shortcut does not make use of the app object at all.

    To use this function, simply import it from the module and use it in a
    similar fashion as the original method would be used. Here is a quick
    example::

        from flask_bcrypt import generate_password_hash
        pw_hash = generate_password_hash('hunter2', 10)

    :param password: The password to be hashed.
    :param rounds: The optional number of rounds.
    '''
    return Bcrypt().generate_password_hash(password, rounds)


def check_password_hash(pw_hash, password):
    '''This helper function wraps the eponymous method of :class:`Bcrypt.` It
    is intended to be used as a helper function at the expense of the
    configuration variable provided when passing back the app object. In other
    words this shortcut does not make use of the app object at all.

    To use this function, simply import it from the module and use it in a
    similar fashion as the original method would be used. Here is a quick
    example::

        from flask_bcrypt import check_password_hash
        check_password_hash(pw_hash, 'hunter2') # returns True

    :param pw_hash: The hash to be compared against.
    :param password: The password to compare.
    '''
    return Bcrypt().check_password_hash(pw_hash, password)


class Bcrypt(object):
    '''Bcrypt class container for password hashing and checking logic using
    bcrypt, of course. This class may be used to intialize your Flask app
    object. The purpose is to provide a simple interface for overriding
    Werkzeug's built-in password hashing utilities.

    Although such methods are not actually overriden, the API is intentionally
    made similar so that existing applications which make use of the previous
    hashing functions might be easily adapted to the stronger facility of
    bcrypt.

    To get started you will wrap your application's app object something like
    this::

        app = Flask(__name__)
        bcrypt = Bcrypt(app)

    Now the two primary utility methods are exposed via this object, `bcrypt`.
    So in the context of the application, important data, such as passwords,
    could be hashed using this syntax::

        password = 'hunter2'
        pw_hash = bcrypt.generate_password_hash(password)

    Once hashed, the value is irreversible. However in the case of validating
    logins a simple hashing of candidate password and subsequent comparison.
    Importantly a comparison should be done in constant time. This helps
    prevent timing attacks. A simple utility method is provided for this::

        candidate = 'secret'
        bcrypt.check_password_hash(pw_hash, candidate)

    If both the candidate and the existing password hash are a match
    `check_password_hash` returns True. Otherwise, it returns False.

    .. admonition:: Namespacing Issues

        It's worth noting that if you use the format, `bcrypt = Bcrypt(app)`
        you are effectively overriding the bcrypt module. Though it's unlikely
        you would need to access the module outside of the scope of the
        extension be aware that it's overriden.

        Alternatively consider using a different name, such as `flask_bcrypt
        = Bcrypt(app)` to prevent naming collisions.

    Additionally a configuration value for `BCRYPT_LOG_ROUNDS` may be set in
    the configuration of the Flask app. If none is provided this will
    internally be assigned to 12. (This value is used in determining the
    complexity of the encryption, see bcrypt for more details.)

    You may also set the hash version using the `BCRYPT_HASH_PREFIX` field in
    the configuration of the Flask app. If not set, this will default to `2b`.
    (See bcrypt for more details)

    By default, the bcrypt algorithm has a maximum password length of 72 bytes
    and ignores any bytes beyond that. A common workaround is to hash the
    given password using a cryptographic hash (such as `sha256`), take its
    hexdigest to prevent NULL byte problems, and hash the result with bcrypt.
    If the `BCRYPT_HANDLE_LONG_PASSWORDS` configuration value is set to `True`,
    the workaround described above will be enabled.
    **Warning: do not enable this option on a project that is already using
    Flask-Bcrypt, or you will break password checking.**
    **Warning: if this option is enabled on an existing project, disabling it
    will break password checking.**

    :param app: The Flask application object. Defaults to None.
    '''

    _log_rounds = 12
    _prefix = '2b'
    _handle_long_passwords = False

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        '''Initalizes the application with the extension.

        :param app: The Flask application object.
        '''
        self._log_rounds = app.config.get('BCRYPT_LOG_ROUNDS', 12)
        self._prefix = app.config.get('BCRYPT_HASH_PREFIX', '2b')
        self._handle_long_passwords = app.config.get(
            'BCRYPT_HANDLE_LONG_PASSWORDS', False)

    def _unicode_to_bytes(self, unicode_string):
        '''Converts a unicode string to a bytes object.

        :param unicode_string: The unicode string to convert.'''
        if isinstance(unicode_string, str):
            bytes_object = bytes(unicode_string, 'utf-8')
        else:
            bytes_object = unicode_string
        return bytes_object

    def generate_password_hash(self, password, rounds=None, prefix=None):
        '''Generates a password hash using bcrypt. Specifying `rounds`
        sets the log_rounds parameter of `bcrypt.gensalt()` which determines
        the complexity of the salt. 12 is the default value. Specifying `prefix`
        sets the `prefix` parameter of `bcrypt.gensalt()` which determines the
        version of the algorithm used to create the hash.

        Example usage of :class:`generate_password_hash` might look something
        like this::

            pw_hash = bcrypt.generate_password_hash('secret', 10)

        :param password: The password to be hashed.
        :param rounds: The optional number of rounds.
        :param prefix: The algorithm version to use.
        '''

        if not password:
            raise ValueError('Password must be non-empty.')

        if rounds is None:
            rounds = self._log_rounds
        if prefix is None:
            prefix = self._prefix

        # Python 3 unicode strings must be encoded as bytes before hashing.
        password = self._unicode_to_bytes(password)
        prefix = self._unicode_to_bytes(prefix)

        if self._handle_long_passwords:
            password = hashlib.sha256(password).hexdigest()
            password = self._unicode_to_bytes(password)

        salt = bcrypt.gensalt(rounds=rounds, prefix=prefix)
        return bcrypt.hashpw(password, salt)

    def check_password_hash(self, pw_hash, password):
        '''Tests a password hash against a candidate password. The candidate
        password is first hashed and then subsequently compared in constant
        time to the existing hash. This will either return `True` or `False`.

        Example usage of :class:`check_password_hash` would look something
        like this::

            pw_hash = bcrypt.generate_password_hash('secret', 10)
            bcrypt.check_password_hash(pw_hash, 'secret') # returns True

        :param pw_hash: The hash to be compared against.
        :param password: The password to compare.
        '''

        # Python 3 unicode strings must be encoded as bytes before hashing.
        pw_hash = self._unicode_to_bytes(pw_hash)
        password = self._unicode_to_bytes(password)

        if self._handle_long_passwords:
            password = hashlib.sha256(password).hexdigest()
            password = self._unicode_to_bytes(password)

        return hmac.compare_digest(bcrypt.hashpw(password, pw_hash), pw_hash)
