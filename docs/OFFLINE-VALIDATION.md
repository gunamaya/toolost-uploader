# Validasi offline awal

Keputusan review 25 Oktober 2026: pengguna menyetujui schema/validator offline dan fixture sintetis; nama distribusi `toolost-uploader`, modul `toolost_uploader`, executable `toolost`. Penamaan ini bukan bukti ketersediaan PyPI. Packaging lokal dan console entry point kini tersedia (persetujuan lanjutan pengguna); operasi akun, upload, profil dan publish belum tersedia.

```sh
toolost validate path/to/manifest.json --json
python3 -m toolost_uploader validate path/to/manifest.json --json
python3 scripts/validate.py path/to/manifest.json --json
python3 -m unittest discover -s tests -v
```

Runtime stdlib saja, tanpa browser, jaringan atau pembacaan cookie. Instalasi package lokal memakai setuptools sebagai build dependency; extra `dev` menyediakan `build` dan `jsonschema`, tidak diperlukan saat menjalankan CLI. Manifest dan aset yang dirujuk dibaca, tidak dimodifikasi. stdout satu objek JSON untuk pemanggilan script yang benar; exit 0 valid, 2 invalid input, 5 bila output tidak dapat ditulis. Usage salah hanya usage/pesan generik stderr dan exit 2, tanpa mengulang nilai argumen. Help/version memakai stdout, exit 0. Tanpa `--json`, CLI menampilkan status singkat stdout dan warning/error stderr. Tidak ada log berisi nilai input, path, key asing atau lirik. Hasil error pertama dikembalikan, bukan seluruh daftar error.

Verifikasi awal validator (historis): 22 tes, 21 lulus dan 1 skipped saat evaluator independen belum terpasang.

Verifikasi packaging terbaru: 28 tes lulus tanpa skip dengan `TOOLOST_TEST_DIST_DIR=dist .local/packaging-venv/bin/python -m unittest discover -s tests -v`. `jsonschema` 4.26.0 memeriksa kedua meta-schema dan contoh hasil; format tanggal diaktifkan. Build 1.6.1 + setuptools 84.2.1 menghasilkan sdist dan wheel melalui sdist. Instalasi wheel ke venv bersih menggunakan `--no-index --no-deps` berhasil; console entry point dan `python -I -m toolost_uploader` berhasil dari luar checkout. Dependency pengembangan hanya dipasang pada `.local/packaging-venv`, bukan environment browser/global. Tidak ada publikasi paket.

## Schema dan cakupan

- `schemas/manifest-v1.schema.json`: JSON Schema Draft 2020-12 untuk struktur manifest unreleased v1.
- `schemas/validate-result-v1.schema.json`: hanya hasil operasi offline `validate`. Hasil upload/status/release/publish masih proposal, belum memiliki schema implementasi. Unknown/null AI untuk inspect tetap proposal; input upload normal wajib boolean, tidak boleh null/omitted.
- Script memvalidasi kontrak secara langsung dengan stdlib, bukan evaluator JSON Schema umum. Schema eksternal memerlukan pemeriksaan format tanggal diaktifkan. Duplicate JSON keys, keunikan `track_id`, tipe integer literal, file/hash/encoding dan perubahan file adalah pemeriksaan tambahan script, bukan semua dapat diekspresikan oleh schema.
- Metadata opsional dari CONTRACT-V1 divalidasi bentuknya, tidak diterapkan ke akun. UPC/ISRC/ISWC hanya string nonblank saat ini: tidak memverifikasi assignment, checksum, registry atau mapping switch UI. Genre/language tidak dicek terhadap pilihan layanan. Artist/writer/rights declarations, delivery/stores/territories, clear dan participant override ditolak sebagai field unsupported, bukan diabaikan.
- Array tracks adalah urutan final; ID lokal ASCII huruf/angka/underscore/hyphen, panjang 1-128. Tidak memaksakan jumlah track menurut label Album/EP.
- Field optional omitted tetap omitted; tidak ada pengisian baseline/default atau perubahan input. Null/blank bukan perintah clear. Konflik provenance AI menghasilkan warning, bukan perubahan deklarasi.

## File dan batas lokal

- Manifest UTF-8 maksimum 1 MiB dan 1-1000 track; lirik UTF-8 maksimum 1 MiB. Batas ini kebijakan lokal awal, **bukan batas Too Lost/DSP**.
- Referensi relatif terhadap direktori manifest; absolute path diperbolehkan. File reguler readable, nonempty dengan SHA-256 lowercase yang cocok wajib untuk audio/artwork/lirik. Tes memakai bytes sintetis dalam temporary directory, bukan audio/artwork produksi.
- Symlink aset di komponen path mana pun ditolak pada tahap ini. Path relatif `..` diperbolehkan sebagai referensi lokal eksplisit, bukan sandbox. Jangan memvalidasi manifest tak tepercaya dengan akses filesystem lebih luas daripada yang diperlukan.
- Hash dibaca streaming; perubahan ukuran/mtime/ctime saat baca ditolak. Ini bukan snapshot immutable atau perlindungan TOCTOU lengkap terhadap perubahan direktori serentak. Validator tidak memberikan izin upload; executor nanti wajib snapshot atau verifikasi ulang sebelum mutasi.
- Tidak mendeteksi codec, dimensi artwork, kecocokan lirik/audio, hak legal, kualitas media atau kesiapan QC/distribusi. `valid` hanya validasi offline sesuai cakupan ini; `remote_verified` selalu false.

## Keputusan yang masih ditunda

Account binding UI stabil, remote track identity, approval take final oleh integrator, profile storage/lock/checkpoint dan penerapan override kode/metadata perlu tahap berikutnya. `status` nantinya memakai run-id, bukan draft-id dalam contoh lama CONTRACT-PLAN. Persetujuan offline ini bukan izin live smoke, implementasi publish, distribusi, commit/push atau publish PyPI.

Referensi spesifikasi: https://json-schema.org/draft/2020-12/json-schema-validation (khususnya `format` yang default-nya annotation, bukan assertion).

## Packaging lokal

`pyproject.toml` memakai setuptools dengan daftar package eksplisit (`toolost_uploader` saja); tidak ada runtime dependency. Versi alpha `0.1.0a0`, Python minimum deklaratif 3.10. Belum ada matriks multi-versi/OS; pengujian sesi packaging pada macOS Python 3.14.7. Tidak ada lisensi redistribusi yang ditetapkan; classifier `Private :: Do Not Upload` sengaja dipertahankan.

Wheel hanya membawa modul runtime/metadata. Sdist membawa sumber, tes, wrapper, contoh sintetis dan schema untuk pengujian; tidak membawa profil/capture/aset privat. Schema tetap di `docs/schemas` dalam checkout/sdist, bukan resource runtime wheel. Import internal bukan kontrak integrator; integrator tetap memakai subprocess dan JSON.

Build: `python -m build`; tes lengkap: `TOOLOST_TEST_DIST_DIR=dist python -m unittest discover -s tests -v` setelah `pip install -e '.[dev]'` di venv terpisah. Tes default tetap offline stdlib, melewati uji instalasi bila variabel tersebut tidak disetel dan melewati evaluator schema bila extra dev belum dipasang.
