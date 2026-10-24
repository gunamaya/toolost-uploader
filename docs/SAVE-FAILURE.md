# Save gagal sebelum request terkirim

Observasi 2026-10-25, lanjutan uji resume yang diminta pengguna. Tidak Publish/distribusi, upload ulang, Create Release, delete, logout, perubahan profil atau pemaksaan retry.

## Scope simulasi

Pada tab draft riset yang ID/judul/dua track-nya cocok baseline, request HTTP non-GET/HEAD/OPTIONS diblokir sementara melalui Playwright page.route dan route.abort('internetdisconnected'). Rule dipasang sebelum mengubah judul agar mutasi tidak sengaja terkirim. GET tetap diizinkan; ini bukan offline total atau pemutusan jaringan macOS.

Tidak membaca header, cookie, post_data, body request/response, atau kredensial. Log privat hanya method, origin/path tanpa query, dan resource_type. Tujuh request non-read diblokir; jumlah itu tidak membuktikan tujuh percobaan Save atau tujuh endpoint rilis karena bisa mencakup telemetry/operasi terkait. Tidak memakai endpoint hasil observasi untuk API otomatis.

## Langkah dan hasil

1. Verifikasi draft target, judul release baseline dan dua track/urutan sesuai MULTI-TRACK.md.
2. Tambahkan suffix judul ` - SAVE FAILURE PROBE`; blur.
3. Save Changes → konfirmasi Save → klik Save sekali, tunggu5detik.
4. UI menunjukkan `We could not process your release.` dan alert `Something went wrong while saving your release.` dengan Cancel dan Try again. Probe judul masih tampak lokal.
5. Tidak klik Try again: hasil harus direkonsiliasi, bukan retry buta.
6. Dalam finally, lepaskan hanya route guard milik uji; reload draft setelah jaringan tab normal kembali.
7. Judul kembali persis baseline. Dua track dan urutan tetap sesuai baseline; tidak perlu mutasi pemulihan atau upload ulang. Assert read-back lolos.

State akhir: draft pengganti yang sama, Manage Tracks, dua MP3 yang sudah ada, titlefilename, tanpa artwork. Judul probe tidak tersimpan dalam read-back. Error dialog tidak ada lagi setelah reload. Route guard sudah dilepas.

## Konsekuensi automasi

- Dialog error adalah sinyal kegagalan, bukan tombol yang boleh di-retry otomatis tanpa memeriksa target/server state.
- Bedakan local staged title, Save submitted, UI error dan persisted read-back. Jangan checkpoint save sukses hanya karena dialog Save menghilang.
- Simulasi ini memblokir request sebelum network; tidak menguji server menerima write lalu respons hilang. Baseline yang tetap utuh didukung read-back setelah reload, bukan asumsi semua error selalu rollback.
- Outcome unknown setelah request terkirim memerlukan rekonsiliasi desired vs actual dan deteksi konflik manual. Jangan Create Release/Upload sebagai fallback.
- Tidak membuktikan partial upload/encoding recovery, crash saat saving, expired session, concurrency atau duplicate-filename matching aman.
- Resource request yang luput dari page.route (misalnya service worker) tidak diklaim tercakup. Inilah alasan read-back wajib; pengujian ini bukan sandbox distribusi. Publish tidak pernah dipanggil.

## Status lanjutan

Uji browser restart, unsaved release title, track Done tanpa Save, dan Save blocked-before-send telah selesai. Gangguan upload, server-saved-response-lost dan session expiry tetap belum diuji. Dahulukan fixture/mock offline untuk failure matrix; pengujian live berisiko menambah media atau mengubah autentikasi harus dibatasi dan dikomunikasikan terpisah.

Bukti privat `.local/captures/save-failure/`: blocked-save.yml, blocked-requests.json, reloaded.yml, title-result.json, result.json. Tidak membagikan log ber-ID akun/draft sebagai dokumentasi publik.
