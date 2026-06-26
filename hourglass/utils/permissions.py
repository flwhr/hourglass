from __future__ import annotations


def user_is_manager(is_admin: bool, user_role_ids: set[int], manager_role_id: int | None) -> bool:
    if is_admin:
        return True
    return manager_role_id is not None and manager_role_id in user_role_ids
