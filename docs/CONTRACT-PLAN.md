# Kontrak integrator dan rencana automasi

Diperbarui: 2026-10-25. Status: catatan keputusan dan rancangan, bukan schema/CLI yang sudah diimplementasikan. Baca bersama RESEARCH.md dan bukti UI terkait.

Update review offline: schema manifest + hasil validate dan script validator stdlib kini tersedia, lihat OFFLINE-VALIDATION.md. Nama distribusi `toolost-uploader`, modul `toolost_uploader`, executable `toolost` disetujui; packaging offline kini tersedia, operasi akun belum dibuat. Untuk manifest upload normal `ai_assisted` wajib boolean (null/omitted invalid); unknown/null hanya untuk future inspect. `status` fase berikutnya menargetkan run-id, bukan draft-id pada contoh historis di bawah. Approval draft/publish, binding akun dan identity remote tetap proposal/blocker.

## Keputusan yang disepakati

- Python + Playwright, CLI terpisah untuk integrasi yt-to-flowmusic; kemungkinan distribusi PyPI. Belum ada izin publish paket.
- Produk final ditargetkan sampai release, tetapi riset saat ini maksimal upload dan simpan draft. Dilarang Publish/distribusi, termasuk menguji validasi lewat Publish.
- Release type menjadi parameter: album, ep, single, compilation. Ejaan lowercase adalah kontrak lokal usulan, bukan nilai API Too Lost terverifikasi.
- AI-assisted menjadi parameter per track, bukan default false global. Pengguna menyetujui parameterisasi setelah pembahasan issue dokumentasi.
- Default profil akun perlu dipertahankan bila integrator tidak mengirim override; nilai efektif tetap harus dibaca ulang dan direview.

## AI-assisted dan kode rekaman

- `ai_assisted`: true atau false jika dinyatakan eksplisit. Field tidak diberikan berarti belum ditentukan, bukan false. Cara serialisasi null vs omission masih perlu diputuskan.
- True: deklarasi diaktifkan; dokumentasi yang belum lengkap dilaporkan sebagai issue, tidak menghalangi penyimpanan draft bila UI mengizinkan. Penyelesaian AI Documentation belum terverifikasi; lihat AI-DOCUMENTATION.md.
- False: deklarasi integrator/pengguna, bukan fallback untuk menghilangkan validasi. Provenance generate AI yang bertentangan harus diberi peringatan dan direview; jangan diam-diam dimatikan.
- Perubahan deklarasi AI dapat memengaruhi kelayakan stores/additional delivery. Baca ulang state setelah perubahan.
- ISRC: identitas rekaman, opsional pada input bila distributor menyediakan kode. Rekaman yang sama yang sudah memiliki kode seharusnya mempertahankannya; jangan mengarang kode atau menjanjikan assignment sebelum verifikasi UI.
- ISWC (bukan ISRW): identitas komposisi; isi hanya bila telah diperoleh dari lembaga terkait. Jangan menyamakan dengan ISRC.
- UPC/EAN: identitas rilis. Field opsional dan pemberian otomatis ditampilkan UI; hasil assignment/persistence belum dipetakan.
- Kepemilikan kode bukan bukti hak distribusi atau izin komersial AI.

## Pemilihan profil — rancangan yang direkomendasikan

Update implementasi offline: helper internal `storage.profile` + checkpoint snapshot/cancel atomik sudah dibuat atas permintaan pengguna; lihat LOCAL-STATE.md. Lokasi macOS/Linux, permission dan lock POSIX ditetapkan untuk subset ini; Windows unsupported. Config account_fingerprint tetap null. Login/binding UI/remote resume dan command profil belum diimplementasikan. Rincian rancangan di bawah tetap konteks historis, bukan capability akun tersedia.

Pengguna meminta agar integrator bisa memilih profil. Direkomendasikan `--profile <nama-lokal>`; syntax/storage final belum ditetapkan dan belum dibuat multi-profile manager.

Bedakan:
1. Profil browser/login: sesi akun Too Lost lokal dalam user-data-dir Chrome khusus aplikasi.
2. Artist/participant dalam Too Lost: identitas metadata di dalam akun; satu profil browser tidak identik dengan satu artist.

Aturan yang perlu masuk kontrak:
- Integrator mengirim nama profil lokal, bukan password/cookie/browser storage. Manifest media tidak berisi kredensial.
- Login/CAPTCHA/2FA manual. Profil expired menghasilkan `login_required` (nama status usulan), bukan mengambil kredensial atau mem-bypass login.
- Satu proses penulis per profil; cegah upload paralel yang bersaing pada session/draft.
- Resume diikat pada profil, identitas akun yang sudah diverifikasi, dan ID draft remote. Jangan lanjut ke akun berbeda hanya karena nama profil sama.
- Verifikasi identitas akun/artist yang tampil sebelum mutasi; mismatch harus menghentikan proses.
- Lokasi storage produksi, validasi nama profil/path traversal, izin filesystem, pemulihan lock dan lifecycle profile belum difinalkan. `.local/chrome-profile` saat ini hanya profil riset.
- Daftar/status profil tidak perlu membuka/mengekspor cookie. Penghapusan profil perlu konfirmasi tersendiri; jangan membuat command penghapusan spekulatif.
- Genre, language, label/C/P, writer, stores dan layanan tambahan bukan otomatis konfigurasi lokal profil. Baca state akun dan bedakan default dari perubahan draft.

Contoh antarmuka usulan, BELUM tersedia:

```sh
toolost login --profile label-utama
toolost validate release.json --json
toolost upload release.json --profile label-utama --json
toolost status <draft-id> --profile label-utama --json
```

Nama executable/paket, flag, mode resume dan exit codes belum final. Jangan menjanjikan command publish selama riset.

## Kontrak input/output — usulan v1

Input:
- schema_version, ID rilis lokal stabil, release_type, title dan jadwal eksplisit.
- Artist level rilis terpisah dari artist track, terutama Compilation/Various Artists.
- Daftar track dengan ID lokal stabil dan urutan eksplisit; path audio final + hash, path lirik yang terikat pada take yang sama, artwork + hash.
- Metadata writer/credits dan deklarasi per track: original/cover, AI-assisted, explicit/clean/instrumental. Jangan menebak identitas legal atau hak dari nama artist.
- Genre/language, label/C/P, kode opsional, stores/territories/additional delivery menurut scope yang akhirnya disepakati.
- Kebijakan field: omitted mempertahankan baseline bila aman; nilai eksplisit override; cara clear harus dibedakan dari omitted. Deklarasi wajib belum ditentukan tidak boleh dianggap default negatif.
- Default profil tidak menggantikan persetujuan metadata final. Ringkasan nilai efektif menunjukkan asal inherited vs explicit dan perubahan otomatis UI.

Output:
- stdout JSON yang stabil; stderr progres/log yang disensor; exit code konsisten.
- ID/URL draft remote, hasil tiap track, status save dan read-back, issue UI, kebutuhan aksi manusia.
- Bedakan `draft_saved` dari `release_ready`; isu yang masih ada harus ikut dilaporkan meski save sukses.
- Bedakan gagal pasti, dibatalkan dan hasil remote belum diketahui. Jangan memberi status sukses hanya dari progress100% atau hilangnya modal.
- Nomor/nama exit code dan schema hasil belum final.

Resume:
- Rekonsiliasi draft/track remote sebelum retry. Jangan Create Release lagi hanya karena timeout.
- ID lokal, profil/akun, draft remote dan hash media membantu pencocokan; judul/nama file saja tidak cukup.
- Timeout, cancel, encoding dan session expiry memerlukan checkpoint; detil checkpoint/retry masih harus diuji.
- Interupsi lokal tidak membuktikan upload/server berhenti. Jangan otomatis menghapus/replace track sebagai pemulihan.

## Riset prioritas sebelum finalisasi kontrak

Update pelaksanaan: draft lama dihapus dengan izin dan draft baru dibuat; baseline rilis serta reopen sudah diverifikasi (DRAFT-LIFECYCLE.md). Poin2 di bawah selesai untuk artist/genre/language/label/C/P level rilis, tetapi writer/credits per track dan asal konfigurasi layanan masih belum diverifikasi. Multi-track/resume tetap belum dilakukan.

Update multi-track berikutnya: MULTI-TRACK.md memverifikasi dua track, writer default satu nama/dua role, titlefilename, lyricskosong, AIfalse. Hasil ingest membalik urutan pilihan; drag dan save/reopen berhasil. Poin3 kini selesai untuk dua audio unik, bukan bulk edit/duplicate filenames. Resume/failure recovery belum diuji, dan asal serta validitas legal writer default bukan hasil verifikasi ini.

Update resume tersimpan: RESUME.md memverifikasi restart browser terkontrol, session masih aktif, pencocokan ID/status/judul draft melalui daftar, count2 dan urutan track sama tanpa reupload. Ini menyelesaikan sebagian poin4; bukan partial-transfer recovery atau crash saat Save. Track ID tidak terlihat pada atribut/link baris yang diamati, sehingga pencocokan basename duplikat tetap unknown dan harus berhenti untuk review, bukan retry otomatis.

Update unsaved: UNSAVED-STATE.md menunjukkan perubahan judul release tanpa Save dan track title setelah Done tidak bertahan reload pada uji2.5detik. Checkpoint wajib memisahkan local staged edits dari Save dan persisted read-back; replay metadata tidak berarti replay upload. Tidak menggeneralisasi autosave seluruh field atau debounce lebih panjang.

Update Save failure: SAVE-FAILURE.md memverifikasi dialog error saat request mutasi diblokir sebelum network, guard dibersihkan dan baseline kembali lewat reload. Tidak menekan Try again; read-back wajib sebelum retry. Server telah menyimpan tetapi respons hilang, partial upload dan expired session tetap belum diuji; jangan menganggap error UI otomatis rollback.

Update remove track: TRACK-REMOVAL.md memverifikasi penghapusan satu track yang diizinkan melalui dialog nama target→Remove→Save→reopen. Baseline terkini satu track, bukan dua. Resume harus mendeteksi perubahan manual/destruktif dan tidak memulihkan track hilang lewat upload otomatis. Library deletion/undo serta persistensi Remove sebelum Save belum diuji.

1. **Pemilihan output FlowStudio**: mekanisme approval take/versi final, pasangan audio-lirik dan urutan lagu. `ready` tidak otomatis berarti dipilih pengguna. Integrator perlu menghasilkan manifest, bukan uploader membaca database internal sembarang.
2. **Default profil pada draft baru**: bandingkan artist, genre/language, label/C/P, writer dan pilihan layanan. Informasi pengguna bahwa defaults terisi dicatat, tetapi perlu bukti draft kedua. Komunikasikan pembuatan draft uji dan jangan ubah profil.
3. **Multi-track**: dua audio berbeda, urutan ingest vs manifest, reorder dan metadata per track. Jangan duplicate track atau upload6+ hanya untuk menghilangkan issue Album. Tentukan file sebelum upload.
4. **Save/reopen/resume**: pisahkan local state, Done, autosave, Save Changes→Save dan read-back setelah restart. Reproduksi hasil remote unknown tanpa retry buta.
5. **Kegagalan terbatas**: transfer/encoding gagal, pembatalan dan session expired memakai fixture/mocks offline dahulu. Uji live yang mengganggu koneksi/proses harus dikomunikasikan dan dibatasi.
6. **Metadata bersyarat**: writer role list, required composer, original/cover/licensing, code assignment, jadwal/zona waktu, lyrics formatting, explicit/clean. Jangan submit klaim hak palsu sebagai uji.
7. **Distribusi**: pisahkan stores, territories dan additional delivery; verifikasi read-back dan efek AI-assisted. Layanan hak/monetisasi/AI training harus opt-in sadar, bukan default blanket.
8. **Ketentuan automasi**: izin operasional/ToS belum diverifikasi; browser berhasil bukan bukti otomasi diizinkan.

Urutan disarankan: default satu draft baru → multi-track/order → save/reopen/resume → schema JSON v1 + tes offline. Ini rencana, bukan tes yang sudah dilakukan atau izin memperluas scope.

## Hal yang tidak perlu menghambat draft v1

- AI Documentation masih dapat ditandai unresolved/manual support, asalkan deklarasi jujur, issue terlihat dan tidak ada klaim siap publish.
- GUI/dashboard, Rust/hybrid runtime, cloud browser dan LLM per klik tidak diperlukan.
- Riset publikasi/QC/delivery final harus fase terpisah dengan persetujuan eksplisit; tidak dilakukan sekarang. Nanti gate publish harus terikat draft/akun dan konten tepat yang sudah direview, bukan flag boolean tanpa konteks.

## Referensi bukti

- RELEASE-MODES.md: empat mode dan kontrol bersyarat.
- MEDIA-DRAFT.md: satu audio/artwork, editor dan save/read-back nyata.
- PROFILE-DEFAULTS.md: pengisian manual pengguna vs default yang belum diverifikasi.
- AI-DOCUMENTATION.md: issue tanpa respons, efek AI dan state terakhir.
- BROWSER.md: dua tahap login/observasi, bukan kontrak profil produksi.
