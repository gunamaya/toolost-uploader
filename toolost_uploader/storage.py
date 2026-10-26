"""Storage lokal POSIX; tidak membuka browser atau membuktikan identitas akun."""

from contextlib import contextmanager
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

from .validation import InvalidInput, nonfinite, unique_keys, validate_manifest, validate_manifest_structure


MAX_RECORD_BYTES = 2 * 1024 * 1024
ALIAS = re.compile(r"[A-Za-z0-9_-]{1,64}")
RELEASE_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")


class StorageError(Exception):
    """Kode lokal stabil; pesan tidak berisi path atau nilai input."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _require(condition, code="invalid_record"):
    if not condition:
        raise StorageError(code)


def _identifier(value, pattern):
    _require(isinstance(value, str) and pattern.fullmatch(value), "invalid_identifier")


def default_root():
    if sys.platform == "darwin":
        return Path.home().resolve() / "Library/Application Support/toolost-uploader"
    if sys.platform.startswith("linux"):
        base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home().resolve() / ".local/state")))
        _require(base.is_absolute(), "unsafe_storage_path")
        return base / "toolost-uploader"
    raise StorageError("unsupported_platform")


def _private(info, directory=False):
    expected = 0o700 if directory else 0o600
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    _require(kind(info.st_mode) and info.st_uid == os.geteuid()
             and stat.S_IMODE(info.st_mode) == expected, "unsafe_permissions")
    if not directory:
        _require(info.st_nlink == 1, "unsafe_links")


def _directory(parent, name):
    try:
        os.mkdir(name, 0o700, dir_fd=parent)
    except FileExistsError:
        pass
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    try:
        _private(os.fstat(fd), directory=True)
    except BaseException:
        os.close(fd)
        raise
    return fd


def _root(path):
    _require(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "unsupported_platform")
    path = Path(path)
    _require(path.is_absolute() and ".." not in path.parts, "unsafe_storage_path")
    _require(len(path.parts) > 1, "unsafe_storage_path")
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for index, part in enumerate(path.parts[1:], 1):
            # Parent sistem boleh shared; subtree aplikasi harus dimiliki user dan privat.
            try:
                os.mkdir(part, 0o700, dir_fd=fd)
            except FileExistsError:
                pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            if index == len(path.parts) - 1:
                _private(os.fstat(fd), directory=True)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _encode(value):
    try:
        data = json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, RecursionError):
        raise StorageError("invalid_record") from None
    _require(len(data) <= MAX_RECORD_BYTES, "record_too_large")
    return data


def _digest(value):
    return hashlib.sha256(_encode(value)).hexdigest()


def _read(directory, name):
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    except FileNotFoundError:
        raise
    except OSError:
        raise StorageError("unsafe_or_unavailable_storage") from None
    try:
        _private(os.fstat(fd))
    except BaseException:
        os.close(fd)
        raise
    try:
        with os.fdopen(fd, "rb") as stream:
            data = stream.read(MAX_RECORD_BYTES + 1)
    except OSError:
        raise StorageError("unsafe_or_unavailable_storage") from None
    _require(len(data) <= MAX_RECORD_BYTES, "record_too_large")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=unique_keys, parse_constant=nonfinite)
    except (UnicodeError, ValueError, RecursionError):
        raise StorageError("corrupt_record") from None


def _atomic_write(directory, name, value):
    data = _encode(value)
    temporary = ".pending-" + uuid.uuid4().hex
    replaced = False
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory)
        with os.fdopen(fd, "wb") as stream:
            _private(os.fstat(stream.fileno()))
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
        replaced = True
        os.fsync(directory)
    except OSError:
        # Sesudah rename, file baru mungkin sudah terpasang walau durability belum pasti.
        raise StorageError("write_outcome_unknown" if replaced else "write_failed") from None
    finally:
        if not replaced:
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass


@contextmanager
def profile(alias, *, root=None):
    """Buka profil offline dengan exclusive lock; root eksplisit hanya untuk tes/embedding."""
    _identifier(alias, ALIAS)
    _require(os.name == "posix" and hasattr(os, "O_NOFOLLOW"), "unsupported_platform")
    descriptors = []
    session = None
    try:
        import fcntl

        root_fd = _root(default_root() if root is None else root)
        descriptors.append(root_fd)
        profiles_fd = _directory(root_fd, "profiles")
        descriptors.append(profiles_fd)
        profile_fd = _directory(profiles_fd, alias)
        descriptors.append(profile_fd)
        lock_fd = os.open("writer.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                          0o600, dir_fd=profile_fd)
        descriptors.append(lock_fd)
        _private(os.fstat(lock_fd))
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            if error.errno in (errno.EACCES, errno.EAGAIN):
                raise StorageError("profile_locked") from None
            raise
        config = {"storage_version": 1, "profile": alias, "account_fingerprint": None}
        try:
            actual = _read(profile_fd, "profile.json")
        except FileNotFoundError:
            _atomic_write(profile_fd, "profile.json", config)
        else:
            _require(actual == config and type(actual.get("storage_version")) is int, "profile_mismatch")
        checkpoints_fd = _directory(profile_fd, "checkpoints")
        descriptors.append(checkpoints_fd)
        session = Profile(alias, checkpoints_fd)
        yield session
    except OSError:
        if session is not None:
            raise
        raise StorageError("unsafe_or_unavailable_storage") from None
    finally:
        if session is not None:
            session.closed = True
        # Jangan unlink lock: proses lain mungkin sudah memegang inode yang sama.
        for fd in reversed(descriptors):
            os.close(fd)


class Profile:
    def __init__(self, alias, directory):
        self.alias = alias
        self.directory = directory
        self.closed = False

    def _check(self, release_id):
        _require(not self.closed, "profile_closed")
        _identifier(release_id, RELEASE_ID)
        return release_id + ".json"

    def create_checkpoint(self, manifest, manifest_dir):
        """Validasi aset saat create; simpan snapshot terpisah dari dict milik pemanggil."""
        _require(not self.closed, "profile_closed")
        try:
            manifest = json.loads(_encode(manifest))
            base = Path(manifest_dir)
            _require(base.is_absolute() and ".." not in base.parts, "invalid_manifest_directory")
            validate_manifest(manifest, base)
        except (InvalidInput, OSError, ValueError):
            raise StorageError("invalid_manifest") from None
        name = self._check(manifest["release_id"])
        try:
            _read(self.directory, name)
        except FileNotFoundError:
            pass
        else:
            raise StorageError("checkpoint_exists")
        record = dict(storage_version=1, run_id=uuid.uuid4().hex, revision=1,
                      profile=self.alias, release_id=manifest["release_id"],
                      manifest=manifest, manifest_dir=str(base), manifest_sha256=_digest(manifest),
                      account_fingerprint=None, remote_draft_id=None, state="validated")
        record["record_sha256"] = _digest(record)
        _atomic_write(self.directory, name, record)
        return record

    def read_checkpoint(self, release_id):
        name = self._check(release_id)
        try:
            record = _read(self.directory, name)
        except FileNotFoundError:
            raise StorageError("checkpoint_not_found") from None
        keys = {"storage_version", "run_id", "revision", "profile", "release_id", "manifest",
                "manifest_dir", "manifest_sha256", "account_fingerprint", "remote_draft_id",
                "state", "record_sha256"}
        _require(isinstance(record, dict) and set(record) == keys)
        _require(type(record["storage_version"]) is int and record["storage_version"] == 1)
        _require(type(record["revision"]) is int and record["revision"] >= 1)
        _require(isinstance(record["run_id"], str) and re.fullmatch(r"[0-9a-f]{32}", record["run_id"]))
        _require(record["profile"] == self.alias and record["release_id"] == release_id, "checkpoint_mismatch")
        _require(record["account_fingerprint"] is None and record["remote_draft_id"] is None)
        _require(record["state"] in ("validated", "cancelled"))
        _require(isinstance(record["manifest_dir"], str) and Path(record["manifest_dir"]).is_absolute()
                 and ".." not in Path(record["manifest_dir"]).parts)
        try:
            validate_manifest_structure(record["manifest"])
        except (InvalidInput, TypeError, ValueError):
            raise StorageError("invalid_record") from None
        _require(record["manifest"]["release_id"] == release_id, "checkpoint_mismatch")
        _require(record["manifest_sha256"] == _digest(record["manifest"]), "manifest_hash_mismatch")
        content = {key: value for key, value in record.items() if key != "record_sha256"}
        _require(record["record_sha256"] == _digest(content), "record_hash_mismatch")
        return record

    def cancel_checkpoint(self, release_id, *, run_id, expected_revision):
        """Satu transisi lokal saja; tidak menerima status remote atau arbitrary payload."""
        record = self.read_checkpoint(release_id)
        _require(record["run_id"] == run_id, "run_mismatch")
        _require(type(expected_revision) is int and record["revision"] == expected_revision, "revision_conflict")
        _require(record["state"] == "validated", "invalid_transition")
        record.update(state="cancelled", revision=record["revision"] + 1)
        record["record_sha256"] = _digest({key: value for key, value in record.items() if key != "record_sha256"})
        _atomic_write(self.directory, self._check(release_id), record)
        return record

    def update_checkpoint(self, manifest, manifest_dir, *, expected_revision):
        """Update snapshot manifest untuk update metadata atau append track ke draft existing; menaikkan revision."""
        _require(not self.closed, "profile_closed")
        try:
            manifest = json.loads(_encode(manifest))
            base = Path(manifest_dir)
            _require(base.is_absolute() and ".." not in base.parts, "invalid_manifest_directory")
            validate_manifest(manifest, base)
        except (InvalidInput, OSError, ValueError):
            raise StorageError("invalid_manifest") from None
        name = self._check(manifest["release_id"])
        record = self.read_checkpoint(manifest["release_id"])
        _require(type(expected_revision) is int and record["revision"] == expected_revision, "revision_conflict")
        _require(record["state"] == "validated", "invalid_transition")

        old_manifest = record["manifest"]
        _require(old_manifest.get("release_type") == "album" and manifest.get("release_type") == "album", "update_requires_album")
        old_tracks = old_manifest.get("tracks", [])
        new_tracks = manifest.get("tracks", [])

        # Semua audio track lama harus tetap dipertahankan (tidak boleh menghapus lagu)
        old_audio_hashes = {t.get("audio", {}).get("sha256") for t in old_tracks}
        new_audio_hashes = {t.get("audio", {}).get("sha256") for t in new_tracks}
        _require(old_audio_hashes.issubset(new_audio_hashes), "update_cannot_remove_tracks")

        # Harus ada perbedaan nyata (title, release_date, artwork, track metadata/urutan)
        _require(manifest != old_manifest, "checkpoint_already_up_to_date")

        record.update(
            revision=record["revision"] + 1,
            manifest=manifest,
            manifest_dir=str(base),
            manifest_sha256=_digest(manifest),
        )
        record["record_sha256"] = _digest({key: value for key, value in record.items() if key != "record_sha256"})
        _atomic_write(self.directory, name, record)
        return record
