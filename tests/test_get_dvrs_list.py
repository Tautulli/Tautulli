from unittest.mock import patch

from plexpy import pmsconnect


def test_get_dvrs_list_returns_empty_when_pms_is_unreachable(app_config):
    with patch.object(pmsconnect.PmsConnect, "get_dvrs", return_value=None):
        assert pmsconnect.PmsConnect().get_dvrs_list() == []
