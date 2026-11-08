"""The image proxy swaps a whole image into its cache.

A request serving a cached image reads the file size for Content-Length,
then reads the bytes. A file written in place could grow in between.
"""

import errno
import os
import threading
from pathlib import Path

import pytest

from plexpy import pmsconnect
from plexpy import webserve

INFO_PAGE = Path(__file__).resolve().parent.parent / "data/interfaces/default/info.html"
OLD = b"old image"
NEW = b"new image, longer than the old one"


@pytest.fixture
def cache(app_config, tmp_path, monkeypatch):
    app_config.CACHE_DIR = str(tmp_path)
    app_config.CACHE_IMAGES = 1
    monkeypatch.setattr(pmsconnect.PmsConnect, "get_image", lambda self, **kwargs: (NEW, "image/png"))
    return tmp_path / "images"


def fetch():
    # refresh skips the cached file and fetches the image again
    return webserve.WebInterface().real_pms_image_proxy(img="/library/metadata/1/thumb/2", refresh=True)


def cached_file(cache):
    fetch()
    (path,) = cache.iterdir()
    path.write_bytes(OLD)
    return path


def test_cached_image_stays_whole_while_the_new_one_is_written(cache, monkeypatch):
    path = cached_file(cache)
    real_open = webserve.open
    seen = []

    def spying_open(file, mode="r", *args, **kwargs):
        f = real_open(file, mode, *args, **kwargs)
        if "w" in mode:
            seen.append(path.read_bytes())
        return f

    monkeypatch.setattr(webserve, "open", spying_open)

    assert fetch() == NEW
    assert seen == [OLD]
    assert path.read_bytes() == NEW
    assert list(cache.iterdir()) == [path]


def test_concurrent_fetches_write_separate_temp_files(cache, monkeypatch):
    # Two requests for one uncached image must not write into one temp file.
    # The barrier holds both inside the fetch until both have arrived.
    barrier = threading.Barrier(2, timeout=10)

    def get_image(self, **kwargs):
        barrier.wait()
        return NEW, "image/png"

    monkeypatch.setattr(pmsconnect.PmsConnect, "get_image", get_image)
    real_open = webserve.open
    written = []

    def spying_open(file, mode="r", *args, **kwargs):
        if "w" in mode:
            written.append(file)
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(webserve, "open", spying_open)
    results = []
    threads = [threading.Thread(target=lambda: results.append(fetch())) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results == [NEW, NEW]
    assert len(set(written)) == 2
    # os.replace cannot move a file across filesystems
    assert {os.path.dirname(file) for file in written} == {str(cache)}
    (path,) = cache.iterdir()
    assert path.read_bytes() == NEW


@pytest.mark.parametrize("error", [PermissionError("in use"), OSError(errno.EIO, "I/O error")])
def test_a_failed_swap_still_returns_the_image(cache, monkeypatch, error):
    # Windows refuses to replace a file another request has open
    path = cached_file(cache)

    def locked(src, dst):
        raise error

    monkeypatch.setattr(os, "replace", locked)

    assert fetch() == NEW
    assert path.read_bytes() == OLD
    assert list(cache.iterdir()) == [path]


@pytest.mark.parametrize("img_format, content_type", [("jpg", "image/jpeg"), ("png", "image/png")])
def test_cached_image_is_served_with_its_content_type(cache, monkeypatch, img_format, content_type):
    served = []
    monkeypatch.setattr(webserve, "serve_file", lambda **kwargs: served.append(kwargs))

    webserve.WebInterface().real_pms_image_proxy(img="/library/metadata/1/thumb/2", img_format=img_format)

    (kwargs,) = served
    assert kwargs["path"].endswith("." + img_format)
    assert kwargs["content_type"] == content_type


def test_info_page_requests_the_background_art_as_jpg():
    lines = INFO_PAGE.read_text(encoding="utf-8").splitlines()
    (art,) = [line for line in lines if 'class="art-face"' in line]
    # The fallback gives Live TV items their art
    assert ("page('pms_image_proxy', data['art'], data['rating_key'], 1920, 1080, "
            "img_format='jpg', fallback=fallback)") in art


@pytest.fixture
def fetched(app_config, tmp_path, monkeypatch):
    app_config.CACHE_DIR = str(tmp_path)
    app_config.CACHE_IMAGES = 0
    calls = []

    def get_image(self, **kwargs):
        calls.append(kwargs["img"])
        return NEW, "image/png"

    monkeypatch.setattr(pmsconnect.PmsConnect, "get_image", get_image)
    return calls


@pytest.mark.parametrize("img", [
    "@otherhost/a/b/c",
    "/library/metadata/../..",
    "library/metadata/1/thumb/2",
    "/..",
    "/library/metadata/../x/thumb",
    "/library/metadata/1/thumb/..",
    "/library/sections/1/refresh",
    "/foo/library/metadata/1/thumb",
    "/library/metadata/%2e%2e/%2e%2e",
    "/library/metadata/%252e%252e/x",
    "/library/metadatax/1/thumb",
    "/playlistsx/1/composite/2",
    "/:/resourcesx/a.png",
    "/library/partsx/1/indexes",
])
def test_bad_image_path_is_not_fetched(fetched, img):
    assert webserve.WebInterface().real_pms_image_proxy(img=img) is None
    assert fetched == []


@pytest.mark.parametrize("img, sent", [
    # the proxy keeps only the first parts of a metadata path
    ("/library/metadata/1/thumb/2", "/library/metadata/1/thumb"),
    ("/:/resources/show-fallback.png", "/:/resources/show-fallback.png"),
    ("/:/resources/a..b.png", "/:/resources/a..b.png"),
    ("/library/collections/1/composite/2", "/library/collections/1/composite/2"),
    ("/library/parts/1/indexes/sd/1000", "/library/parts/1/indexes"),
    ("/playlists/1/composite/2", "/playlists/1/composite/2"),
])
def test_good_image_path_is_fetched(fetched, img, sent):
    assert webserve.WebInterface().real_pms_image_proxy(img=img) == NEW
    assert fetched == [sent]
