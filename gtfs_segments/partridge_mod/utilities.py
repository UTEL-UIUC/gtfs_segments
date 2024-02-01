from typing import Any, BinaryIO, Set

from charset_normalizer import detect
from pandas.core.common import flatten


def setwrap(value: Any) -> Set[str]:
    """
    Returns a flattened and stringified set from the given object or iterable.

    For use in public functions which accept argmuents or kwargs that can be
    one object or a list of objects.
    """
    return set(map(str, set(flatten([value]))))


def detect_encoding(file: BinaryIO, limit: int = 2500) -> str:
    """
    Return encoding of provided input stream.

    Most of the time it's unicode, but if we are unable to decode the input
    natively, use `chardet` to determine the encoding heuristically.
    """
    unicode_decodable = True

    for line_no, line in enumerate(file):
        try:
            line.decode("utf-8")
        except UnicodeDecodeError:
            unicode_decodable = False
            break

        if line_no > limit:
            break

    if unicode_decodable:
        return "utf-8"

    file.seek(0)
    encoding = detect(file.read())["encoding"]
    return encoding
