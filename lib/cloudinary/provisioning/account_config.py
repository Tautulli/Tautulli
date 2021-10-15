from __future__ import absolute_import

import os

from cloudinary import BaseConfig, import_django_settings

ACCOUNT_URI_SCHEME = "account"


class AccountConfig(BaseConfig):
    def __init__(self):
        self._uri_scheme = ACCOUNT_URI_SCHEME

        super(AccountConfig, self).__init__()

    def _config_from_parsed_url(self, parsed_url):
        if not self._is_url_scheme_valid(parsed_url):
            raise ValueError("Invalid CLOUDINARY_ACCOUNT_URL scheme. URL should begin with 'account://'")

        return {
            "account_id": parsed_url.hostname,
            "provisioning_api_key": parsed_url.username,
            "provisioning_api_secret": parsed_url.password,
        }

    def _load_config_from_env(self):
        if os.environ.get("CLOUDINARY_ACCOUNT_URL"):
            self._load_from_url(os.environ.get("CLOUDINARY_ACCOUNT_URL"))


def account_config(**keywords):
    global _account_config
    _account_config.update(**keywords)
    return _account_config


def reset_config():
    global _account_config
    _account_config = AccountConfig()


_account_config = AccountConfig()
