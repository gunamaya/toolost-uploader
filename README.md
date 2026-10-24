# Toolost uploader

Riset dan rancangan CLI Python + Playwright untuk mengelola draft release Too Lost, terpisah dari integrator yt-to-flowmusic. **Uploader/CLI terpasang belum tersedia; validator offline awal tersedia sebagai script stdlib.**

- [Indeks riset](docs/RESEARCH.md)
- [Prompt melanjutkan pengembangan](docs/CONTINUE-PROMPT.md)
- [Kontrak v1 untuk review](docs/CONTRACT-V1.md)
- [Kontrak release list/detail/publish](docs/RELEASE-CONTRACT.md) — publish masih capability future, tidak diuji atau dieksekusi selama riset.
- [Script browser riset](docs/BROWSER.md)
- [Validator offline dan cakupan schema](docs/OFFLINE-VALIDATION.md)

```sh
python3 scripts/validate.py path/to/manifest.json --json
```

Schema v1 masih unreleased. Nama distribusi `toolost-uploader`, modul `toolost_uploader`, executable `toolost` disetujui untuk tahap berikutnya; belum ada packaging/console entry point. Validator hanya membaca manifest dan aset, tidak membuka browser atau menjalankan upload/publish.

Scope riset maksimal upload dan simpan draft. Tidak ada izin/tindakan Publish atau distribusi. Produk final dapat mendukung release pada fase terpisah dengan persetujuan eksplisit.

Profil browser, capture akun dan aset riset disimpan lokal dalam `.local/` dan tidak boleh di-commit. Repo private bukan tempat penyimpanan cookie, kredensial atau media pengguna.

Contoh JSON pada docs hanya ilustrasi: hash nol dan path contoh bukan aset valid. Command di kontrak adalah proposal, bukan command yang telah diimplementasikan.

Tes offline harness dan validator (stdlib, tanpa login/network):

```sh
python3 -m unittest discover -s tests -v
```

Jangan publish paket PyPI sebelum diminta. Tidak ada lisensi redistribusi yang ditetapkan pada tahap ini.
