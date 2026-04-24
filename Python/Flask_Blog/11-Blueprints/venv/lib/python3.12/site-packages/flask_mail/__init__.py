from __future__ import annotations

import collections.abc as c
import re
import smtplib
import time
import typing as t
import unicodedata
import warnings
from contextlib import contextmanager
from email import charset
from email import policy
from email.encoders import encode_base64
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from email.utils import formatdate
from email.utils import make_msgid
from email.utils import parseaddr
from mimetypes import guess_type
from types import TracebackType

import blinker
from flask import current_app
from flask import Flask

if t.TYPE_CHECKING:
    import typing_extensions as te

charset.add_charset("utf-8", charset.SHORTEST, None, "utf-8")


class FlaskMailUnicodeDecodeError(UnicodeDecodeError):
    def __init__(self, obj: t.Any, *args: t.Any) -> None:
        self.obj = obj
        super().__init__(*args)

    def __str__(self) -> str:
        original = super().__str__()
        return f"{original}. You passed in {self.obj!r} ({type(self.obj)})"


def force_text(s: t.Any, encoding: str = "utf-8", errors: str = "strict") -> str:
    """
    Similar to smart_text, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.
    """
    if isinstance(s, str):
        return s

    try:
        if isinstance(s, bytes):
            out = str(s, encoding, errors)
        else:
            out = str(s)
    except UnicodeDecodeError as e:
        if not isinstance(s, Exception):
            raise FlaskMailUnicodeDecodeError(s, *e.args) from e

        out = " ".join([force_text(arg, encoding, errors) for arg in s.args])

    return out


def sanitize_subject(subject: str, encoding: str = "utf-8") -> str:
    try:
        subject.encode("ascii")
    except UnicodeEncodeError:
        try:
            subject = Header(subject, encoding).encode()
        except UnicodeEncodeError:
            subject = Header(subject, "utf-8").encode()

    return subject


def sanitize_address(addr: str | tuple[str, str], encoding: str = "utf-8") -> str:
    if isinstance(addr, str):
        addr = parseaddr(force_text(addr))

    nm, addr = addr

    try:
        nm = Header(nm, encoding).encode()
    except UnicodeEncodeError:
        nm = Header(nm, "utf-8").encode()

    try:
        addr.encode("ascii")
    except UnicodeEncodeError:  # IDN
        if "@" in addr:
            localpart, domain = addr.split("@", 1)
            localpart = str(Header(localpart, encoding))
            domain = domain.encode("idna").decode("ascii")
            addr = "@".join([localpart, domain])
        else:
            addr = Header(addr, encoding).encode()

    return formataddr((nm, addr))


def sanitize_addresses(
    addresses: c.Iterable[str | tuple[str, str]], encoding: str = "utf-8"
) -> list[str]:
    return [sanitize_address(e, encoding) for e in addresses]


def _has_newline(line: str) -> bool:
    """Used by has_bad_header to check for \\r or \\n"""
    return "\n" in line or "\r" in line


class Connection:
    """Handles connection to host."""

    def __init__(self, mail: Mail) -> None:
        self.mail = mail
        self.host: smtplib.SMTP | smtplib.SMTP_SSL | None = None
        self.num_emails: int = 0

    def __enter__(self) -> te.Self:
        if self.mail.suppress:
            self.host = None
        else:
            self.host = self.configure_host()

        self.num_emails = 0
        return self

    def __exit__(
        self, exc_type: type[BaseException], exc_value: BaseException, tb: TracebackType
    ) -> None:
        if self.host is not None:
            self.host.quit()

    def configure_host(self) -> smtplib.SMTP | smtplib.SMTP_SSL:
        host: smtplib.SMTP | smtplib.SMTP_SSL

        if self.mail.use_ssl:
            host = smtplib.SMTP_SSL(self.mail.server, self.mail.port)
        else:
            host = smtplib.SMTP(self.mail.server, self.mail.port)

        host.set_debuglevel(int(self.mail.debug))

        if self.mail.use_tls:
            host.starttls()

        if self.mail.username and self.mail.password:
            host.login(self.mail.username, self.mail.password)

        return host

    def send(
        self, message: Message, envelope_from: str | tuple[str, str] | None = None
    ) -> None:
        """Verifies and sends message.

        :param message: Message instance.
        :param envelope_from: Email address to be used in MAIL FROM command.
        """
        assert message.send_to, "No recipients have been added"
        assert message.sender, (
            "The message does not specify a sender and a default sender "
            "has not been configured"
        )

        if message.has_bad_headers():
            raise BadHeaderError

        if message.date is None:
            message.date = time.time()

        if self.host is not None:
            self.host.sendmail(
                sanitize_address(envelope_from or message.sender),
                list(sanitize_addresses(message.send_to)),
                message.as_bytes(),
                message.mail_options,
                message.rcpt_options,
            )

        app = current_app._get_current_object()  # type: ignore[attr-defined]
        email_dispatched.send(app, message=message)
        self.num_emails += 1

        if self.num_emails == self.mail.max_emails:
            self.num_emails = 0

            if self.host:
                self.host.quit()
                self.host = self.configure_host()

    def send_message(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Shortcut for send(msg).

        Takes same arguments as Message constructor.

        :versionadded: 0.3.5
        """
        self.send(Message(*args, **kwargs))


class BadHeaderError(Exception):
    pass


class Attachment:
    """Encapsulates file attachment information.

    :param filename: filename of attachment
    :param content_type: file mimetype
    :param data: the raw file data
    :param disposition: content-disposition (if any)

    .. versionchanged:: 0.10.0
        The `data` argument is required.

    .. versionadded: 0.3.5
    """

    def __init__(
        self,
        filename: str | None = None,
        content_type: str | None = None,
        data: str | bytes | None = None,
        disposition: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        if data is None:
            raise ValueError("The 'data' argument is required.")

        self.data: str | bytes = data

        if content_type is None and filename is not None:
            content_type = guess_type(filename)[0]

        if content_type is None:
            if isinstance(data, str):
                content_type = "text/plain"
            else:
                content_type = "application/octet-stream"

        self.filename: str | None = filename
        self.content_type: str = content_type
        self.disposition: str = disposition or "attachment"

        if headers is None:
            headers = {}

        self.headers: dict[str, str] = headers


class Message:
    """Encapsulates an email message.

    :param subject: email subject header
    :param recipients: list of email addresses
    :param body: plain text message
    :param html: HTML message
    :param alts: A dict or an iterable to go through dict() that contains multipart
                 alternatives
    :param sender: email sender address, or **MAIL_DEFAULT_SENDER** by default
    :param cc: CC list
    :param bcc: BCC list
    :param attachments: list of Attachment instances
    :param reply_to: reply-to address
    :param date: send date
    :param charset: message character set
    :param extra_headers: A dictionary of additional headers for the message
    :param mail_options: A list of ESMTP options to be used in MAIL FROM command
    :param rcpt_options:  A list of ESMTP options to be used in RCPT commands
    """

    def __init__(
        self,
        subject: str = "",
        recipients: list[str | tuple[str, str]] | None = None,
        body: str | None = None,
        html: str | None = None,
        alts: dict[str, str] | c.Iterable[tuple[str, str]] | None = None,
        sender: str | tuple[str, str] | None = None,
        cc: list[str | tuple[str, str]] | None = None,
        bcc: list[str | tuple[str, str]] | None = None,
        attachments: list[Attachment] | None = None,
        reply_to: str | tuple[str, str] | None = None,
        date: float | None = None,
        charset: str | None = None,
        extra_headers: dict[str, str] | None = None,
        mail_options: list[str] | None = None,
        rcpt_options: list[str] | None = None,
    ):
        sender = sender or current_app.extensions["mail"].default_sender

        if isinstance(sender, tuple):
            sender = f"{sender[0]} <{sender[1]}>"

        self.recipients: list[str | tuple[str, str]] = recipients or []
        self.subject: str = subject
        self.sender: str | tuple[str, str] = sender  # pyright: ignore
        self.reply_to: str | tuple[str, str] | None = reply_to
        self.cc: list[str | tuple[str, str]] = cc or []
        self.bcc: list[str | tuple[str, str]] = bcc or []
        self.body: str | None = body
        self.alts: dict[str, str] = dict(alts or {})
        self.html: str | None = html
        self.date: float | None = date
        self.msgId: str = make_msgid()
        self.charset: str | None = charset
        self.extra_headers: dict[str, str] | None = extra_headers
        self.mail_options: list[str] = mail_options or []
        self.rcpt_options: list[str] = rcpt_options or []
        self.attachments: list[Attachment] = attachments or []

    @property
    def send_to(self) -> set[str | tuple[str, str]]:
        out = set(self.recipients)

        if self.bcc:
            out.update(self.bcc)

        if self.cc:
            out.update(self.cc)

        return out

    @property
    def html(self) -> str | None:  # pyright: ignore
        return self.alts.get("html")

    @html.setter
    def html(self, value: str | None) -> None:  # pyright: ignore
        if value is None:
            self.alts.pop("html", None)
        else:
            self.alts["html"] = value

    def _mimetext(self, text: str | None, subtype: str = "plain") -> MIMEText:
        """Creates a MIMEText object with the given subtype (default: 'plain')
        If the text is unicode, the utf-8 charset is used.
        """
        charset = self.charset or "utf-8"
        return MIMEText(text, _subtype=subtype, _charset=charset)  # type: ignore[arg-type]

    def _message(self) -> MIMEBase:
        """Creates the email"""
        ascii_attachments = current_app.extensions["mail"].ascii_attachments
        encoding = self.charset or "utf-8"
        attachments = self.attachments or []
        msg: MIMEBase

        if len(attachments) == 0 and not self.alts:
            # No html content and zero attachments means plain text
            msg = self._mimetext(self.body)
        elif len(attachments) > 0 and not self.alts:
            # No html and at least one attachment means multipart
            msg = MIMEMultipart()
            msg.attach(self._mimetext(self.body))
        else:
            # Anything else
            msg = MIMEMultipart()
            alternative = MIMEMultipart("alternative")
            alternative.attach(self._mimetext(self.body, "plain"))

            for mimetype, content in self.alts.items():
                alternative.attach(self._mimetext(content, mimetype))

            msg.attach(alternative)

        if self.subject:
            msg["Subject"] = sanitize_subject(force_text(self.subject), encoding)

        msg["From"] = sanitize_address(self.sender, encoding)
        msg["To"] = ", ".join(list(set(sanitize_addresses(self.recipients, encoding))))
        msg["Date"] = formatdate(self.date, localtime=True)
        # see RFC 5322 section 3.6.4.
        msg["Message-ID"] = self.msgId

        if self.cc:
            msg["Cc"] = ", ".join(list(set(sanitize_addresses(self.cc, encoding))))

        if self.reply_to:
            msg["Reply-To"] = sanitize_address(self.reply_to, encoding)

        if self.extra_headers:
            for k, v in self.extra_headers.items():
                msg[k] = v

        SPACES = re.compile(r"[\s]+", re.UNICODE)

        for attachment in attachments:
            f = MIMEBase(*attachment.content_type.split("/"))
            f.set_payload(attachment.data)
            encode_base64(f)

            if attachment.filename is not None:
                filename = attachment.filename

                if ascii_attachments:
                    # force filename to ascii
                    filename = unicodedata.normalize("NFKD", attachment.filename)
                    filename = filename.encode("ascii", "ignore").decode("ascii")
                    filename = SPACES.sub(" ", filename).strip()

                try:
                    filename.encode("ascii")
                except UnicodeEncodeError:
                    f.add_header(
                        "Content-Disposition",
                        attachment.disposition,
                        filename=("UTF8", "", filename),
                    )
                else:
                    f.add_header(
                        "Content-Disposition", attachment.disposition, filename=filename
                    )

            for key, value in attachment.headers.items():
                f.add_header(key, value)

            msg.attach(f)

        msg.policy = policy.SMTP
        return msg

    def as_string(self) -> str:
        return self._message().as_string()

    def as_bytes(self) -> bytes:
        return self._message().as_bytes()

    def __str__(self) -> str:
        return self.as_string()

    def __bytes__(self) -> bytes:
        return self.as_bytes()

    def has_bad_headers(self) -> bool:
        """Checks for bad headers i.e. newlines in subject, sender or recipients.
        RFC5322: Allows multiline CRLF with trailing whitespace (FWS) in headers
        """
        headers = [self.sender, *self.recipients]

        if self.reply_to:
            headers.append(self.reply_to)

        for header in headers:
            if isinstance(header, tuple):
                header = f"{header[0]} <{header[1]}>"

            if _has_newline(header):
                return True

        if self.subject:
            if _has_newline(self.subject):
                for linenum, line in enumerate(self.subject.split("\r\n")):
                    if not line:
                        return True
                    if linenum > 0 and line[0] not in "\t ":
                        return True
                    if _has_newline(line):
                        return True
                    if len(line.strip()) == 0:
                        return True

        return False

    def is_bad_headers(self) -> bool:
        warnings.warn(
            "'is_bad_headers' is renamed to 'has_bad_headers'. The old name is"
            " deprecated and will be removed in Flask-Mail 1.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.has_bad_headers()

    def send(self, connection: Connection) -> None:
        """Verifies and sends the message."""

        connection.send(self)

    def add_recipient(self, recipient: str | tuple[str, str]) -> None:
        """Adds another recipient to the message.

        :param recipient: email address of recipient.
        """

        self.recipients.append(recipient)

    def attach(
        self,
        filename: str | None = None,
        content_type: str | None = None,
        data: str | bytes | None = None,
        disposition: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Adds an attachment to the message.

        :param filename: filename of attachment
        :param content_type: file mimetype
        :param data: the raw file data
        :param disposition: content-disposition (if any)
        """
        self.attachments.append(
            Attachment(filename, content_type, data, disposition, headers)
        )


class _MailMixin:
    @contextmanager
    def record_messages(self) -> c.Iterator[list[Message]]:
        """Records all messages. Use in unit tests for example::

            with mail.record_messages() as outbox:
                response = app.test_client.get("/email-sending-view/")
                assert len(outbox) == 1
                assert outbox[0].subject == "testing"

        :versionadded: 0.4
        """
        outbox = []

        def record(app: Flask, message: Message) -> None:
            outbox.append(message)

        with email_dispatched.connected_to(record):
            yield outbox

    def send(self, message: Message) -> None:
        """Sends a single message instance. If TESTING is True the message will
        not actually be sent.

        :param message: a Message instance.
        """

        with self.connect() as connection:
            message.send(connection)

    def send_message(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Shortcut for send(msg).

        Takes same arguments as Message constructor.

        :versionadded: 0.3.5
        """

        self.send(Message(*args, **kwargs))

    def connect(self) -> Connection:
        """Opens a connection to the mail host."""
        app = getattr(self, "app", None) or current_app

        try:
            return Connection(app.extensions["mail"])
        except KeyError as err:
            raise RuntimeError(
                "The current application was not configured with Flask-Mail"
            ) from err


class _Mail(_MailMixin):
    def __init__(
        self,
        server: str,
        username: str | None,
        password: str | None,
        port: int | None,
        use_tls: bool,
        use_ssl: bool,
        default_sender: str | None,
        debug: int,
        max_emails: int | None,
        suppress: bool,
        ascii_attachments: bool,
    ):
        self.server = server
        self.username = username
        self.password = password
        self.port = port
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.default_sender = default_sender
        self.debug = debug
        self.max_emails = max_emails
        self.suppress = suppress
        self.ascii_attachments = ascii_attachments


class Mail(_MailMixin):
    """Manages email messaging."""

    def __init__(self, app: Flask | None = None) -> None:
        self.app = app

        if app is not None:
            self.state: _Mail | None = self.init_app(app)
        else:
            self.state = None

    def init_mail(
        self, config: dict[str, t.Any], debug: bool | int = False, testing: bool = False
    ) -> _Mail:
        return _Mail(
            config.get("MAIL_SERVER", "127.0.0.1"),
            config.get("MAIL_USERNAME"),
            config.get("MAIL_PASSWORD"),
            config.get("MAIL_PORT", 25),
            config.get("MAIL_USE_TLS", False),
            config.get("MAIL_USE_SSL", False),
            config.get("MAIL_DEFAULT_SENDER"),
            int(config.get("MAIL_DEBUG", debug)),
            config.get("MAIL_MAX_EMAILS"),
            config.get("MAIL_SUPPRESS_SEND", testing),
            config.get("MAIL_ASCII_ATTACHMENTS", False),
        )

    def init_app(self, app: Flask) -> _Mail:
        """Initializes your mail settings from the application settings.

        You can use this if you want to set up your Mail instance
        at configuration time.
        """
        state = self.init_mail(app.config, app.debug, app.testing)

        # register extension with app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["mail"] = state
        return state

    def __getattr__(self, name: str) -> t.Any:
        return getattr(self.state, name, None)


signals: blinker.Namespace = blinker.Namespace()
email_dispatched: blinker.NamedSignal = signals.signal(
    "email-dispatched",
    doc="""
Signal sent when an email is dispatched. This signal will also be sent
in testing mode, even though the email will not actually be sent.
""",
)


def __getattr__(name: str) -> t.Any:
    if name == "__version__":
        import importlib.metadata

        warnings.warn(
            "The '__version__' attribute is deprecated and will be removed in"
            " Flask-Mail 1.0. Use feature detection or"
            " 'importlib.metadata.version(\"flask-mail\")' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return importlib.metadata.version("flask-mail")

    raise AttributeError(name)
