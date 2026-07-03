"""One store setting — a key/value row behind SettingsService's cache."""

from typing import ClassVar

from arvel import Model


class Setting(Model):
    __table_name__ = "settings"
    __fields__: ClassVar[dict[str, type]] = {"key": str, "value": str}
    __fillable__: ClassVar[list[str]] = ["key", "value"]
