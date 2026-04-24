Translations
============

WTForms uses gettext to provide translations. Translations for various
strings rendered by WTForms are created and updated by the community. If
you notice that your locale is missing, or find a translation error,
please submit a fix.


Create
------

To create a translation, initialize a catalog in the new locale:

```
$ pybabel init --input-file src/wtforms/locale/wtforms.pot --output-dir src/wtforms/locale --domain wtforms --locale <your locale>
```

This will create some folders under the locale name and copy the
template.

Update
------

To add new translatable string to the catalog:

```
pybabel extract --copyright-holder="WTForms Team" --project="WTForms" --version="$(python -c 'import wtforms; print(wtforms.__version__)')" --output-file src/wtforms/locale/wtforms.pot src/wtforms
```

Edit
----

After creating a translation, or to edit an existing translation, open
the ``.po`` file. While they can be edited by hand, there are also tools
that make working with gettext files easier.

Make sure the `.po` file:

- Is a valid UTF-8 text file.
- Has the header filled out appropriately.
- Translates all messages.


Verify
------

After working on the catalog, verify that it compiles and produces the
correct translations.

```
$ pybabel compile --directory src/wtforms/locale --domain wtforms --statistics
```

Try loading your translations into some sample code to verify they look
correct.


Submit
------

To submit your translation, create a pull request on GitHub.
