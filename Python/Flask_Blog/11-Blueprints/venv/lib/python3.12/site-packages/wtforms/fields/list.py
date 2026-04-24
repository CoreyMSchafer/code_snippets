import itertools

from wtforms.utils import unset_value

from .. import widgets
from .core import Field
from .core import UnboundField

__all__ = ("FieldList",)


class FieldList(Field):
    """
    Encapsulate an ordered list of multiple instances of the same field type,
    keeping data as a list.

    >>> authors = FieldList(StringField('Name', [validators.DataRequired()]))

    :param unbound_field:
        A partially-instantiated field definition, just like that would be
        defined on a form directly.
    :param min_entries:
        if provided, always have at least this many entries on the field,
        creating blank ones if the provided input does not specify a sufficient
        amount.
    :param max_entries:
        accept no more than this many entries as input, even if more exist in
        formdata.
    :param separator:
        A string which will be suffixed to this field's name to create the
        prefix to enclosed list entries. The default is fine for most uses.
    """

    widget = widgets.ListWidget()

    def __init__(
        self,
        unbound_field,
        label=None,
        validators=None,
        min_entries=0,
        max_entries=None,
        separator="-",
        default=(),
        **kwargs,
    ):
        super().__init__(label, validators, default=default, **kwargs)
        if self.filters:
            raise TypeError(
                "FieldList does not accept any filters. Instead, define"
                " them on the enclosed field."
            )
        assert isinstance(
            unbound_field, UnboundField
        ), "Field must be unbound, not a field class"
        self.unbound_field = unbound_field
        self.min_entries = min_entries
        self.max_entries = max_entries
        self.last_index = -1
        self._prefix = kwargs.get("_prefix", "")
        self._separator = separator
        self._field_separator = unbound_field.kwargs.get("separator", "-")

    def process(self, formdata, data=unset_value, extra_filters=None):
        if extra_filters:
            raise TypeError(
                "FieldList does not accept any filters. Instead, define"
                " them on the enclosed field."
            )

        self.entries = []
        if data is unset_value or not data:
            try:
                data = self.default()
            except TypeError:
                data = self.default

        self.object_data = data

        if formdata:
            indices = sorted(set(self._extract_indices(self.name, formdata)))
            if self.max_entries:
                indices = indices[: self.max_entries]

            idata = iter(data)
            for index in indices:
                try:
                    obj_data = next(idata)
                except StopIteration:
                    obj_data = unset_value
                self._add_entry(formdata, obj_data, index=index)
        else:
            for obj_data in data:
                self._add_entry(formdata, obj_data)

        while len(self.entries) < self.min_entries:
            self._add_entry(formdata)

    def _extract_indices(self, prefix, formdata):
        """
        Yield indices of any keys with given prefix.

        formdata must be an object which will produce keys when iterated.  For
        example, if field 'foo' contains keys 'foo-0-bar', 'foo-1-baz', then
        the numbers 0 and 1 will be yielded, but not necessarily in order.
        """
        offset = len(prefix) + 1
        for k in formdata:
            if k.startswith(prefix):
                k = k[offset:].split(self._field_separator, 1)[0]
                if k.isdigit():
                    yield int(k)

    def validate(self, form, extra_validators=()):
        """
        Validate this FieldList.

        Note that FieldList validation differs from normal field validation in
        that FieldList validates all its enclosed fields first before running any
        of its own validators.
        """
        self.errors = []

        # Run validators on all entries within
        for subfield in self.entries:
            subfield.validate(form)
            self.errors.append(subfield.errors)

        if not any(x for x in self.errors):
            self.errors = []

        chain = itertools.chain(self.validators, extra_validators)
        self._run_validation_chain(form, chain)

        return len(self.errors) == 0

    def populate_obj(self, obj, name):
        values = getattr(obj, name, None)
        try:
            ivalues = iter(values)
        except TypeError:
            ivalues = iter([])

        candidates = itertools.chain(ivalues, itertools.repeat(None))
        _fake = type("_fake", (object,), {})
        output = []
        for field, data in zip(self.entries, candidates):
            fake_obj = _fake()
            fake_obj.data = data
            field.populate_obj(fake_obj, "data")
            output.append(fake_obj.data)

        setattr(obj, name, output)

    def _add_entry(self, formdata=None, data=unset_value, index=None):
        assert (
            not self.max_entries or len(self.entries) < self.max_entries
        ), "You cannot have more than max_entries entries in this FieldList"
        if index is None:
            index = self.last_index + 1
        self.last_index = index
        name = f"{self.short_name}{self._separator}{index}"
        id = f"{self.id}{self._separator}{index}"
        field = self.unbound_field.bind(
            form=None,
            name=name,
            prefix=self._prefix,
            id=id,
            _meta=self.meta,
            translations=self._translations,
        )
        field.process(formdata, data)
        self.entries.append(field)
        return field

    def append_entry(self, data=unset_value):
        """
        Create a new entry with optional default data.

        Entries added in this way will *not* receive formdata however, and can
        only receive object data.
        """
        return self._add_entry(data=data)

    def pop_entry(self):
        """Removes the last entry from the list and returns it."""
        entry = self.entries.pop()
        self.last_index -= 1
        return entry

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, index):
        return self.entries[index]

    @property
    def data(self):
        return [f.data for f in self.entries]
