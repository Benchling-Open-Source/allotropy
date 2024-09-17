import re

from allotropy.parsers.utils.uuids import random_uuid_str


def test_random_uuid_str() -> None:
    uuid = random_uuid_str()
    assert isinstance(uuid, str)
    assert re.match(
        "[a-zA-Z0-9]{8}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{12}",
        uuid,
    )
