import hashlib

from common.hashing import sha256_of_bytes, sha256_of_file


def test_sha256_of_bytes_matches_stdlib():
    data = b"hello wrc"
    assert sha256_of_bytes(data) == hashlib.sha256(data).hexdigest()


def test_sha256_of_bytes_is_deterministic():
    data = b"same content"
    assert sha256_of_bytes(data) == sha256_of_bytes(data)


def test_sha256_of_bytes_differs_on_change():
    assert sha256_of_bytes(b"a") != sha256_of_bytes(b"b")


def test_sha256_of_file(tmp_path):
    path = tmp_path / "doc.html"
    path.write_bytes(b"<html>content</html>")
    assert sha256_of_file(path) == sha256_of_bytes(b"<html>content</html>")