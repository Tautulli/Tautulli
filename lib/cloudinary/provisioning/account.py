from cloudinary.api_client.call_account_api import _call_account_api
from cloudinary.utils import encode_list


SUB_ACCOUNTS_SUB_PATH = "sub_accounts"
USERS_SUB_PATH = "users"
USER_GROUPS_SUB_PATH = "user_groups"


class Role(object):
    """
    A user role to use in the user management API (create/update user).
    """
    MASTER_ADMIN = "master_admin"
    ADMIN = "admin"
    BILLING = "billing"
    TECHNICAL_ADMIN = "technical_admin"
    REPORTS = "reports"
    MEDIA_LIBRARY_ADMIN = "media_library_admin"
    MEDIA_LIBRARY_USER = "media_library_user"


def sub_accounts(enabled=None, ids=None, prefix=None, **options):
    """
    List all sub accounts
    :param enabled:     Whether to only return enabled sub-accounts (true) or disabled accounts (false).
                        Default: all accounts are returned (both enabled and disabled).
    :type enabled:      bool, optional
    :param ids:         List of sub-account IDs. Up to 100. When provided, other filters are ignored.
    :type ids:          list, optional
    :param prefix:      Search by prefix of the sub-account name. Case-insensitive.
    :type prefix:       str, optional
    :param options:     Generic advanced options dict, see online documentation
    :type options:      dict, optional
    :return:            A list of sub accounts
    :rtype:             dict
    """
    uri = [SUB_ACCOUNTS_SUB_PATH]
    params = {"ids": ids, "enabled": enabled, "prefix": prefix}
    return _call_account_api("GET", uri, params=params, **options)


def create_sub_account(name, cloud_name=None, custom_attributes=None, enabled=None,
                       base_account=None, **options):
    """
    Create a new sub account
    :param name:                Name of the new sub account
    :type name:                 str
    :param cloud_name:          A case-insensitive cloud name comprised of alphanumeric and underscore characters.
                                * Generates an error if the cloud name is not unique across all Cloudinary accounts.
    :type cloud_name:           str, optional
    :param custom_attributes:   Any custom attributes you want to associate with the sub-account
    :type custom_attributes:    dict, optional
    :param enabled:             Whether to create the account as enabled (default is enabled).
    :type enabled:              bool, optional
    :param base_account:        ID of sub-account from which to copy settings
    :type base_account:         str, optional
    :param options:             Generic advanced options dict, see online documentation
    :type options:              dict, optional
    :return:                    The created sub account
    :rtype:                     dict
    """
    uri = [SUB_ACCOUNTS_SUB_PATH]
    params = {"name": name,
              "cloud_name": cloud_name,
              "custom_attributes": custom_attributes,
              "enabled": enabled,
              "base_account": base_account}
    return _call_account_api("POST", uri, params=params, **options)


def delete_sub_account(sub_account_id, **options):
    """
    Delete a sub account
    :param sub_account_id:      The id of the sub account
    :type sub_account_id:       str
    :param options:             Generic advanced options dict, see online documentation
    :type options:              dict, optional
    :return:                    Result message
    :rtype:                     dict
    """
    uri = [SUB_ACCOUNTS_SUB_PATH, sub_account_id]
    return _call_account_api("delete", uri, {}, **options)


def sub_account(sub_account_id, **options):
    """
    Get information of a sub account
    :param sub_account_id:      The id of the sub account
    :type sub_account_id:       str
    :param options:             Generic advanced options dict, see online documentation
    :type options:              dict, optional
    :return:                    A sub account
    :rtype:                     dict
    """
    uri = [SUB_ACCOUNTS_SUB_PATH, sub_account_id]
    return _call_account_api("get", uri, {}, **options)


def update_sub_account(sub_account_id, name=None, cloud_name=None, custom_attributes=None, enabled=None, **options):
    """
    Update a sub account
    :param sub_account_id:      The id of the sub account
    :type sub_account_id:       str
    :param name:                Name of the account
    :type name:                 str, optional
    :param cloud_name:          Unique cloud name
    :type cloud_name:           str, optional
    :param custom_attributes:   Any custom attributes you want to associate with the sub-account.
    :type custom_attributes:    dict, optional
    :param enabled:             Whether to create the account as enabled (default is enabled).
    :type enabled:              bool, optional
    :param options:             Generic advanced options dict, see online documentation
    :type options:              dict, optional
    :return:                    Updated sub account
    :rtype:                     dict
    """
    uri = [SUB_ACCOUNTS_SUB_PATH, sub_account_id]
    params = {"name": name,
              "cloud_name": cloud_name,
              "custom_attributes": custom_attributes,
              "enabled": enabled}
    return _call_account_api("put", uri, params=params, **options)


def users(user_ids=None, sub_account_id=None, pending=None, prefix=None, **options):
    """
    List all users
    :param user_ids:        The ids of the users to fetch
    :type user_ids:         list, optional
    :param sub_account_id:  The id of a sub account
    :type sub_account_id:   str, optional
    :param pending:         Limit results to pending users (True),
                            users that are not pending (False),
                            or all users (None, the default).
    :type pending:          bool, optional
    :param prefix:          User prefix
    :type prefix:           str, optional
    :param options:         Generic advanced options dict, see online documentation.
    :type options:          dict, optional
    :return:                List of users associated with the account
    :rtype:                 dict
    """
    uri = [USERS_SUB_PATH]
    user_ids = encode_list(user_ids)
    params = {"ids": user_ids,
              "sub_account_id": sub_account_id,
              "pending": pending,
              "prefix": prefix}
    return _call_account_api("get", uri, params=params, **options)


def create_user(name, email, role, sub_account_ids=None, **options):
    """
    Create a user
    :param name:                Username
    :type name:                 str
    :param email:               User's email
    :type email:                str
    :param role:                User's role
    :type role:                 str
    :param sub_account_ids:     Optional. Sub accounts to associate with the user
    :type sub_account_ids:      list, optional
    :param options:             Generic advanced options dict, see online documentation.
    :type options:              dict, optional
    :return:                    Details of created user
    :rtype:                     dict
    """
    uri = [USERS_SUB_PATH]
    params = {"name": name,
              "email": email,
              "role": role,
              "sub_account_ids": sub_account_ids}
    return _call_account_api("post", uri, params=params, **options)


def delete_user(user_id, **options):
    """
    Delete a user
    :param user_id:             The id of user to delete
    :type user_id:              str
    :param options:             Generic advanced options dict, see online documentation.
    :type options:              dict, optional
    :return:                    Result message
    :rtype:                     dict
    """
    uri = [USERS_SUB_PATH, user_id]
    return _call_account_api("delete", uri, {}, **options)


def user(user_id, **options):
    """
    Get information of a user
    :param user_id:             The id of the user
    :type user_id:              str
    :param options:             Generic advanced options dict, see online documentation.
    :type options:              dict, optional
    :return:                    A user
    :rtype:                     dict
    """
    uri = [USERS_SUB_PATH, user_id]
    return _call_account_api("get", uri, {}, **options)


def update_user(user_id, name=None, email=None, role=None, sub_account_ids=None, **options):
    """
    Update a user
    :param user_id:             The id of the user to update
    :type user_id:              str
    :param name:                Username
    :type name:                 str, optional
    :param email:               User's email
    :type email:                str, optional
    :param role:                User's role
    :type role:                 Role, optional
    :param sub_account_ids:     The list of sub-account IDs that this user can access.
                                Note: This parameter is ignored if the role is specified as master_admin.
    :type sub_account_ids:      list, optional
    :param options:             Generic advanced options dict, see online documentation.
    :type options:              dict, optional
    :return:                    The updated user
    :rtype:                     dict
    """
    uri = [USERS_SUB_PATH, user_id]
    params = {"name": name,
              "email": email,
              "role": role,
              "sub_account_ids": sub_account_ids}
    return _call_account_api("put", uri, params=params, **options)


def user_groups(**options):
    """
    List all user groups
    :param options:         Generic advanced options dict, see online documentation
    :type options:          dict, optional
    :return:                List of user groups
    :rtype:                 ProvisioningAPIRespose
    """
    uri = [USER_GROUPS_SUB_PATH]
    return _call_account_api("get", uri, {}, **options)


def create_user_group(name, **options):
    """
    Create a new user group
    :param name:            Name of the user group
    :type name:             str
    :param options:         Generic advanced options dict, see online documentation
    :type options:          dict, optional
    :return:                The newly created group
    :rtype:                 dict
    """
    uri = [USER_GROUPS_SUB_PATH]
    params = {"name": name}
    return _call_account_api("post", uri, params, **options)


def update_user_group(user_group_id, name, **options):
    """
    Update a user group
    :param user_group_id:       The id of the user group to update
    :type user_group_id:        str
    :param name:                Name of the user group
    :type name:                 str, optional
    :param options:             Generic advanced options dict, see online documentation
    :type options:              dict, optional
    :return:                    The updated group
    :rtype:                     dict
    """
    uri = [USER_GROUPS_SUB_PATH, user_group_id]
    params = {"name": name}
    return _call_account_api("put", uri, params, **options)


def delete_user_group(user_group_id, **options):
    """
    Delete a user group
    :param user_group_id:       The id of the user group to delete
    :type user_group_id:        str
    :param options:             Generic advanced options dict, see online documentation
    :type options:              dict, optional
    :return:                    The result message
    :rtype:                     dict
    """
    uri = [USER_GROUPS_SUB_PATH, user_group_id]
    return _call_account_api("delete", uri, {}, **options)


def user_group(user_group_id, **options):
    """
    Get information of a user group
    :param user_group_id:       The id of the user group
    :type user_group_id:        str
    :param options:             Generic advanced options dict, see online documentation
    :type options:              dict, optional
    :return:                    Details of the group
    :rtype:                     dict
    """
    uri = [USER_GROUPS_SUB_PATH, user_group_id]
    return _call_account_api("get", uri, {}, **options)


def add_user_to_group(user_group_id, user_id, **options):
    """
    Add a user to a user group
    :param user_group_id:       The id of the user group to add the user to
    :type user_group_id:        str
    :param user_id:             The user id to add
    :type user_id:              str
    :param options:             Generic advanced options dict, see online documentation
    :type options:              dict, optional
    :return:                    List of users in the group
    :rtype:                     dict
    """
    uri = [USER_GROUPS_SUB_PATH, user_group_id, "users", user_id]
    return _call_account_api("post", uri, {}, **options)


def remove_user_from_group(user_group_id, user_id, **options):
    """
    Remove a user from a user group
    :param user_group_id:       The id of the user group to remove the user from
    :type user_group_id:        str
    :param user_id:             The id of the user to remove
    :type user_id:              str
    :param options:             Generic advanced options dict, see online documentation
    :type options:              dict, optional
    :return:                    List of users in the group
    :rtype:                     dict
    """
    uri = [USER_GROUPS_SUB_PATH, user_group_id, "users", user_id]
    return _call_account_api("delete", uri, {}, **options)


def user_group_users(user_group_id, **options):
    """
    Get all users in a user group
    :param user_group_id:       The id of user group to get list of users
    :type user_group_id:        str
    :param options:             Generic advanced options dict, see online documentation
    :type options:              dict, optional
    :return:                    List of users in the group
    :rtype:                     dict
    """
    uri = [USER_GROUPS_SUB_PATH, user_group_id, "users"]
    return _call_account_api("get", uri, {}, **options)


def user_in_user_groups(user_id, **options):
    """
    Get all user groups a user belongs to
    :param user_id:             The id of user
    :param user_id:             str
    :param options:             Generic advanced options dict, see online documentation
    :type options:              dict, optional
    :return:                    List of groups user is in
    :rtype:                     dict
    """
    uri = [USER_GROUPS_SUB_PATH, user_id]
    return _call_account_api("get", uri, {}, **options)
