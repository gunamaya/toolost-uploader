# Executor Playwright smoke draft-only

Koreksi arah setelah pengguna meminta implementasi, bukan pengulangan riset manual. Kini tersedia `scripts/upload_draft.py` dan `toolost_uploader/live_draft.py`: kode nyata Playwright, bukan FakeUI. **Smoke live selesai sampai Save/reopen dengan perbaikan locator; belum dianggap uploader produksi.** Tidak ada aksi Publish/delete/rights/artist/services. Subcommand CLI terpasang `toolost upload --draft-only` kini tersedia di samping `toolost validate`.

## Command

```sh
# Environment browser terpisah; Playwright sudah tersedia pada .venv riset lokal.
python -m pip install '.[browser]'

# Melalui CLI resmi:
toolost upload /path/to/manifest.json --draft-only \
  --profile smoke-alias --expected-account ACCOUNT_ID \
  --cdp http://127.0.0.1:9437 --approve-draft --accept-ui-date --verbose --json

# Atau melalui script langsung:
python scripts/upload_draft.py /path/to/manifest.json \
  --profile smoke-alias --expected-account ACCOUNT_ID \
  --cdp http://127.0.0.1:9437 --approve-draft --accept-ui-date-for-smoke
```

Tidak meluncurkan/mematikan Chrome atau melakukan login; attach ke CDP loopback milik operator yang sudah login manual. Jangan gunakan Chrome harian. Satu halaman https://toolost.com wajib; DevTools dikecualikan oleh origin. Start dari portal tanpa dialog; editor existing ditolak agar staged changes tidak ditinggalkan diam-diam. Expected account harus berasal dari review pengguna, bukan artist ID; tidak di-hardcode ke repo.

## Scope

Manifest divalidasi dengan hash/aturan yang sama. Mendukung Single (1 track) dan Album (multi-track), dengan field wajib minimal release dan track_id/title/audio/ai_assisted. Optional field lain ditolak. Artwork dan audio di-hash ulang sebelum chooser; ini bukan snapshot immutable/TOCTOU protection lengkap. release_date manifest **belum diterapkan**, hanya UI baseline diwarisi dengan flag eksplisit smoke/draft; hasil selalu subset, bukan seluruh manifest diterapkan. Tidak untuk penjadwalan/distribusi produksi.

Urutan: observasi respons asli `/api/auth/me` saat membuka release list → akun cocok → New Release sekali → modal tipe Single → modal judul → Create Release sekali → ID editor dari URL → artwork chooser → tunggu Artwork selected → audio dialog/chooser → Upload 1 file sekali → satu row + dialog selesai → title track dan AI berdasarkan ARIA scoped label → Done → Save Changes sekali dan konfirmasi Save bila muncul → reopen exact draft → read-back title/Single/artwork/satu row/title track/AI.

AI label/container, nama upload/artwork dan konfirmasi Save memakai bukti UI smoke yang sukses pada commit 74a24b2. Hardening sesudah commit itu hanya diuji offline, tidak mengulang smoke. Locator mismatch, dialog tak terduga, timeout atau write error berhenti; tidak fallback ke force click, DOM mutation, endpoint tulis atau Publish. Satu row/title bukan bukti remote track ID atau remote audio hash/codec. Encoding artwork ditunggu pada selected; audio row/dialog hanyalah batas UI yang tersedia, bukan bukti seluruh proses server siap distribusi.

## Journal dan failure

Storage per user + lock alias memakai LOCAL-STATE. Checkpoint dibuat sebelum attach; existing release_id tidak dapat membuat run baru. `live_journal.py` menyimpan `<release_id>.live.json` versi 2: digest checkpoint, run/profile/release, akun yang direview, endpoint, ID draft, amendment dan event berurutan dengan digest record. Semua tetap privat. Unknown ditulis atomik sebelum operasi, observed hanya setelah operasi dan guard berhasil. Event yang tidak sesuai urutan, duplicate intent, binding/digest berbeda, checkpoint cancelled, atau ID draft berubah ditolak. Hash mendeteksi korupsi, bukan tanda tangan atau perlindungan terhadap operator yang sengaja mengubah file dan menghitung ulang hash.

Create masih unknown jika proses terhenti sebelum ID diketahui; wajib rekonsiliasi manusia, bukan create ulang. Tidak ada resume mutasi otomatis atau delete/reset CLI. Script error menghasilkan reconciliation_required exit4 dengan kode aman; sukses subset exit0. Ini envelope script riset, bukan schema result produksi. Journal lama dari smoke tidak dimigrasi/replay otomatis karena tidak memiliki binding versi 2. Jangan memakai release_id baru atau mengedit ledger untuk melewati unknown.

Preflight akun penuh tetap mengamati respons asli aplikasi `/api/auth/me` saat navigasi portal, bukan direct fetch/cookie/token. Listener context tetap aktif sampai selesai: akun berbeda, 401 atau respons identity tidak terbaca menandai identity changed secara sticky. Guard dijalankan sebelum klik/fill/chooser dan setelah tahap. Route guard membatalkan request non-read ke origin Too Lost saat identity/target berubah, termasuk bila perubahan teramati selama auto-wait klik. Listener/route dilepas tanpa menutup Chrome eksternal. Tidak membaca header/body request atau menyimpan respons auth.

Lock alias tidak mengunci Chrome atau operator. Pergantian sesi tanpa respons identity/navigasi yang teramati, request yang sudah terkirim, service worker, WebSocket dan efek server di luar route guard tidak dapat dibuktikan aman oleh tes Mock. Endpoint yang sama bukan bukti sesi browser yang sama setelah restart. Guard ini bukan transaksi atomik akun-draft; operator wajib tidak berinteraksi selama run. Journal dan checkpoint juga bukan transaksi lintas file.

## Rekonsiliasi terbatas, bukan resume produksi

- Empat flag `--resume-stopped-before-artwork`, `--resume-stopped-before-audio`, `--resume-selected-audio`, `--resume-open-metadata` adalah kompatibilitas historis saja: sekarang selalu ditolak sebelum disk/browser (`debug_recovery_requires_readback_only`). Tidak ada replay upload/metadata/Save dari jejak debugging.
- `--reconcile-readback-only` hanya menerima journal versi 2 yang sudah mencapai attempt Save (unknown/observed) atau readback sebelumnya. Create/upload unknown tetap memerlukan review manual; tidak ada cara melanjutkan mutasinya.
- Manifest asli harus cocok persis dengan checkpoint dan direktori asalnya, tetapi bytes aset tidak dibaca/hash ulang karena tidak ada upload. Binding akun dan endpoint harus sama. Amendment baru ditolak pada rekonsiliasi.
- Operator harus menyiapkan portal tanpa dialog; editor terbuka tidak ditinggalkan otomatis. Preflight akun penuh diulang sebelum membuka exact draft. Semua request non-read ke origin Too Lost diblokir selama rekonsiliasi dan readback. Tidak fill/toggle/Done/Save, hanya membuka panel/editor dan membaca subset.
- Readback cocok menambah `readback/verified_subset`; event `save/unknown` tetap unknown, tidak diganti menjadi observed palsu. Hasil script `draft_readback_subset`, bukan klaim mengirim Save. Pemanggilan rekonsiliasi ulang tidak menambah duplicate event. Mismatch/timeout tidak mengubah journal atau memberi izin retry.
- `--approve-release-title-equals-track` sekarang hanya persetujuan amendment **sebelum create baru**, bukan izin mengedit judul draft existing. Before/after title, keputusan eksplisit, digest manifest asli/efektif disimpan sebelum mutasi. Snapshot checkpoint asli tidak berubah; manifest efektif diturunkan dari amendment tersimpan. Tidak bisa mengganti amendment pada run yang sudah dimulai.

Resume produksi belum tersedia. Kebutuhannya mencakup identitas account/session dan remote track yang lebih kuat, pemetaan state remote parsial, approval per operasi setelah rekonsiliasi, serta kebijakan conflict/unknown tanpa retry buta. Tidak ada command `toolost resume` atau promosi fake workflow menjadi bukti live.

## State sesi saat implementasi

Sebelum kode ditulis, langkah manual berhenti di modal **Name your release** setelah memilih Single. **Create Release belum diklik, file belum diupload, Save belum dilakukan.** Script belum dijalankan pada modal tersebut dan menolak memulai dari `/uploader`. Tidak membuat manifest produksi/aset fixture baru otomatis. Persetujuan live yang sudah diberikan tetap hanya draft uji baru dan aset riset yang dipilih, bukan izin merilis.

Tes offline menggunakan mocks untuk urutan mutasi, fail-stop, journal-before-action, login/target/modal guard, hash mismatch, field unsupported, approval/loopback flags. Bukan bukti selector end-to-end. Packaging extra browser opsional; runtime validate tetap stdlib. Tidak ada instalasi dependency baru dalam sesi implementasi ini.

## Hasil smoke live dan perbaikan

Satu draft baru dibuat lewat script; artwork dan satu WAV terpilih dari daftar riset ber-hash diupload, tanpa duplicate create/media. Tombol artwork/audio ternyata memiliki subtitle; locator diperbaiki memakai awalan label. Dialog audio di-scope Cancel yang stabil karena browse files hilang setelah file dipilih. Recovery hanya setelah operator membuktikan tahap sebelum kirim/file sudah dipilih, memakai exact jejak jurnal run; bukan retry otomatis.

Pada Single ini Track name disabled dan mengikuti release title. Tidak bypass disabled. Pengguna menyetujui amendment release title menjadi judul lagu; amendment dicatat privat terpisah dari snapshot awal. AI memakai scope .ted__ai-toggle dan ARIA read-back, klik pembungkus visual hanya bila nilai berbeda. Save dipanggil sekali. Read-back awal timeout karena asumsi heading judul; diperbaiki menunggu panel Basic Information dan Single name. Verifikasi berikut hanya readback(), tanpa Save kedua.

Hasil reopen terverifikasi: Single; judul release dan track Terangnya Belum Pulang; artwork selected; tepat satu track; AI=true. AI Documentation masih issue manual; tanggal/default rights/services tidak diklaim verified, tidak ada Publish. ID draft, manifest/amendment, aset dan event ledger tetap privat. Draft lama tidak dimodifikasi.

Recovery flags pada commit 74a24b2 dahulu sengaja sempit terhadap jejak debugging ini dan tidak mengulang identity preflight penuh. Jalur mutasi historis tersebut kini dinonaktifkan; lihat kontrak rekonsiliasi di atas. Draft smoke sukses dan ledger privatnya tidak diubah atau diuji ulang dalam hardening offline.
