from utils.permissions import user_is_manager


def test_admin_is_manager():
    assert user_is_manager(True, set(), None) is True


def test_manager_role_grants():
    assert user_is_manager(False, {5, 9}, 5) is True


def test_non_admin_without_role_denied():
    assert user_is_manager(False, {1, 2}, 5) is False


def test_no_manager_role_configured_and_not_admin_denied():
    assert user_is_manager(False, {1, 2}, None) is False
