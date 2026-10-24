# Default profil dan perubahan manual pengguna

Update berikutnya: baseline pada draft pengganti sudah diuji; lihat DRAFT-LIFECYCLE.md. Pernyataan belum dibuat draft kedua di bawah adalah status historis observasi pertama, bukan status terkini.

Observasi 2026-10-24 setelah pengguna melengkapi draft riset. Tidak ada upload tambahan, Create Release baru, Save/Publish/distribusi dalam observasi ini. Mengunjungi tab editor dan kembali dengan Done dapat memicu sinkronisasi lokal aplikasi; efek server dari Done tidak dipisahkan lewat network trace.

## Fakta teramati

- Sidebar draft menampilkan hanya `1 issue`: Release Format / Add more tracks or change the format.
- Mode Album masih berisi satu track. Tidak menambah track, menggandakan audio, mengubah format atau mencoba Publish untuk memvalidasi batas minimal.
- Record Label Name, C-Line, P-Line, Primary Genre dan Language terisi. Nilai identitas tidak disalin ke dokumen ini.
- Writer Roles berisi satu full name dan dua role. Credits tambahan kosong; kedua bagian bukan field yang sama. Nama/role dipilih pengguna, bukan dibuat agen; validitas legal tidak diverifikasi.
- Lirik masih 1344 karakter. Belum mereview/menyetujui format lirik untuk distribusi.
- Manual Stores aktif; sejumlah Additional Delivery aktif, berbeda dari observasi awal agen. Tidak mengubah atau menganggap layanan aktif sebagai default profil. Terms/rights/AI-training consent belum diaudit.
- Switch Information urutan pertama, yang pada observasi sebelumnya dipetakan AI-assisted, sekarang aria-checked=false. Tiga switch lain juga false. Issue AI Documentation tidak tampil. Ini BUKAN bukti dokumentasi AI selesai: deklarasi AI-assisted berubah dari true menjadi false pada draft berisi audio hasil generate.
- Perubahan pengisian pengguna diamati pada UI saat ini; belum dilakukan Save+reload untuk memastikan seluruh perubahan manual terbaru persisted.

## Informasi dari pengguna vs bukti independen

Pengguna menjelaskan: setelah profil artist lengkap, release baru otomatis terisi data yang diperlukan selain detail rilis. Catat sebagai perilaku akun menurut pengguna.

Bukti sebelumnya memang menunjukkan artist primary, genre dan language diwarisi setelah setup. Label/C/P dahulu kosong pada draft riset, sekarang terisi setelah pengisian manual. Belum dibuat release kedua untuk menguji apakah label/C/P, writer dan pilihan layanan sekarang juga default profile.

Preferences dibuka read-only di tab tambahan, tetapi konten belum termuat lengkap ketika snapshot pertama diambil. Koneksi CDP kemudian terputus (ECONNREFUSED); tidak restart browser, membuat draft, membaca storage/cookie atau mengubah profil. Tidak ada klaim Preferences telah terpetakan.

## Implikasi integrator

- Pisahkan baseline dari akun, field manifest eksplisit, dan hasil read-back UI.
- Field manifest yang tidak diberikan tidak boleh otomatis mengosongkan field yang sudah terisi.
- Jangan menganggap field terisi berarti benar untuk tiap release; tampilkan ringkasan nilai efektif sebelum Save/Publish.
- Bedakan parameter required-by-integrator dari required-by-UI: beberapa field dapat dipenuhi baseline profil tetapi tetap perlu diverifikasi.
- Genre/bahasa, artist, label/C/P, writer, stores dan additional delivery jangan disamaratakan asalnya. Default yang berubah harus terdeteksi, bukan silently dipakai.
- AI-assisted, original/cover, explicit/clean, rights dan consent layanan tetap harus jujur/eksplisit. Hilangnya issue bukan bukti akurasi atau hak distribusi.
- Album/EP overlap pada label track count belum terselesaikan. Jangan hardcode minimal album hanya dari label6+; validasi jumlah/durasi perlu bukti lebih lanjut tanpa Publish.
- Semua riset tetap draft-only. Scope produk final hingga release tidak memperluas izin riset.
