"""XDG environment variable mixin for Unix and macOS."""

from __future__ import annotations

import os

from .api import PlatformDirsABC


class XDGMixin(PlatformDirsABC):
    """Mixin that checks XDG environment variables, falling back to platform-specific defaults via ``super()``."""

    @property
    def user_data_dir(self) -> str:
        """Data directory tied to the user, from ``$XDG_DATA_HOME`` if set, else platform default."""
        if path := os.environ.get("XDG_DATA_HOME", "").strip():
            return self._append_app_name_and_version(path)
        return super().user_data_dir

    @property
    def _site_data_dirs(self) -> list[str]:
        if xdg_dirs := _xdg_dir_list("XDG_DATA_DIRS"):
            return [self._append_app_name_and_version(p) for p in xdg_dirs]
        return super()._site_data_dirs

    @property
    def site_data_dir(self) -> str:
        """Data directories shared by users, from ``$XDG_DATA_DIRS`` if set, else platform default."""
        dirs = self._site_data_dirs
        return os.pathsep.join(dirs) if self.multipath else dirs[0]

    @property
    def user_config_dir(self) -> str:
        """Config directory tied to the user, from ``$XDG_CONFIG_HOME`` if set, else platform default."""
        if path := os.environ.get("XDG_CONFIG_HOME", "").strip():
            return self._append_app_name_and_version(path)
        return super().user_config_dir

    @property
    def _site_config_dirs(self) -> list[str]:
        if xdg_dirs := _xdg_dir_list("XDG_CONFIG_DIRS"):
            return [self._append_app_name_and_version(p) for p in xdg_dirs]
        return super()._site_config_dirs

    @property
    def site_config_dir(self) -> str:
        """Config directories shared by users, from ``$XDG_CONFIG_DIRS`` if set, else platform default."""
        dirs = self._site_config_dirs
        return os.pathsep.join(dirs) if self.multipath else dirs[0]

    @property
    def user_cache_dir(self) -> str:
        """Cache directory tied to the user, from ``$XDG_CACHE_HOME`` if set, else platform default."""
        if path := os.environ.get("XDG_CACHE_HOME", "").strip():
            return self._append_app_name_and_version(path)
        return super().user_cache_dir

    @property
    def user_state_dir(self) -> str:
        """State directory tied to the user, from ``$XDG_STATE_HOME`` if set, else platform default."""
        if path := os.environ.get("XDG_STATE_HOME", "").strip():
            return self._append_app_name_and_version(path)
        return super().user_state_dir

    @property
    def user_runtime_dir(self) -> str:
        """Runtime directory tied to the user, from ``$XDG_RUNTIME_DIR`` if set, else platform default."""
        if path := os.environ.get("XDG_RUNTIME_DIR", "").strip():
            return self._append_app_name_and_version(path)
        return super().user_runtime_dir

    @property
    def site_runtime_dir(self) -> str:
        """Runtime directory shared by users, from ``$XDG_RUNTIME_DIR`` if set, else platform default."""
        if path := os.environ.get("XDG_RUNTIME_DIR", "").strip():
            return self._append_app_name_and_version(path)
        return super().site_runtime_dir

    @property
    def user_documents_dir(self) -> str:
        """Documents directory tied to the user, from ``$XDG_DOCUMENTS_DIR`` if set, else platform default."""
        if path := os.environ.get("XDG_DOCUMENTS_DIR", "").strip():
            return os.path.expanduser(path)  # ruff:ignore[os-path-expanduser]
        return super().user_documents_dir

    @property
    def user_downloads_dir(self) -> str:
        """Downloads directory tied to the user, from ``$XDG_DOWNLOAD_DIR`` if set, else platform default."""
        if path := os.environ.get("XDG_DOWNLOAD_DIR", "").strip():
            return os.path.expanduser(path)  # ruff:ignore[os-path-expanduser]
        return super().user_downloads_dir

    @property
    def user_pictures_dir(self) -> str:
        """Pictures directory tied to the user, from ``$XDG_PICTURES_DIR`` if set, else platform default."""
        if path := os.environ.get("XDG_PICTURES_DIR", "").strip():
            return os.path.expanduser(path)  # ruff:ignore[os-path-expanduser]
        return super().user_pictures_dir

    @property
    def user_videos_dir(self) -> str:
        """Videos directory tied to the user, from ``$XDG_VIDEOS_DIR`` if set, else platform default."""
        if path := os.environ.get("XDG_VIDEOS_DIR", "").strip():
            return os.path.expanduser(path)  # ruff:ignore[os-path-expanduser]
        return super().user_videos_dir

    @property
    def user_music_dir(self) -> str:
        """Music directory tied to the user, from ``$XDG_MUSIC_DIR`` if set, else platform default."""
        if path := os.environ.get("XDG_MUSIC_DIR", "").strip():
            return os.path.expanduser(path)  # ruff:ignore[os-path-expanduser]
        return super().user_music_dir

    @property
    def user_desktop_dir(self) -> str:
        """Desktop directory tied to the user, from ``$XDG_DESKTOP_DIR`` if set, else platform default."""
        if path := os.environ.get("XDG_DESKTOP_DIR", "").strip():
            return os.path.expanduser(path)  # ruff:ignore[os-path-expanduser]
        return super().user_desktop_dir

    @property
    def user_projects_dir(self) -> str:
        """Projects directory tied to the user, from ``$XDG_PROJECTS_DIR`` if set, else platform default."""
        if path := os.environ.get("XDG_PROJECTS_DIR", "").strip():
            return os.path.expanduser(path)  # ruff:ignore[os-path-expanduser]  # API returns str, not Path
        return super().user_projects_dir

    @property
    def user_publicshare_dir(self) -> str:
        """Public share directory tied to the user, from ``$XDG_PUBLICSHARE_DIR`` if set, else platform default."""
        if path := os.environ.get("XDG_PUBLICSHARE_DIR", "").strip():
            return os.path.expanduser(path)  # ruff:ignore[os-path-expanduser]  # API returns str, not Path
        return super().user_publicshare_dir

    @property
    def user_templates_dir(self) -> str:
        """Templates directory tied to the user, from ``$XDG_TEMPLATES_DIR`` if set, else platform default."""
        if path := os.environ.get("XDG_TEMPLATES_DIR", "").strip():
            return os.path.expanduser(path)  # ruff:ignore[os-path-expanduser]  # API returns str, not Path
        return super().user_templates_dir

    @property
    def user_fonts_dir(self) -> str:
        """Fonts directory tied to the user, from ``$XDG_DATA_HOME/fonts`` if set, else platform default."""
        if path := os.environ.get("XDG_DATA_HOME", "").strip():
            return f"{os.path.expanduser(path)}/fonts"  # ruff:ignore[os-path-expanduser]  # API returns str, not Path
        return super().user_fonts_dir

    @property
    def user_applications_dir(self) -> str:
        """Applications directory tied to the user, from ``$XDG_DATA_HOME`` if set, else platform default."""
        if path := os.environ.get("XDG_DATA_HOME", "").strip():
            return os.path.join(os.path.expanduser(path), "applications")  # ruff:ignore[os-path-expanduser, os-path-join]
        return super().user_applications_dir

    @property
    def _site_applications_dirs(self) -> list[str]:
        if xdg_dirs := _xdg_dir_list("XDG_DATA_DIRS"):
            return [os.path.join(p, "applications") for p in xdg_dirs]  # ruff:ignore[os-path-join]
        return super()._site_applications_dirs

    @property
    def site_applications_dir(self) -> str:
        """Applications directories shared by users, from ``$XDG_DATA_DIRS`` if set, else platform default."""
        dirs = self._site_applications_dirs
        return os.pathsep.join(dirs) if self.multipath else dirs[0]


def _xdg_dir_list(env_var: str) -> list[str]:
    """Stripped non-blank entries of ``env_var``, so a value of only separators and whitespace falls back like unset."""
    return [stripped for path in os.environ.get(env_var, "").split(os.pathsep) if (stripped := path.strip())]


__all__ = [
    "XDGMixin",
]
