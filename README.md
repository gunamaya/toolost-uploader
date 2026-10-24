# Toolost uploader

Riset dan rancangan CLI Python + Playwright untuk mengelola draft release Too Lost, terpisah dari integrator yt-to-flowmusic. **CLI produk belum tersedia.**

- [Indeks riset](docs/RESEARCH.md)
- [Prompt melanjutkan pengembangan](docs/CONTINUE-PROMPT.md)
- [Kontrak v1 untuk review](docs/CONTRACT-V1.md)
- [Kontrak release list/detail/publish](docs/RELEASE-CONTRACT.md) — publish masih capability future, tidak diuji atau dieksekusi selama riset.
- [Script browser riset](docs/BROWSER.md)

Scope riset maksimal upload dan simpan draft. Tidak ada izin/tindakan Publish atau distribusi. Produk final dapat mendukung release pada fase terpisah dengan persetujuan eksplisit.

Profil browser, capture akun dan aset riset disimpan lokal dalam `.local/` dan tidak boleh di-commit. Repo private bukan tempat penyimpanan cookie, kredensial atau media pengguna.

Contoh JSON pada docs hanya ilustrasi: hash nol dan path contoh bukan aset valid. Command di kontrak adalah proposal, bukan command yang telah diimplementasikan.

Tes offline script observasi (stdlib, tanpa login/network):

```sh
python3 -m unittest discover -s tests -v
```

Jangan publish paket PyPI sebelum diminta. Tidak ada lisensi redistribusi yang ditetapkan pada tahap ini.
