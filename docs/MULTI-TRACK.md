# Uji dua track berbeda

Observasi 2026-10-25, atas izin pengguna untuk dua track pada draft pengganti. Tidak Publish/distribusi, tidak mengubah profile defaults, tidak menghapus track atau menggandakan audio.

## Fixture

Dua MP3 dari dua song berbeda di folder FlowStudio yang telah diizinkan: Terangnya Belum Pulang dan Sungai Teh Susu. Masing-masing tercatat take ready, file tersedia, snapshot source.lyrics.txt satu direktori, hash audio berbeda. MP3 dipakai agar uji antrean lebih ringan, bukan penetapan master final.

Urutan pemilihan: Terangnya Belum Pulang → Sungai Teh Susu. Ukuran sekitar5.1MB dan4.5MB. Path, take/song IDs dan SHA-256 hanya di `.local/captures/two-tracks/selection.json`. File sumber tidak diubah dan lirik tidak diupload pada uji ini.

## Multiple upload

- Target draft pengganti dicocokkan dari ID URL dan title; Manage Tracks awalnya kosong.
- Upload tracks → dialog → browse files. FileChooser.is_multiple() true.
- set_files dua path sekaligus menghasilkan 2 files selected, dua item dalam urutan pemilihan, Add more files, Remove file, Upload2 files.
- Klik Upload2 files sekali. Teks progress sempat menyatakan Uploading1 file sekaligus1 of2 files uploaded dan84%. Jumlah pada label tidak selalu jumlah total antrean.
- Tunggu daftar Edit track terlihat, lalu pastikan tepat dua baris hasil ingest; jangan menilai sukses dari persentase saja.

## Urutan hasil dan reorder

Hasil ingest pada uji ini TERBALIK: Sungai Teh Susu → Terangnya Belum Pulang. Penyebab urutan (durasi proses/penyortiran/bug) tidak diketahui; satu uji tidak menetapkan aturan sorting universal.

Manage Tracks memiliki `.track-item`, title, number, Edit, tombol remove anonim, selection button berlabel Select track, dan drag handle `.track-item__drag.drag-me`.

Drag handle baris kedua ke bagian atas baris pertama via mouse move/down/move/up berhasil mengembalikan urutan sesuai manifest uji. DOM tidak diubah dan handler internal tidak dipanggil. Locator structural ini berbasis UI sesi sekarang, bukan selector stabil yang dijamin platform. Reorder harus diverifikasi dengan read-back daftar, bukan hanya keberhasilan event mouse.

## Default per-track

Diperiksa kedua editor:
- Title otomatis berasal dari basename MP3, bukan display_title FlowStudio.
- Artist primary terisi (bukti ARIA privat).
- Writer Roles: satu textbox Full name sudah terisi, tombol Role menampilkan2 roles. Nama dan role default tidak diubah oleh agen. Identitas/otoritas hak belum divalidasi.
- Lyrics kosong0 karakter pada keduanya. File source.lyrics.txt lokal tidak otomatis dibaca uploader.
- AI-assisted aria-checked=false pada keduanya. Tidak diubah dalam eksperimen ini agar baseline teramati; karena sumber hasil generate, ini BUKAN deklarasi final yang direview untuk distribusi. Integrator tetap perlu parameter eksplisit/provenance check.
- Tidak mengarang credits/identitas atau menganggap tidak adanya issue sebagai bukti metadata benar.

## Save dan reopen

Setelah reorder: Save Changes → dialog Save → Save; menunggu Saving your release hilang, lalu buka daftar rilis dan Edit draft yang sama.

Kartu tetap Draft · Album. Manage Tracks setelah reopen menunjukkan tepat2 track, urutan Terangnya Belum Pulang → Sungai Teh Susu sesuai hasil drag. Assert jumlah dan kesamaan urutan lolos pada script observasi.

State akhir: draft pengganti, dua MP3, belum artwork, judul track filename, lyrics belum diisi dan AI-assisted defaultfalse. Tidak ada publish atau klaim release-ready. Format Album masih belum lengkap; tidak menambah6+ track hanya untuk menghapus issue.

## Dampak kontrak

- Input file chooser order tidak menjamin order hasil ingest. Integrator harus mengirim track_id lokal + urutan eksplisit dan uploader merekonsiliasi hasil sebelum reorder.
- Basename/hash mapping dua file unik membantu fixture ini, tetapi hash lokal bukan bukti hash remote. Pencocokan remote yang tahan filename duplikat/normalisasi belum dipetakan.
- Title, lyrics, AI, writer/artist perlu dibaca ulang, tidak diturunkan dari filename atau diasumsikan final dari defaults.
- Save harus beradaptasi terhadap dialog vs navigasi; kali ini dialog ada, berbeda uji baseline tanpa edit.
- Uji sukses ini tidak membuktikan resume aman setelah timeout/crash atau upload partial. Itu riset berikutnya dengan batas dan fixture yang disepakati.

Bukti privat `.local/captures/two-tracks/`: ingested.yml, track-*-information.yml, track-*-artists.yml, track-*-writers.yml, after-reorder.yml, list-saved.yml, reopened.yml, result.json, selection.json. Jangan commit/share capture identitas.
