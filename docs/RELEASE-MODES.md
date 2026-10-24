# Matriks release type dan operasi uploader

Observasi akun nyata 2026-10-24 via Playwright CDP. Izin: eksplorasi empat mode dan draft riset; tanpa upload media/publish. Dokumen ini bukan kontrak API ataupun spesifikasi DSP.

## Draft dan batas mutasi

Setelah profil artist diselesaikan pengguna, dialog awal memiliki dua langkah:
1. Select release type: Album / EP / Single / Compilation, Continue.
2. Name your release: textbox, Back, Create Release (disabled bila judul kosong).

Dibuat SATU draft berjudul `RESEARCH ONLY - CLI UI Mapping - 2026-10-24`. Setelah Create Release, dialog `Setting up your release...` tampil dan URL berubah ke `/uploader/edit/<id>`. ID/path lengkap hanya di sesi/capture privat. Jangan mengulangi Create Release saat menunggu; ada risiko duplikasi. Keberadaan draft remote dan halaman edit teramati, tetapi persistensi pergantian field setelah reload belum diuji. Save Changes tidak ditekan; draft tidak dihapus.

## Matriks mode (satu draft, tanpa track)

| Calon nilai release_type | Label UI | Label judul | Artist level rilis | Harga album iTunes default yang ditampilkan |
|---|---|---|---|---|
| album | Album / 6+ tracks | Album name | Artist profil; Existing Artist, New Participant | Mini Album One $4.99 |
| ep | EP / 4–6 tracks | EP name | Sama seperti Album | Mini Album One $4.99 |
| single | Single / 1–3 tracks | Single name | Sama seperti Album | Digital 45 $1.99 |
| compilation | Compilation / Various artists | Compilation name | Various Artists otomatis; Existing Artist/New Participant tidak tampil | Back $7.99 |

- Semua mode menyediakan Basic Information → Artwork → Release Information → Manage Tracks.
- Klik sidebar bisa berpindah langkah meski field wajib/media belum lengkap; navigasi bukan bukti validasi lulus.
- Pergantian mode tidak menghapus judul dalam eksperimen. Compilation → Album mengembalikan artist profil yang semula dipilih.
- Default harga track terlihat Front $1.29 pada semua mode. Harga bukan janji penjualan/biaya distribusi.
- Album 6+ dan EP 4–6 beririsan; label tidak cukup untuk hardcode batas validator. Semua mode tanpa track tetap menampilkan issue Release Format.
- Parameter lowercase di tabel adalah USULAN schema lokal, bukan nilai wire Too Lost yang diamati.

## Artwork — sama pada empat mode

- Upload Artwork: JPG, PNG, TIFF. Teks UI: recommended 3000px, maximum 5000px, perfect square, under 36MB, RGB, tidak buram/border tidak rata, review manual sebelum publish.
- Minimum ukuran yang diterima belum diuji. Panduan publik menyebut minimum 3000, tetapi UI hanya berkata recommended; jangan menyamakan keduanya.
- Tombol Gemini / Generate with Google, DALL-E / Generate with OpenAI: tidak diklik, tidak ada request generasi/biaya diotorisasi.
- Apple Motion Art terpisah dari cover, ProRes untuk Apple Music; belum diuji.

## Release Information

- Release Date, original release date opsional, pre-order date opsional, waktu + zona waktu opsional.
- Field tanggal sudah berisi tanggal pada draft baru; jangan menganggapnya default universal atau jadwal yang disetujui integrator.
- Original date: tanggal tampilan untuk konten lama, jadwal live tetap Release Date menurut teks UI.
- Waktu/zona waktu menampilkan Select time zone dan Release Time. Tanpa ini, teks UI menyebut midnight per territory; teks ingest GMT+4 belum diverifikasi di DSP.
- Primary Genre, optional Secondary Genre, Language dan No lyrics / instrumental. Genre/bahasa profil otomatis mengisi draft pada akun ini, bukan default global.
- Record Label Name; Copyright Year/C-Line dan Year/P-Line. Label dan copyright kosong memunculkan issues.
- Stores default semua tersedia. Manual selection membuka ringkasan `479 of 479 stores included` dan Edit selection pada sesi ini; katalog dan jumlah dapat berubah. Daftar individual belum dipetakan.
- Territories default worldwide; manual selection menampilkan panel pemilihan wilayah. Daftar/semantik include-exclude belum diuji menyeluruh.
- Optional: version line, licensing type (Copyright / Creative commons), album pricing, track pricing, own UPC/EAN opsional (otherwise automatic menurut UI).
- Track pricing terlihat $0.69 Back, $0.99 Mid, $1.29 Front. Dropdown album hanya menampilkan sebagian daftar pada viewport; inventaris opsi tidak exhaustif. Query option global dapat mencakup menu tersembunyi sebelumnya, sehingga harus scope ke menu aktif.

## Additional Delivery — jangan diaktifkan otomatis

YouTube Content ID, Meta Rights Manager, SoundCloud Monetization, SoundExchange, Beatport, Traxsource, Tracklib, Hook, LyricFind, EVEN, Udio, Roblox, Managed Media.

- Content ID meminta 100% exclusive rights menurut UI.
- Beatport/Traxsource disabled dengan pesan genre/language incompatible pada konfigurasi sesi ini.
- LyricFind disabled karena belum ada track berlyrics; EVEN disabled karena akun belum terhubung.
- Udio berarti lisensi untuk generative AI training, BUKAN sekadar pilihan store biasa.
- Tidak satu pun switch Additional Delivery diaktifkan oleh agen. Kelayakan, hak, biaya, terms dan consent tiap layanan belum diperiksa.

## Manage Tracks dan preview

- Keempat mode tanpa audio: Upload tracks / browse audio, select from existing tracks (disabled pada state yang diamati).
- Bantuan sidebar menyebut WAV recommended; tipe WAV, MP3, M4A, AIFF, FLAC.
- Input file DOM yang ditemukan memiliki accept image/png,image/jpeg,application/pdf; belum terbukti terhubung ke tombol audio. Jangan memakai atribut itu sebagai whitelist audio.
- Belum membuka file picker atau memilih/upload file; belum memetakan track editor, progress, processing server, batas durasi/size/track, ordering, credits, ISRC, lyrics ataupun existing track.
- Preview Release bisa membuka preview draft kosong: type, title, artist, label/date/copyright placeholder, 0 songs. Ini bukan validasi kelengkapan/publish.
- Publish tidak diklik; enabled secara visual bukan bukti siap distribusi.

## Temuan teknis untuk automation

- ID input dinamis; utamakan role + accessible name dan scope dialog/main/menu aktif.
- Overlay onboarding menangkap klik sidebar. Tunggu dialog selesai, jangan force click atau menghapus overlay.
- Custom Vuetify switches: native `checked`/Playwright is_checked() tetap false walaupun aria-checked true dan panel terlihat.
- `.check()` gagal karena ripple/overlay; focus + Space membuka panel. Untuk pemulihan, baca aria-checked DAN pastikan panel hilang, bukan hanya native checked.
- Opsi original date, pre-order, timezone, stores dan territories dibuka untuk observasi, lalu seluruhnya dikembalikan aria-checked=false. Field Release Time hilang dan issue waktu hilang; issue akhir tinggal format, artwork, label, copyright.
- State akhir: Album, Basic Information, draft riset masih ada. Harga efektif setelah round-trip mode/persistensi reload belum diverifikasi terpisah.
- Capture ARIA privat: `.local/captures/mode-research/`. Berisi data akun; jangan commit/bagikan. Tidak ada network trace/cookie/password diambil.

## Dampak kontrak integrator (usulan, belum implementasi)

- `release_type`: album | ep | single | compilation; integrator memilih eksplisit, jangan selalu menebak dari jumlah track.
- `title` stabil terlepas dari label input per mode.
- Artist release dan artist track harus terpisah; Compilation punya perilaku khusus, jangan membuat artist bernama Various Artists otomatis di akun.
- Release date harus eksplisit; original/preorder/timezone bersifat opsional terstruktur.
- Artist IDs/mapping, genre/language, label/C/P, artwork, tracks dan rights perlu validasi dari bukti lanjutan sebelum finalisasi schema.
- Stores/territories dan additional deliveries jangan dicampur. Layanan hak/monetisasi/AI training wajib opt-in eksplisit.
- Update: pengguna kemudian mengizinkan media dari folder FlowStudio yang ditentukan serta artwork sintetis. Satu audio/artwork telah diuji sampai save/read-back; lihat MEDIA-DRAFT.md. Multi-track/ingest recovery masih belum diuji; lihat CONTRACT-PLAN.md. Jangan publish.
