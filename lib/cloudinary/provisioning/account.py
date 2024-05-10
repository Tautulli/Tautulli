from cloudinary.api_client.call_account_api import _call_account_api
from cloudinary.utils import encode_list

SUB_ACCOUNTS_SUB_PATH = "sub_accounts"
USERS_SUB_PATH = "users"
USER_GROUPS_SUB_PATH = "user_groups"
ACCESS_KEYS = "access_keys"


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
              "base_sub_account_id": base_account}
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


def users(user_ids=None, sub_account_id=None, pending=None, prefix=None, last_login=None, from_date=None, to_date=None,
          **options):
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
    :param last_login:      Return only users that last logged in in the specified range of dates (true), 
                            users that didn't last logged in in that range (false), or all users (None).
    :type last_login:       bool, optional
    :param from_date:       Last login start date.
    :type from_date:        datetime, optional
    :param to_date:         Last login end date.
    :type to_date:          datetime, optional
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
              "prefix": prefix,
              "last_login": last_login,
              "from": from_date,
              "to": to_date}
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
    :type user_id:              str
    :param options:             Generic advanced options dict, see online documentation
    :type options:              dict, optional
    :return:                    List of groups user is in
    :rtype:                     dict
    """
    uri = [USER_GROUPS_SUB_PATH, user_id]
    return _call_account_api("get", uri, {}, **options)


def access_keys(sub_account_id, page_size=None, page=None, sort_by=None, sort_order=None, **options):
    """
    Get sub account access keys.

    :param sub_account_id:  The id of the sub account.
    :type sub_account_id:   str
    :param page_size:       How many entries to display on each page.
    :type page_size:        int
    :param page:            Which page to return (maximum pages: 100). **Default**: All pages are returned.
    :type page:             int
    :param sort_by:         Which response parameter to sort by.
                                **Possible values**: `api_key`, `created_at`, `name`, `enabled`.
    :type sort_by:          str
    :param sort_order:      Control the order of returned keys. **Possible values**: `desc` (default), `asc`.
    :type sort_order:       str
    :param options:         Generic advanced options dict, see online documentation.
    :type options:          dict, optional
    :return:                List of access keys
    :rtype:                 dict
    """
    uri = [SUB_ACCOUNTS_SUB_PATH, sub_account_id, ACCESS_KEYS]
    params = {
        "page_size": page_size,
        "page": page,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }
    return _call_account_api("get", uri, params, **options)


def generate_access_key(sub_account_id, name=None, enabled=None, **options):
    """
    Generate a new access key.

    :param sub_account_id:      The id of the sub account.
    :type sub_account_id:       str
    :param name:                The name of the new access key.
    :type name:                 str
    :param enabled:             Whether the new access key is enabled or disabled.
    :type enabled:              bool
    :param options:             Generic advanced options dict, see online documentation.
    :type options:              dict, optional
    :return:                    Access key details
    :rtype:                     dict
    """
    uri = [SUB_ACCOUNTS_SUB_PATH, sub_account_id, ACCESS_KEYS]
    params = {
        "name": name,
        "enabled": enabled,
    }
    return _call_account_api("post", uri, params, **options)


def update_access_key(sub_account_id, api_key, name=None, enabled=None, dedicated_for=None, **options):
    """
    Update the name and/or status of an existing access key.

    :param sub_account_id:      The id of the sub account.
    :type sub_account_id:       str
    :param api_key:             The API key of the access key.
    :type api_key:              str|int
    :param name:                The updated name of the access key.
    :type name:                 str
    :param enabled:             Enable or disable the access key.
    :type enabled:              bool
    :param dedicated_for:       Designates the access key for a specific purpose while allowing it to be used for
                                other purposes, as well. This action replaces any previously assigned key.
                                **Possible values**: `webhooks`
    :type dedicated_for:        str
    :param options:             Generic advanced options dict, see online documentation.
    :type options:              dict, optional
    :return:                    Access key details
    :rtype:                     dict
    """
    uri = [SUB_ACCOUNTS_SUB_PATH, sub_account_id, ACCESS_KEYS, str(api_key)]
    params = {
        "name": name,
        "enabled": enabled,
        "dedicated_for": dedicated_for,
    }
    return _call_account_api("put", uri, params, **options)


def delete_access_key(sub_account_id, api_key=None, name=None, **options):
    """
    Delete an existing access key by api_key or by name.

    :param sub_account_id:      The id of the sub account.
    :type sub_account_id:       str
    :param api_key:             The API key of the access key.
    :type api_key:              str|int
    :param name:                The name of the access key.
    :type name:                 str
    :param options:             Generic advanced options dict, see online documentation.
    :type options:              dict, optional
    :return:                    Operation status.
    :rtype:                     dict
    """
    uri = [SUB_ACCOUNTS_SUB_PATH, sub_account_id, ACCESS_KEYS]

    if api_key is not None:
        uri.append(str(api_key))

    params = {
        "name": name
    }
    return _call_account_api("delete", uri, params, **options)
