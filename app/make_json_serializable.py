# type: ignore
# https://stackoverflow.com/a/18561055

""" Module that monkey-patches json module when it's imported so
JSONEncoder.default() automatically checks for a special "to_json()"
method and uses it to encode the object if found.
"""

from datetime import date, datetime
from json import JSONEncoder


def _default(self, obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj.__dict__


_default.default = JSONEncoder.default  # Save unmodified default.
JSONEncoder.default = _default  # Replace it.
