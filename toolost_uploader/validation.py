"""Validasi offline manifest; bukan executor upload atau validator JSON Schema umum."""

import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat


MAX_MANIFEST_BYTES = 1024 * 1024
MAX_TRACKS = 1000
MAX_LYRICS_BYTES = 1024 * 1024
ID = re.compile(r"[A-Za-z0-9_-]{1,128}")
SHA256 = re.compile(r"[0-9a-f]{64}")
RELEASE_TEXT = {"language", "primary_genre", "secondary_genre", "label", "upc"}
TRACK_TEXT = {"version_line", "language", "isrc", "iswc"}
TRACK_BOOL = {"ai_assisted", "provenance_known_ai_generated", "instrumental", "explicit", "clean_version"}


class InvalidInput(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def reject(code, message):
    raise InvalidInput(code, message)


def object_keys(value, required, optional=()):
    if not isinstance(value, dict):
        reject("invalid_type", "Objek JSON diperlukan.")
    if set(value) - set(required) - set(optional):
        reject("unknown_field", "Field asing atau capability yang belum didukung ditemukan.")
    if set(required) - set(value):
        reject("missing_field", "Field wajib belum lengkap, termasuk deklarasi AI per track.")


def text(value):
    if not isinstance(value, str) or not value.strip() or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        reject("invalid_text", "String UTF-8 nonblank diperlukan.")


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        reject("invalid_id", "ID harus 1-128 karakter ASCII huruf, angka, underscore atau hyphen.")


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            reject("duplicate_key", "Duplicate JSON key ditolak.")
        result[key] = value
    return result


def nonfinite(_):
    reject("invalid_json", "Konstanta non-JSON ditolak.")


def load_manifest(path):
    with path.open("rb") as stream:
        raw = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        reject("manifest_too_large", "Manifest melebihi batas lokal 1 MiB.")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_keys, parse_constant=nonfinite)


def file_reference_structure(reference):
    object_keys(reference, {"path", "sha256"})
    text(reference["path"])
    if "\x00" in reference["path"]:
        reject("invalid_path", "Path mengandung karakter yang tidak diizinkan.")
    if not isinstance(reference["sha256"], str) or not SHA256.fullmatch(reference["sha256"]):
        reject("invalid_hash", "SHA-256 harus 64 karakter lowercase hex.")


def file_reference(reference, base, lyrics=False):
    file_reference_structure(reference)
    path = Path(reference["path"])
    if not path.is_absolute():
        path = base / path
    # Tidak mengikuti symlink di komponen mana pun; bukan snapshot untuk upload nanti.
    path = Path(os.path.abspath(path))
    for component in (path, *path.parents):
        if component.is_symlink():
            reject("symlink_not_supported", "Symlink pada referensi aset belum didukung.")
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        reject("invalid_file", "Referensi harus file reguler yang dapat dibaca.")
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            reject("invalid_file", "Referensi harus file reguler yang dapat dibaca.")
        if before.st_size == 0:
            reject("empty_file", "File kosong tidak didukung.")
        if lyrics and before.st_size > MAX_LYRICS_BYTES:
            reject("lyrics_too_large", "Lirik melebihi batas lokal 1 MiB.")
        digest = hashlib.sha256()
        content = bytearray() if lyrics else None
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            if lyrics:
                content.extend(chunk)
                if len(content) > MAX_LYRICS_BYTES:
                    reject("lyrics_too_large", "Lirik melebihi batas lokal 1 MiB.")
        after = os.fstat(stream.fileno())
    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        reject("file_changed", "File berubah saat validasi; pilih ulang aset final.")
    if digest.hexdigest() != reference["sha256"]:
        reject("hash_mismatch", "Hash aset tidak cocok dengan manifest.")
    if lyrics:
        try:
            content.decode("utf-8")
        except UnicodeError:
            reject("invalid_lyrics_encoding", "File lirik harus UTF-8.")


def validate_manifest_structure(manifest):
    required = {"schema_version", "release_id", "release_type", "title", "release_date", "artwork", "tracks"}
    object_keys(manifest, required, RELEASE_TEXT | {"copyright"})
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        reject("unsupported_schema", "schema_version harus integer 1.")
    identifier(manifest["release_id"])
    if manifest["release_type"] not in ("album", "ep", "single", "compilation"):
        reject("invalid_release_type", "release_type tidak didukung.")
    text(manifest["title"])
    date = manifest["release_date"]
    if not isinstance(date, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", date):
        reject("invalid_date", "release_date harus tanggal YYYY-MM-DD yang valid.")
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        reject("invalid_date", "release_date harus tanggal YYYY-MM-DD yang valid.")
    for field in RELEASE_TEXT & manifest.keys():
        text(manifest[field])
    if "copyright" in manifest:
        rights = manifest["copyright"]
        object_keys(rights, set(), {"c_year", "p_year", "c_owner", "p_owner"})
        if not rights:
            reject("invalid_copyright", "Copyright kosong bukan perintah clear.")
        for field, value in rights.items():
            if field.endswith("year"):
                if type(value) is not int or not 1 <= value <= 9999:
                    reject("invalid_year", "Tahun copyright harus integer 1-9999.")
            else:
                text(value)
    tracks = manifest["tracks"]
    if not isinstance(tracks, list) or not 1 <= len(tracks) <= MAX_TRACKS:
        reject("invalid_tracks", "Jumlah track harus 1-1000 (batas lokal, bukan aturan DSP).")
    seen = set()
    warnings = ["Validasi offline saja; bukan bukti format media, hak, QC/DSP atau kesiapan distribusi."]
    references = [(manifest["artwork"], False)]
    for track in tracks:
        object_keys(track, {"track_id", "title", "audio", "ai_assisted"}, TRACK_TEXT | TRACK_BOOL | {"lyrics"})
        identifier(track["track_id"])
        if track["track_id"] in seen:
            reject("duplicate_track_id", "ID track harus unik dalam rilis.")
        seen.add(track["track_id"])
        text(track["title"])
        for field in TRACK_TEXT & track.keys():
            text(track[field])
        for field in TRACK_BOOL & track.keys():
            if type(track[field]) is not bool:
                reject("invalid_boolean", "Deklarasi track harus boolean eksplisit, bukan null/angka/string.")
        if track.get("provenance_known_ai_generated") and not track["ai_assisted"]:
            warnings.append("Konflik provenance AI dan ai_assisted; review manusia diperlukan.")
        references.append((track["audio"], False))
        if "lyrics" in track:
            references.append((track["lyrics"], True))
    for reference, lyrics in references:
        file_reference_structure(reference)
    return warnings


def validate_manifest(manifest, base):
    warnings = validate_manifest_structure(manifest)
    file_reference(manifest["artwork"], base)
    for track in manifest["tracks"]:
        file_reference(track["audio"], base)
        if "lyrics" in track:
            file_reference(track["lyrics"], base, lyrics=True)
    return warnings


def validate_result(result):
    """Periksa envelope validate saja; hasil operasi akun belum didukung."""
    object_keys(result, {"schema_version", "command", "run_id", "status", "profile",
                         "release_id", "draft_id", "remote_verified", "issues", "warnings", "error"})
    if type(result["schema_version"]) is not int or result["schema_version"] != 1:
        reject("invalid_result", "Versi hasil tidak didukung.")
    if result["command"] != "validate" or result["status"] not in ("valid", "invalid_input"):
        reject("invalid_result", "Hanya hasil validate offline didukung.")
    if any(result[key] is not None for key in ("run_id", "profile", "draft_id")) or result["remote_verified"] is not False:
        reject("invalid_result", "Hasil offline tidak boleh mengklaim state akun.")
    if result["release_id"] is not None:
        identifier(result["release_id"])
    for key in ("issues", "warnings"):
        if not isinstance(result[key], list):
            reject("invalid_result", "Daftar issues/warnings diperlukan.")
    for warning in result["warnings"]:
        text(warning)
    for issue in result["issues"]:
        object_keys(issue, {"code", "scope", "message"})
        for value in issue.values():
            text(value)
    if result["status"] == "valid":
        if result["error"] is not None or result["issues"] or result["release_id"] is None:
            reject("invalid_result", "Hasil valid harus tanpa error/issues dan memiliki release_id.")
    else:
        error = result["error"]
        object_keys(error, {"code", "message", "retryable"})
        text(error["code"])
        text(error["message"])
        if error["retryable"] is not False or not result["issues"]:
            reject("invalid_result", "Hasil invalid memerlukan issue dan retryable false.")


def validate(path):
    result = dict(schema_version=1, command="validate", run_id=None, status="invalid_input",
                  profile=None, release_id=None, draft_id=None, remote_verified=False,
                  issues=[], warnings=[], error=None)
    try:
        path = Path(path).absolute()
        manifest = load_manifest(path)
        result["warnings"] = validate_manifest(manifest, path.parent)
        result["release_id"] = manifest["release_id"]
        result["status"] = "valid"
    except InvalidInput as error:
        result["error"] = dict(code=error.code, message=str(error), retryable=False)
    except (OSError, ValueError, UnicodeError, RecursionError, OverflowError):
        result["error"] = dict(code="unreadable_input", message="JSON UTF-8 atau file referensi tidak valid/tidak dapat diakses.", retryable=False)
    if result["error"]:
        error = result["error"]
        result["issues"] = [dict(code=error["code"], scope="release", message=error["message"])]
    return result
