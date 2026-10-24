# Toolost uploader

Riset dan rancangan CLI Python + Playwright untuk mengelola draft release Too Lost, terpisah dari integrator yt-to-flowmusic. **CLI offline `toolost validate` tersedia; uploader/operasi akun belum tersedia.**

- [Indeks riset](docs/RESEARCH.md)
- [Prompt melanjutkan pengembangan](docs/CONTINUE-PROMPT.md)
- [Kontrak v1 untuk review](docs/CONTRACT-V1.md)
- [Kontrak release list/detail/publish](docs/RELEASE-CONTRACT.md) — publish masih capability future, tidak diuji atau dieksekusi selama riset.
- [Script browser riset](docs/BROWSER.md)
- [Validator offline dan cakupan schema](docs/OFFLINE-VALIDATION.md)
- [Profil privat dan checkpoint offline](docs/LOCAL-STATE.md) — helper internal POSIX, bukan command akun/login/resume.
- [Attempt journal dan rekonsiliasi fake offline](docs/OFFLINE-JOURNAL.md) — simulasi satu save, bukan executor akun.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/toolost validate path/to/manifest.json --json
```

Schema v1 masih unreleased. Package lokal `toolost-uploader` versi `0.1.0a0` membutuhkan Python ≥3.10; modul `toolost_uploader`, executable `toolost`. Classifier `Private :: Do Not Upload` menahan publikasi PyPI. Validator hanya membaca manifest dan aset, tidak membuka browser atau menjalankan upload/publish.

Scope riset maksimal upload dan simpan draft. Tidak ada izin/tindakan Publish atau distribusi. Produk final dapat mendukung release pada fase terpisah dengan persetujuan eksplisit.

Profil browser, capture akun dan aset riset disimpan lokal dalam `.local/` dan tidak boleh di-commit. Repo private bukan tempat penyimpanan cookie, kredensial atau media pengguna.

Contoh JSON pada docs hanya ilustrasi: hash nol dan path contoh bukan aset valid. Hanya command `validate` yang sudah diimplementasikan; command akun dalam kontrak masih proposal.

Tes offline harness dan validator (stdlib, tanpa login/network):

```sh
python3 -m unittest discover -s tests -v
```

Jangan publish paket PyPI sebelum diminta. Tidak ada lisensi redistribusi yang ditetapkan pada tahap ini.

Build/schema/install checks (dependency pengembangan, bukan runtime):

```sh
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m build
TOOLOST_TEST_DIST_DIR=dist .venv/bin/python -m unittest discover -s tests -v
```

`python3 -m toolost_uploader validate <manifest.json> --json` dan wrapper lama `scripts/validate.py` memakai validator yang sama. Uji instalasi opt-in membuat venv sementara, memasang wheel tanpa network/dependency, lalu menjalankan command di luar checkout. Jangan gunakan environment browser riset untuk development packaging bila ingin tetap terpisah.
