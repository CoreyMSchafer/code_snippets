#
# Copyright 2016 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
import bandit


def get_url(bid):
    # where our docs are hosted
    base_url = f"https://bandit.readthedocs.io/en/{bandit.__version__}/"

    # NOTE(tkelsey): for some reason this import can't be found when stevedore
    # loads up the formatter plugin that imports this file. It is available
    # later though.
    from bandit.core import extension_loader

    info = extension_loader.MANAGER.plugins_by_id.get(bid)
    if info is not None:
        return f"{base_url}plugins/{bid.lower()}_{info.plugin.__name__}.html"

    info = extension_loader.MANAGER.blacklist_by_id.get(bid)
    if info is not None:
        template = "blacklists/blacklist_{kind}.html#{id}-{name}"
        info["name"] = info["name"].replace("_", "-")

        if info["id"].startswith("B3"):  # B3XX
            # Some of the links are combined, so we have exception cases
            if info["id"] in ["B304", "B305"]:
                info = info.copy()
                info["id"] = "b304-b305"
                info["name"] = "ciphers-and-modes"
            elif info["id"] in [
                "B313",
                "B314",
                "B315",
                "B316",
                "B317",
                "B318",
                "B319",
                "B320",
            ]:
                info = info.copy()
                info["id"] = "b313-b320"
            ext = template.format(
                kind="calls", id=info["id"], name=info["name"]
            )
        else:
            ext = template.format(
                kind="imports", id=info["id"], name=info["name"]
            )

        return base_url + ext.lower()

    return base_url  # no idea, give the docs main page
