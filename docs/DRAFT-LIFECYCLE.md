# Hapus draft dan buat ulang untuk uji defaults

Observasi 2026-10-25; pengguna meminta eksplisit hapus draft riset lama, catat proses, kemudian buat draft baru. Semua tindakan lewat UI Playwright; tidak ada Publish/distribusi, upload baru, perubahan profil atau penghapusan media sumber lokal.

## Hapus draft lama — berhasil

1. Buka All Releases `/user-portal/releases/manage/1`.
2. Identifikasi kartu berdasarkan judul riset lama, link Edit ber-ID yang sesuai, dan status `Draft · Album`. Daftar saat itu hanya satu rilis. ID disimpan dalam bukti privat, bukan dicocokkan dari posisi kartu saja.
3. Kartu `.release-grid-card` memiliki `.release-grid-card__actions button` berikon `fa-trash-alt`. Tombol tidak punya accessible name; scope selector ke kartu dan ID tepat. Jangan memilih tombol anonim global atau ikon issue.
4. Klik ikon menampilkan dialog: `Remove release` / `You can not revert this action`, tombol Close dan Remove.
5. Klik Remove sesuai izin pengguna, tunggu link Edit lama hilang.
6. Reload daftar: `No releases yet`. Penghapusan terverifikasi dari daftar setelah reload. Tidak mencoba membuka URL edit lama karena efek fallback belum diketahui.

Yang belum diketahui: apakah track/audio/artwork remote ikut terhapus, masih ada di library, atau bisa dipulihkan support. Pesan UI menyatakan irreversible; jangan menjanjikan undo. File audio/lirik sumber lokal tidak disentuh.

Implikasi kontrak: penghapusan bukan bagian retry/resume otomatis. Harus permintaan eksplisit, target akun+ID+judul+status Draft cocok, dan konfirmasi destruktif yang terpisah. Jangan gunakan jalur ini untuk takedown rilis published.

## Draft pengganti — berhasil

- Dari daftar kosong klik Create New Release.
- Quick Setup artist tidak muncul lagi. Wizard Select release type → Album → Continue → Name your release.
- Judul baru `RESEARCH ONLY - Profile Defaults - 2026-10-25`, lalu Create Release sekali.
- Tunggu setting up selesai dan URL `/uploader/edit/<new-id>`; ID baru berbeda dari draft lama.
- Tidak upload audio/artwork; tidak mengisi manual metadata lain.

## Defaults akun yang kini diverifikasi pada draft baru

Sesudah panel benar-benar terlihat, Primary Artist, Primary Genre, Language, Record Label Name, C-Line, P-Line dan tahun copyright terisi. Secondary Genre kosong. Nilai identitas hanya dalam capture privat; tidak hardcode sebagai default semua akun.

Tanggal rilis otomatis terisi dan berbeda dari draft lama. Jangan memakai jadwal otomatis sebagai tanggal final integrator tanpa konfirmasi.

Manual Stores=false dan manual territories=false. Additional Delivery: beberapa switch bawaan true (Content ID, Meta, SoundCloud Monetization, SoundExchange, Tracklib, Hook, serta LyricFind memiliki aria-checked true tetapi disabled karena belum ada lyrics). Udio=false. Ketersediaan/checked/consent bukan hal sama; lihat seluruh state efektif sebelum mutasi. Agen tidak mengubah switch layanan. Asal semua nilai ini dari Preferences vs default platform belum dipisahkan; yang terbukti adalah baseline draft baru pada akun ini.

Sisa issue di editor settled: Artwork dan Release Format. Daftar rilis sempat menunjukkan counter3 sedangkan editor2; counter ringkasan tidak boleh menjadi satu-satunya otoritas validasi.

## Save dan reopen

Klik Save Changes pada draft baru tanpa edit lanjutan membawa browser kembali ke Manage Releases. Tidak ditemukan tombol Save; menunggu tombol itu timeout. Berbeda dari uji media sebelumnya yang menampilkan dialog konfirmasi Save. Tidak mengulang submit atau menganggap timeout berarti gagal.

Daftar menunjukkan draft baru dengan status Draft · Album. Edit dibuka ulang; field Primary/Secondary Genre, Language, Record Label Name, C-Line dan P-Line sama persis dengan snapshot settled sebelum Save Changes. Ini membuktikan baseline persisted setelah create/save/navigate pada sesi ini, bukan memisahkan efek Create Release dan Save Changes secara kausal. Tidak ada konfirmasi dialog Save yang diklik dalam siklus baru ini.

State akhir browser: draft baru, Basic Information, tanpa media. Draft lama terhapus. Belum menguji writer defaults pada track baru karena tidak ada track di draft ini. Jangan mengasumsikan composer diwarisi berdasarkan baseline rilis saja.

## Jebakan observasi

- Setelah klik panel, ARIA dapat tetap merefleksikan panel lama selama transisi; query textbox hidden pada scope role menghasilkan hasil kosong. Pembacaan awal kosong dibuang sebagai belum settled, bukan fakta defaults kosong.
- Tunggu target field visible dan state stabil sebelum snapshot/read-back.
- Save harus ditangani menurut state aktual: konfirmasi, saving, navigasi daftar, atau error; jangan menunggu satu dialog secara buta.

Bukti privat: `.local/captures/draft-lifecycle/`: list-before.yml, delete-confirm.yml, deleted-reload.yml, new-basic.yml, new-defaults-settled.yml, new-reference.json, reopened.yml. Snapshot awal new-defaults.yml belum settled dan bukan baseline final. Tidak ada screenshot/login/cookie/password diambil dalam siklus ini.
