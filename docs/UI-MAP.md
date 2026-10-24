# Too Lost UI map

Observasi: 2026-10-24, akun pengguna, Chrome profil khusus + Playwright CDP. Login manual berhasil dipakai kembali. Tidak ada password/cookie dibaca, login di-capture, atau upload/publish dilakukan. Draft riset kemudian dibuat dengan izin; lihat update terbaru.

## Update terbaru

Setup profil artist sudah diselesaikan pengguna. Satu draft riset dibuat dengan izin, empat release type dan empat panel uploader telah diamati. **Lihat docs/RELEASE-MODES.md untuk matriks terkini, pemulihan switch, batas bukti, dan state akhir.** Bagian penghalang Quick Setup di bawah adalah riwayat observasi awal, bukan penghalang saat ini.

## Navigasi yang sudah diverifikasi

| Halaman | Path | Temuan |
|---|---|---|
| Situs publik | / | Membuka profil yang sudah login tetap mendarat di situs publik; bukan bukti session expired. Ada tautan Login dan Dashboard. |
| Dashboard | /user-portal | Judul Dashboard - Too Lost; session aktif. Tautan Releases, Preferences, dan upload ke /uploader. |
| All Releases | /user-portal/releases/manage/1 | Judul User Portal - Manage Releases. Ada All Releases, New Release (tautan /uploader), dan tombol Create New Release. |

Menu dashboard yang terlihat: Releases, Wallet, Sales, Analytics, Reports, Insights, Audience, Royalty Splits; fitur perlindungan/marketing; Cover Song Licensing; AI Mastering; Settings, Preferences, Billing, Notifications, Support. Keberadaan menu tidak membuktikan fitur aktif/tersedia pada paket akun.

## Batas izin berikutnya

Pengguna mengizinkan membuka uploader dengan kemungkinan draft riset, tanpa upload atau publish. /uploader sudah dibuka. Belum mengisi metadata atau menekan Save Changes/Publish; apakah navigasi saja membuat draft remote belum terverifikasi.

## Uploader awal — bukti 2026-10-24

Capture privat: `.local/captures/uploader-initial/aria.yml` dan `viewport.png`. Tidak untuk commit/bagikan.

- Sidebar: Basic Information, Artwork, Release Information, Manage Tracks.
- Aksi global: Preview Release, Save Changes (disabled pada state awal), Publish (terlihat enabled, BELUM diklik; ini tidak membuktikan publish dapat berhasil).
- Basic Information: pilihan Album (6+ tracks), EP (4–6 tracks), Single (1–3 tracks), Compilation (Various artists); textbox berlabel Album name; Primary Artists dengan Existing Artist/New Participant; Continue.
- Label Album 6+ tracks berbeda dari cuplikan panduan publik yang menyebut 7+ atau durasi >=30 menit. EP juga mencakup 6; jangan menyimpulkan aturan DSP atau validator final dari label ini.
- Sidebar terlihat menampilkan 5 issues: Release Title, Artist Name, Release Format, Artwork, Label Name. Inventaris seluruh DOM sempat menemukan C & P Line juga, tetapi tidak terlihat dalam ARIA snapshot saat state berikutnya. Daftar issues dinamis, jangan hardcode jumlahnya.
- Banyak panel/kontrol sudah ada di DOM dalam keadaan tersembunyi. Kehadiran markup bukan bukti interaksi atau validasi berhasil.

### Penghalang: Quick Setup profil artist

Modal `Set up your artist profile` muncul di atas uploader dan memblokir interaksi sidebar. Field terlihat: Artist Name, Primary Genre, Language; Spotify Existing/New; Apple Music Existing/New; tombol Save & Continue. Tidak diisi/disimpan oleh agen.

Percobaan klik Artwork berhenti pada timeout 5 detik karena overlay menangkap pointer. Tidak memakai force click, menghapus overlay atau menjalankan handler lewat JavaScript. Belum memetakan langkah lanjutan secara interaktif. Pengguna perlu menyelesaikan profil sendiri, atau memberikan izin dan data profil yang eksplisit; izin draft tidak dianggap izin membuat/mengubah artist.

Batas audio/artwork, detail rilis, track editor, autosave dan draft persistence masih belum diverifikasi pada UI yang dapat dioperasikan.

## Catatan browser

Menutup jendela Chrome tidak selalu menghentikan proses macOS. Peralihan login ke observe memerlukan Quit Chrome (Cmd+Q); script menolak profile lock yang masih aktif dan tidak menghapus lock.

## Capture

Observasi awal hanya membaca URL/judul, tautan navigasi dan deskripsi kontrol. Tidak mengambil screenshot, body text akun, atau network trace. Tidak menyalin data pribadi/katalog ke dokumen ini.
