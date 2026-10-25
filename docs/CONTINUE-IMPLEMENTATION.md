# Prioritas kelanjutan implementasi

Pengguna menegaskan agar membuat script nyata, bukan mengulang riset UI/fake framework. `scripts/upload_draft.py` + `live_draft.py` tersedia, lihat LIVE-DRAFT.md. Smoke subset sudah sukses sampai Save/reopen pada commit 74a24b2. Jangan mengulang smoke atau membuat draft/upload baru tanpa scope dan persetujuan eksplisit baru.

State modal Name your release sebelum Create adalah historis, bukan state live saat ini. Draft smoke sudah dibuat, artwork/satu WAV diupload, amendment title disetujui, AI=true, Save sekali dan reopen terverifikasi. AI Documentation masih issue manual. Tidak ada izin Publish, distribusi, rights, artist, services atau AI Documentation otomatis.

Lanjutkan menguji/memperbaiki script bounded dan verifikasi hasil sebenarnya, bukan menambah fake lapis baru. Semua live mutation berhenti pada Save, tanpa Publish. Account ID diambil dari respons asli aplikasi /api/auth/me, tidak direct fetch yang sebelumnya 403. Jangan hardcode user/artist/draft ID atau private paths ke produk/fixtures.

Update live terbaru: script sudah membuat satu draft baru dan upload artwork/satu WAV; beberapa locator diperbaiki melalui diagnosis script, tanpa duplicate upload. Single track title terkunci mengikuti release. Pengguna mengizinkan amendment release title menjadi Terangnya Belum Pulang. AI=true dan Save sekali; reopen readback memverifikasi Single/title/artwork/satu track/AI. Publish tidak disentuh; AI Documentation masih issue. Lihat LIVE-DRAFT.md. State modal lama di atas sudah historis; jangan create ulang atau mengulang smoke sukses. Recovery flags sekarang khusus run debugging, bukan resume produksi. Kode perbaikan belum otomatis commit/push.

## Hardening offline sesudah 74a24b2

- Recovery mutasi debugging lama dinonaktifkan, bukan dijadikan resume produksi. Tidak memigrasi ledger smoke atau menyentuh akun/browser dalam sesi ini.
- `live_journal.py` versi 2 mengikat checkpoint/run/profile/release/account/endpoint, memvalidasi urutan event dan ID draft, serta menolak duplicate intent. Tulis unknown sebelum setiap tahap, jangan retry pada exception atau kegagalan receipt.
- Amendment immutable disetujui dan diaudit sebelum create, snapshot awal tidak diubah. Tidak boleh dipakai untuk mengubah draft existing melalui recovery.
- `--reconcile-readback-only` hanya journal v2 sesudah attempt Save, dengan preflight akun penuh dari portal tanpa dialog. Tidak membutuhkan bytes aset; request non-read diblokir. Readback tidak mengarang Save observed atau mengeksekusi Save kedua.
- Listener identity aktif sepanjang run, guard target di batas UI dan request tulis. Ini belum menjamin sesi yang berubah tanpa event teramati atau efek request yang sudah terkirim.
- Tes offline mencakup mismatch, legacy/corrupt journal, preflight belum lengkap, duplicate create/upload/Save, amendment/digest, unknown Save/restart/reconciliation, dan account/session/target change. Tes Mock bukan bukti live baru.

Berikutnya: review desain resume produksi dan otoritas identity/remote track secara terpisah. Pertahankan CLI terpasang hanya `validate`; jangan menambah command proposal sebagai implementasi semu. Jalankan suite lengkap dan `git diff --check`; jangan commit/push atau membagikan data privat tanpa instruksi eksplisit.
