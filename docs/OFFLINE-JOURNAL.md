# Attempt journal dan rekonsiliasi fake offline

Implementasi internal `toolost_uploader/journal.py`, atas permintaan pengguna. Bukan executor Too Lost, bukan API integrator stabil, tidak ada command baru. Hanya menerima exact class `FakeAdapter` sintetis dalam memori; adapter browser/arbitrary object ditolak. Tidak ada network, login, publish atau state produksi `draft_saved`.

## Scope kecil

Satu operasi `fake.save`, satu attempt per checkpoint. Fake state hanya `{title, track_ids}`; stable track IDs di sini adalah data sintetis, **bukan solusi identitas track Too Lost**. Baseline dan desired simulasi independen dari metadata rilis checkpoint; ini harness keselamatan outcome, bukan penerapan manifest ke layanan. Unknown keys/duplikat track IDs ditolak. Tidak ada create/upload/delete/reorder executor atau retry/reset attempt.

Jurnal `<release_id>.attempt.json` dalam directory checkpoint yang sama, dilindungi lock/permission/write atomik storage. Checkpoint lama tidak berubah format. Isi jurnal: versi internal, UUID attempt, run/profile/release, hash exact checkpoint, identitas fake tetap, hash baseline/desired, outcome, hash record. Tidak menyimpan title/state mentah, exception, cookie atau lirik. Checkpoint sendiri tetap privat seperti LOCAL-STATE.md. Hash bukan autentikasi atau bukti akun.

## Alur

1. `prepare`: validasi run/revisi checkpoint validated; read baseline lengkap dan identity fake tepat; desired berbeda. Intent `prepared` ditulis atomik sebelum mutasi. Jurnal existing/korup tidak ditimpa. Tidak menghubungi save.
2. `execute`: exact attempt/run/checkpoint/desired dan baseline diperiksa ulang. Account/draft mismatch atau baseline berubah menghentikan mutasi. Setelah itu **simpan `unknown` durably sebelum memanggil save satu kali**. Write gagal/unknown berarti save tidak dipanggil. Crash sesudah intent namun sebelum save tetap unknown, bukan izin retry.
3. Save response bukan bukti persistence. Respons sukses dilanjutkan read-only `reconcile`; timeout save langsung mengembalikan unknown sampai reconcile terpisah. Exception lain/interruption merambat tanpa disimpan; intent unknown sudah ada. Tidak ada retry otomatis.
4. `reconcile` hanya menerima unknown. Read timeout, coverage incomplete atau identity track ambigu tetap unknown. Account/draft berbeda → conflict. Complete read-back exact desired hash → applied; exact baseline hash → not_applied; state lain → conflict. Observasi hanya fake dalam memori, tidak membuktikan server/media persistence.
5. Semua hasil terminal (`applied`, `not_applied`, `conflict`) menolak execute lagi. Tidak ada retry bahkan untuk not_applied. Pending unknown dapat direconcile berulang tanpa save. Revisi/hash checkpoint berubah atau checkpoint cancelled memblokir jurnal lama.

## Failure modes yang diuji

- save sukses + read-back; save diterapkan tetapi response hilang; timeout sebelum kirim;
- partial track state, identity ambigu, read timeout; baseline berubah/account/draft mismatch;
- desired/attempt/run/revisi mismatch, jurnal korup/duplicate keys, checkpoint berubah/cancelled;
- intent write gagal dan directory fsync gagal sesudah rename: nol save calls;
- hasil read-back gagal dijurnal setelah save: intent tetap unknown, reconcile ulang tanpa save;
- interruption sesudah unknown sebelum save, buka ulang profile, reconcile tanpa mutasi ulang.

FakeAdapter modes: success, lost_response, before_send, partial, ambiguous. State fake bertahan hanya selama object masih tersedia di memori; reopen profile pada tes bukan simulasi server persisten lintas proses. `SystemExit` fault meniru penghentian control flow journal, bukan bukti power-loss server. Tes proses SIGKILL dan rename boundary storage terpisah ada di test_storage.py. Filesystem lokal tepercaya dan lock kooperatif tetap prasyarat.

## Berikutnya (belum dibuat)

Verifikasi sesi ini: build wheel melalui sdist berhasil, suite lengkap `TOOLOST_TEST_DIST_DIR=dist .local/packaging-venv/bin/python -m unittest discover -s tests -q` **59/59 lulus tanpa skip** pada macOS/Python 3.14.7; `git diff --check` bersih. Termasuk tes storage tahap sebelumnya yang masih belum di-commit. Tidak ada akun/browser diakses.

Attempt history/multi-attempt dengan approval ulang, binding account/remote track sungguhan, create recovery ambigu, media partial upload dan fake UI modal/delayed field memerlukan scope berikutnya. Jangan menghubungkan helper fake ini ke browser sebagai jalan pintas. CLI tetap hanya validate. Tidak ada commit/push atau publikasi otomatis.
