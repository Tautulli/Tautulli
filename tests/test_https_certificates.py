import ipaddress
import sys
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID

import plexpy
from plexpy import common, helpers


def _create(monkeypatch, tmp_path, domains, ips):
    monkeypatch.setattr(plexpy, "CONFIG", SimpleNamespace(HTTPS_DOMAIN=domains, HTTPS_IP=ips))
    cert_path, key_path = tmp_path / "server.crt", tmp_path / "server.key"
    ok = helpers.create_https_certificates(str(cert_path), str(key_path))
    return ok, cert_path, key_path


def test_self_signed_certificate(monkeypatch, tmp_path):
    ok, cert_path, key_path = _create(monkeypatch, tmp_path, "localhost, example.com", "127.0.0.1, ::1")
    assert ok is True

    cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)

    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert san.get_values_for_type(x509.DNSName) == ["localhost", "example.com"]
    assert san.get_values_for_type(x509.IPAddress) == [
        ipaddress.ip_address("127.0.0.1"), ipaddress.ip_address("::1")]

    assert cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value == common.PRODUCT
    assert cert.issuer == cert.subject
    assert cert.public_key().public_numbers() == key.public_key().public_numbers()
    assert key.key_size == 2048
    assert key.public_key().public_numbers().e == 65537
    assert key_path.read_bytes().startswith(b"-----BEGIN PRIVATE KEY-----")
    assert abs(cert.serial_number - int(time.time())) < 60
    assert isinstance(cert.signature_hash_algorithm, hashes.SHA256)

    lifetime = cert.not_valid_after_utc - cert.not_valid_before_utc
    assert lifetime == timedelta(days=3650)
    assert abs(datetime.now(timezone.utc) - cert.not_valid_before_utc) < timedelta(minutes=1)


def test_no_names_gives_no_san(monkeypatch, tmp_path):
    ok, cert_path, _ = _create(monkeypatch, tmp_path, "", "")
    assert ok is True
    cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    assert len(cert.extensions) == 0


def test_unwritable_path_returns_false(monkeypatch, tmp_path):
    monkeypatch.setattr(plexpy, "CONFIG", SimpleNamespace(HTTPS_DOMAIN="localhost", HTTPS_IP=""))
    assert helpers.create_https_certificates(str(tmp_path / "no" / "c.crt"), str(tmp_path / "k")) is False


def test_missing_cryptography_returns_false(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "cryptography", None)
    ok, cert_path, _ = _create(monkeypatch, tmp_path, "localhost", "127.0.0.1")
    assert ok is False
    assert not cert_path.exists()
