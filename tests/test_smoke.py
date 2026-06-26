import config
import db
import services


def test_packages_import():
    assert config is not None
    assert db is not None
    assert services is not None
