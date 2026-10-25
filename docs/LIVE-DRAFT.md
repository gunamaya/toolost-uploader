# Executor Playwright smoke draft-only

Koreksi arah setelah pengguna meminta implementasi, bukan pengulangan riset manual. Kini tersedia `scripts/upload_draft.py` dan `toolost_uploader/live_draft.py`: kode nyata Playwright, bukan FakeUI. **Smoke live selesai sampai Save/reopen dengan perbaikan locator; belum dianggap uploader produksi.** Tidak ada aksi Publish/delete/rights/artist/services. CLI terpasang `toolost` masih validate.

## Command

```sh
# Environment browser terpisah; Playwright sudah tersedia pada .venv riset lokal.
python -m pip install '.[browser]'
python scripts/upload_draft.py /path/to/manifest.json \
  --profile smoke-alias --expected-account ACCOUNT_ID \
  --cdp http://127.0.0.1:9437 --approve-draft --accept-ui-date-for-smoke
```

Tidak meluncurkan/mematikan Chrome atau melakukan login; attach ke CDP loopback milik operator yang sudah login manual. Jangan gunakan Chrome harian. Satu halaman https://toolost.com wajib; DevTools dikecualikan oleh origin. Start dari portal tanpa dialog; editor existing ditolak agar staged changes tidak ditinggalkan diam-diam. Expected account harus berasal dari review pengguna, bukan artist ID; tidak di-hardcode ke repo.

## Scope

Manifest divalidasi dengan hash/aturan yang sama. Hanya Single dengan satu track, field minimal release dan track_id/title/audio/ai_assisted. Optional field lain ditolak. Artwork dan audio di-hash ulang sebelum chooser; ini bukan snapshot immutable/TOCTOU protection lengkap. release_date manifest **belum diterapkan**, hanya UI baseline diwarisi dengan flag eksplisit smoke; hasil selalu subset, bukan seluruh manifest diterapkan. Tidak untuk penjadwalan/distribusi produksi.

Urutan: observasi respons asli `/api/auth/me` saat membuka release list → akun cocok → New Release sekali → modal tipe Single → modal judul → Create Release sekali → ID editor dari URL → artwork chooser → tunggu Artwork selected → audio dialog/chooser → Upload 1 file sekali → satu row + dialog selesai → title track dan AI berdasarkan ARIA scoped label → Done → Save Changes sekali dan konfirmasi Save bila muncul → reopen exact draft → read-back title/Single/artwork/satu row/title track/AI.

AI label/container, nama upload/artwork dan konfirmasi Save memakai bukti UI riset; belum diverifikasi lewat live script. Locator mismatch, dialog tak terduga, timeout atau write error berhenti; tidak fallback ke force click, DOM mutation, endpoint tulis atau Publish. Satu row/title bukan bukti remote track ID atau remote audio hash/codec. Encoding artwork ditunggu pada selected; audio row/dialog hanyalah batas UI yang tersedia, bukan bukti seluruh proses server siap distribusi.

## Journal dan failure

Storage per user + lock alias memakai LOCAL-STATE. Checkpoint dibuat sebelum attach; existing release_id tidak dapat membuat run baru. File `<release_id>.live.json` private mencatat unknown sebelum setiap operasi, observed setelahnya, ID draft bila diketahui. Create masih unknown jika proses terhenti sebelum ID diketahui; wajib rekonsiliasi manusia, bukan create ulang. Tidak ada resume otomatis atau delete/reset CLI. Script error menghasilkan reconciliation_required exit4 tanpa exception/path/credentials; sukses subset exit0. Ini envelope script riset, bukan schema result produksi.

Guard akun dilakukan saat preflight; belum memantau pergantian akun serentak sepanjang run. Lock alias tidak mengunci harness Chrome atau manusia yang mengoperasikan jendela; operator harus menghentikan interaksi saat eksekusi. Journal dan checkpoint bukan transaksi lintas file. Jangan jalankan ulang dengan release_id baru untuk melewati attempt yang unknown.

## State sesi saat implementasi

Sebelum kode ditulis, langkah manual berhenti di modal **Name your release** setelah memilih Single. **Create Release belum diklik, file belum diupload, Save belum dilakukan.** Script belum dijalankan pada modal tersebut dan menolak memulai dari `/uploader`. Tidak membuat manifest produksi/aset fixture baru otomatis. Persetujuan live yang sudah diberikan tetap hanya draft uji baru dan aset riset yang dipilih, bukan izin merilis.

Tes offline menggunakan mocks untuk urutan mutasi, fail-stop, journal-before-action, login/target/modal guard, hash mismatch, field unsupported, approval/loopback flags. Bukan bukti selector end-to-end. Packaging extra browser opsional; runtime validate tetap stdlib. Tidak ada instalasi dependency baru dalam sesi implementasi ini.

## Hasil smoke live dan perbaikan

Satu draft baru dibuat lewat script; artwork dan satu WAV terpilih dari daftar riset ber-hash diupload, tanpa duplicate create/media. Tombol artwork/audio ternyata memiliki subtitle; locator diperbaiki memakai awalan label. Dialog audio di-scope Cancel yang stabil karena browse files hilang setelah file dipilih. Recovery hanya setelah operator membuktikan tahap sebelum kirim/file sudah dipilih, memakai exact jejak jurnal run; bukan retry otomatis.

Pada Single ini Track name disabled dan mengikuti release title. Tidak bypass disabled. Pengguna menyetujui amendment release title menjadi judul lagu; amendment dicatat privat terpisah dari snapshot awal. AI memakai scope .ted__ai-toggle dan ARIA read-back, klik pembungkus visual hanya bila nilai berbeda. Save dipanggil sekali. Read-back awal timeout karena asumsi heading judul; diperbaiki menunggu panel Basic Information dan Single name. Verifikasi berikut hanya readback(), tanpa Save kedua.

Hasil reopen terverifikasi: Single; judul release dan track Terangnya Belum Pulang; artwork selected; tepat satu track; AI=true. AI Documentation masih issue manual; tanggal/default rights/services tidak diklaim verified, tidak ada Publish. ID draft, manifest/amendment, aset dan event ledger tetap privat. Draft lama tidak dimodifikasi.

Flag recovery --resume-stopped-before-artwork/--resume-stopped-before-audio/--resume-selected-audio/--resume-open-metadata sengaja sempit terhadap jejak debugging ini. --approve-release-title-equals-track hanya untuk amendment yang direview. Bukan resume umum dan jangan memakai release_id baru untuk melewati unknown. Preflight identity tidak diulang penuh oleh recovery khusus ini; jangan memakai mode recovery unattended atau saat operator mengganti sesi akun. Perlu refactor/test recovery lebih lanjut sebelum distribusi.
