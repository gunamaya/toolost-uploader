# Profil privat dan checkpoint offline

Tahap ini disetujui pengguna setelah packaging. Implementasi internal ada di `toolost_uploader/storage.py`, bukan command akun baru. CLI masih hanya `validate`. Tidak membuat/mengimpor profil Chrome, membaca cookie, login, account binding atau menghubungi Too Lost. Tes hanya menggunakan temporary directory; profil riset `.local/` tidak diadopsi.

## Lokasi dan konfigurasi

- macOS: `~/Library/Application Support/toolost-uploader`.
- Linux: `$XDG_STATE_HOME/toolost-uploader`, fallback `~/.local/state/toolost-uploader`; XDG path harus absolut. Linux belum diuji pada host nyata. Windows ditolak (`unsupported_platform`); tidak menjanjikan private ACL dengan chmod saja.
- Alias ASCII `[A-Za-z0-9_-]{1,64}`, bukan path. Nama case-only dapat bertabrakan pada filesystem case-insensitive: isi config harus cocok persis atau `profile_mismatch`, bukan mengadopsi identitas alias lain.
- `profiles/<alias>/profile.json` hanya `{storage_version:1, profile:<alias>, account_fingerprint:null}`. Tidak ada custom user-data-dir, email, password/cookie atau klaim akun terverifikasi. Konfigurasi lain/unknown fields ditolak.
- Subtree aplikasi directory 0700, file 0600, owner effective user. Permission yang sudah terlalu terbuka ditolak, tidak otomatis di-chmod. Symlink di jalur storage dan hardlink file ditolak. Parent OS (mis. `/tmp` pada tes) tidak diubah permission-nya. Root override internal hanya untuk test/embedding, tidak tersedia sebagai flag CLI.
- Storage memegang directory fd dan memakai operasi relative `dir_fd` + `O_NOFOLLOW`. Tidak mengikuti symlink pada komponen jalur. Bukan sandbox melawan root, malware, proses user yang sama, directory yang dipindahkan oleh user tersebut, ACL khusus, NFS atau filesystem remote; gunakan filesystem lokal dan akun OS tepercaya. Belum ada audit ACL lintas platform.

## Lock dan lifecycle

`profile(alias)` adalah context manager yang memegang `flock(LOCK_EX|LOCK_NB)` pada `writer.lock`. Satu penulis per alias; konflik langsung `profile_locked`. Alias berbeda dapat dibuka paralel. Semua operasi checkpoint memakai session dalam context yang sama; handle tertutup ditolak.

Lock file tidak pernah dihapus saat unlock. Kernel melepas lock saat fd/proses ditutup atau mati, jadi tidak perlu stale PID heuristic atau membunuh proses. Lock advisory untuk pemanggil kooperatif; Chrome/executor belum terintegrasi dan lifetime browser tidak dicakup oleh helper ini. Jangan unlink lock manual saat dipakai.

## Snapshot dan write atomik

- `create_checkpoint(manifest, manifest_dir)` memvalidasi struktur dan seluruh hash/file memakai validator yang sama. `manifest_dir` harus absolut. Snapshot JSON terpisah dari dict pemanggil; path relatif tetap berpatokan pada direktori manifest yang dicatat privat.
- Satu file `checkpoints/<release_id>.json` per rilis dalam profil, dengan `run_id` UUID hex lokal, `revision`, manifest snapshot + canonical SHA-256 (sorted keys, ASCII JSON, separator compact), record SHA-256, alias, state dan placeholder akun/draft null. Hash aset tetap berada pada referensi manifest. Batas record lokal 2 MiB.
- Create menolak checkpoint yang sudah ada, termasuk cancelled; file rusak tidak dianggap absent dan tidak ditimpa otomatis. Tidak memindai judul atau menciptakan run retry diam-diam.
- Read memeriksa struktur/unknown keys, identity alias/release/run, hash snapshot dan keseluruhan record tanpa membuka ulang aset. Aset hilang tidak merusak kemampuan membaca checkpoint, tetapi bukan izin resume. Snapshot metadata dapat berisi nama/rights/path privat dari manifest; tidak dicetak ke stdout/log. Raw lyrics tidak disimpan, hanya file reference; unknown credential fields ditolak oleh validator manifest. Tidak dapat mendeteksi secret yang sengaja disisipkan ke field teks yang sah.
- Transisi internal satu-satunya `cancel_checkpoint` dari `validated` ke `cancelled`, dengan exact `run_id` dan `expected_revision`. Tidak menerima arbitrary field update, draft_saved, remote ID atau binding akun. Ini pembatalan catatan lokal, bukan membatalkan server.
- Write: temporary file exclusive 0600 dalam directory yang sama → write/flush → fsync file → `os.replace` → fsync directory. Error sebelum replace: `write_failed`, checkpoint lama tidak berubah. Error sesudah replace: `write_outcome_unknown`; baca dan rekonsiliasi revisi, jangan ulang update membabi buta.
- Process crash sebelum rename meninggalkan checkpoint lama dan mungkin orphan `.pending-*`; sesudah rename checkpoint baru utuh. Orphan tidak dipromosikan/dihapus otomatis. Atomic visibility bukan janji durability universal saat power loss: fsync/hardware/filesystem punya batas sendiri. SHA-256 bukan MAC/signature; user yang sama bisa menulis ulang record beserta hash.

## Belum tersedia

Update tahap berikutnya: attempt journal **fake offline** terpisah kini tersedia di journal.py, lihat OFFLINE-JOURNAL.md. Format checkpoint tidak berubah dan account/draft tetap null. Pernyataan attempt journal belum tersedia di bawah merujuk executor produksi, bukan simulasi.

Tidak ada command profile/init/login/status/resume, profile deletion, browser dir, remote state, track mapping, approval, attempt journal, checkpoint migration/reset atau executor. `storage_version:1` hanya format internal unreleased, terpisah dari `schema_version` manifest/result. Penambahan state remote wajib menunggu desain binding/attempt dan review; helper ini tidak membuktikan identitas akun.

## Tes

Verifikasi sesi ini pada macOS/Python 3.14.7: build wheel melalui sdist berhasil; suite lengkap dengan dependency dev dan uji distribusi aktif **47/47 lulus tanpa skip**. `git diff --check` bersih. Tidak ada browser/akun diakses; Linux/Windows bukan hasil pengujian host ini.

```sh
python3 -m unittest discover -s tests -v
# Semua tes termasuk schema dan instalasi wheel:
.local/packaging-venv/bin/python -m build
TOOLOST_TEST_DIST_DIR=dist .local/packaging-venv/bin/python -m unittest discover -s tests -v
```

Mencakup alias/traversal, permissions/owner/hardlink/symlink, snapshot terpisah, hash corruption/unknown/duplicate keys, asset validation, conflict revisi/run, lock proses kedua, SIGKILL lock owner, fault injection file/directory fsync/rename dan process crash tepat sebelum/sesudah rename. Fault injection hanya storage sintetis lokal, tidak akun/browser. Rujukan API: https://docs.python.org/3/library/os.html dan https://docs.python.org/3/library/fcntl.html.
