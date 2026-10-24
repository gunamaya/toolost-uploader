# Uji media dan simpan draft

Observasi 2026-10-24. Pengguna mengizinkan artwork sintetis dan audio/lirik dari folder songs proyek FlowStudio yang ditentukan. Batas mutlak riset: simpan draft, TIDAK publish/distribusi.

## Aset uji dan provenance

- Satu track uji: Terangnya Belum Pulang, take berstatus ready dengan WAV dan source.lyrics.txt di direktori yang sama. Ini pemilihan fixture riset, bukan persetujuan master final.
- WAV asli stereo, PCM 16-bit, 48000 Hz, 179.52 detik, 34,473,958 byte. Tidak dikonversi/diedit.
- File UNVALIDATED dan take failed/cancelled tidak dipilih. Ready bukan bukti kepemilikan hak atau kualitas master.
- Artwork yang benar-benar diupload: PNG RGB 3000×3000, 39,787 byte, dibuat lokal secara deterministik dengan Python stdlib, tanpa teks/logo. Gambar alternatif dari image generator dibuat terpisah, TIDAK mengganti fixture upload.
- Path absolut dan SHA-256 audio/lirik/artwork hanya di `.local/fixtures/source-selection.json`; jangan commit atau bagikan. File sumber tidak diubah. Lirik snapshot 1344 karakter; jangan salin isi ke docs publik.

## Alur artwork

1. Artwork → Upload Artwork membuka dialog Upload artwork; bukan langsung file chooser.
2. browse files membuka file chooser; pilih satu fixture PNG.
3. Upload/encoding berjalan otomatis setelah pemilihan artwork pada uji ini. Progress 100% masih menunjukkan Encoding; jangan anggap selesai.
4. Setelah encoding selesai, Uploaded/Artwork selected dan Replace/Remove tampil; issue Artwork hilang.

Konflik UI: sidebar menyebut minimum 3000×3000; panel guideline recommended 3000/max5000/under36MB; dialog upload menyebut square min1500/max35MB. Fixture3000 diterima. Batas bawah/atas sebenarnya belum diuji; gunakan validasi konservatif dan laporkan konflik, bukan menebak kontrak backend.

## Alur audio

1. Manage Tracks → Upload tracks membuka dialog.
2. browse files → pilih WAV → 1 file selected, nama/size, Add more files, Remove file, Upload 1 file.
3. Upload 1 file memulai transfer; progress 39% diamati. Tunggu encoding/server selesai, jangan submit ulang.
4. Sesudah selesai, track muncul di daftar; judul awal berasal dari filename (bukan judul dari proyek).
5. Edit membuka editor track; duration tampil 2:59 setelah player termuat. Format48kHz diterima untuk fixture ini, bukan bukti semua kombinasi format diterima.

## Track editor

- Information: Track name, Version Line; Original work/Cover song; AI-assisted content; TikTok custom preview start; Language/instrumental; Assign ISRC/ISWC switches. Default Original work diamati, bukan klaim hak yang diverifikasi.
- Participants: Artist Roles, Writer Roles, Credits; artist primary diwarisi dari rilis. Dua issue track mengarah ke Writer Roles: role harus dipilih setiap writer dan composer wajib. Tidak mengarang nama composer/publisher.
- Audio: upload Instrumental, Dolby Atmos, Apple Digital Master; Mastering house email, upload ADM disabled tanpa email valid. Tidak diuji upload alternatif.
- Lyrics: Contains explicit content, Clean version, textbox Lyrics. Snapshot dari take dimasukkan persis; belum dibersihkan dari section markers/instruksi, sehingga bukan lirik siap distribusi yang disetujui.
- Tab dapat memiliki animasi/panel lama masih ada sesaat dalam ARIA; tunggu settle dan scope kontrol dengan benar.
- Judul diubah menjadi judul sumber; AI-assisted diaktifkan karena sumber hasil generate. Verifikasi aria-checked=true. Ini menambahkan issue AI Documentation di level rilis. Detail dokumen/terms belum dieksplorasi.
- Explicit/Clean tidak diubah dari default; konten belum direview untuk deklarasi final.

## Save dan persistence

1. Done kembali ke daftar track dan judul baru terlihat.
2. Save Changes membuka konfirmasi: Cancel / Save.
3. Save menampilkan Saving your release. Reload kemudian berhasil memuat ulang state remote.
4. Setelah reload diverifikasi: tepat satu track muncul, judul Terangnya Belum Pulang tersimpan, artwork tetap terpasang, AI-assisted aria-checked=true, Lyrics input identik dengan snapshot lokal (1344 karakter).

State draft riset tetap Album dengan satu track. Issue saat save: Track Metadata, Release Format, AI Documentation, Label Name, C & P Line. Draft parsial tersimpan meski ada issue. Tidak mengisi field hak/credit palsu. Tidak menekan Publish, tidak mencoba validasi melalui Publish, tidak melakukan distribusi.

## Sisa riset

- AI documentation schema dan evidensi yang dibutuhkan.
- Participant roles/credits dan persyaratan identitas legal.
- ISRC/ISWC/manual UPC semantics, per-track AI details, cover licensing.
- Multi-track reorder/selection/bulk edit, kelayakan format Album dan jumlah/durasi; tidak mengunggah 6+ lagu hanya untuk menghilangkan issue.
- Penanganan transfer gagal/encoding lambat/cancel/session expiry tanpa duplicate.
- Label/C/P, jadwal final dan hak distribusi perlu data/konfirmasi pengguna sebelum release sungguhan.

Akses privat riset: `.local/captures/media-research/`. Tidak ada test publikasi atau klaim siap rilis.
