import importlib
import warnings

import distro
import pytest

import plexpy.common


OS_RELEASE = {
    'ubuntu': (
        'NAME="Ubuntu"\nVERSION="22.04.4 LTS (Jammy Jellyfish)"\n'
        'ID=ubuntu\nVERSION_ID="22.04"\nVERSION_CODENAME=jammy\n',
        'Ubuntu 22.04 Jammy Jellyfish',
    ),
    'kali': (
        'NAME="Kali GNU/Linux"\nVERSION="2024.2"\n'
        'ID=kali\nVERSION_ID="2024.2"\nVERSION_CODENAME=kali-rolling\n',
        'Kali GNU/Linux 2024.2 kali-rolling',
    ),
    'alpine': (
        'NAME="Alpine Linux"\nID=alpine\nVERSION_ID=3.20.3\n',
        'Alpine Linux 3.20.3',
    ),
}


@pytest.fixture
def reload_common():
    yield
    importlib.reload(plexpy.common)


@pytest.mark.parametrize('name', OS_RELEASE)
def test_linux_distro_string(name, tmp_path, monkeypatch, reload_common):
    contents, expected = OS_RELEASE[name]
    os_release = tmp_path / 'os-release'
    os_release.write_text(contents)
    fake = distro.LinuxDistribution(
        include_lsb=False, include_uname=False, include_oslevel=False,
        os_release_file=str(os_release), distro_release_file='/nonexistent',
    )
    monkeypatch.setattr(distro.distro, '_distro', fake)

    with warnings.catch_warnings():
        warnings.simplefilter('error', DeprecationWarning)
        importlib.reload(plexpy.common)

    assert plexpy.common.PLATFORM_LINUX_DISTRO == expected
