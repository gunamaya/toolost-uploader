# Detail task Toolost Uploader

Status/prioritas/dependency/klaim terkini mengikuti [current index](../ANTRIAN-PEKERJAAN-UTAMA.md). Dokumen ini menyimpan scope dan acceptance, bukan antrean kedua. Baca section task terkait saja.

## GOV-01 — Adopsi tata kerja task

- **Sumber:** user meminta membaca bagaimana task yt-to-flowmusic direncanakan, diantrekan, dikerjakan dan diselesaikan, lalu mengadopsinya di repo ini.
- **Masuk:** current index canonical, detail task, checkpoint history append-only, claim/ownership, prioritas/dependency, acceptance/verifier, handoff dan aturan done; hubungkan ke AGENTS/README/panduan lanjut.
- **Keluar:** queue runtime, scheduler, database baru, dependency baru, perubahan executor/CLI produk, perubahan repo sumber, browser/live, upload/draft baru, commit/push.
- **Acceptance:** satu sumber current state; detail dan history terpisah; task baru wajib terdaftar sebelum edit; claim berisi baseline/files/tests/stop; completion punya evidence dan batas; maksimal lima checkpoint ringkas; panduan lanjut tidak membuat antrean tandingan; izin dan data privat tetap terlindungi.
- **Verifier:** baca/diff dokumen, cek link relatif file lokal, `python3 -m unittest discover -s tests -q`, `git diff --check`. Tes suite hanya regresi baseline karena runtime tidak berubah.
- **Stop:** ownership/diff tidak dikenal, interpretasi perlu perubahan runtime atau live → checkpoint dan konfirmasi scope.

## REC-01 — Recovery executor offline

- **Sumber:** instruksi implementasi sesudah 74a24b2; kode terakhir 684acd6.
- **Scope selesai:** journal v2, guard identity/target, duplicate intent, amendment immutable, recovery debugging dinonaktifkan dan reconciliation readback-only; [LIVE-DRAFT](../LIVE-DRAFT.md).
- **Acceptance:** tes offline mismatch/checkpoint, preflight identity, duplicate create/upload/Save, amendment audit, unknown/reconciliation, account/session berubah.
- **Evidence:** CP-001 merujuk laporan suite 154 tes, 2 skip, py_compile/diff check; bukan bukti live baru. Smoke sukses 74a24b2 tetap historis, tidak diulang.
- **Tidak termasuk:** resume produksi, publish/distribusi, rights/artist/services/AI Documentation otomatis, build/install opt-in terbaru.

## CLI-01 — Review subset draft CLI dan integrator

- **Sumber:** target CLI terpisah untuk yt-to-flowmusic; kontrak existing [CONTRACT-V1](../CONTRACT-V1.md), [CONTRACT-PLAN](../CONTRACT-PLAN.md), implementasi [LIVE-DRAFT](../LIVE-DRAFT.md).
- **Masuk:** review perbedaan CLI `validate`, script smoke draft, hasil JSON/exit code, field didukung dan gap integrator. Usulkan satu slice produk terkecil untuk keputusan user.
- **Keluar:** implementasi command baru, modifikasi integrator, queue runtime, resume/publish, live atau instalasi. Task ini review/proposal saja.
- **Acceptance:** tabel implemented/proposal/unsupported akurat; rekomendasi menyebut input/output/field/izin/tes yang dibutuhkan; tidak mengklaim command tersedia sebelum implementasi; tidak mengulang fake framework atau smoke sukses.
- **Verifier:** inspeksi kode/kontrak/help offline dan referensi exact file; implementasi berikutnya membutuhkan scope task baru/child dan keputusan user.
- **Hasil:** dokumen review komprehensif di [CLI-REVIEW](../CLI-REVIEW.md) memetakan implemented vs proposed vs unsupported, perbandingan manifest validator vs live draft, format output/exit codes, gap integrator yt-to-flowmusic, dan usulan slice terkecil `CLI-02` (subcommand `upload-draft` Single draft-only).

## CLI-02 — Subcommand CLI toolost upload --draft-only untuk Album (multi-track)

- **Sumber:** keputusan pengguna memilih penamaan Opsi B (`toolost upload --draft-only`) dan cakupan rilis **Album** (multi-track).
- **Masuk:**
  1. Subcommand `upload` di `toolost_uploader/cli.py` dengan flag wajib `--draft-only`, `--profile <alias>`, optional `--json`, `--expected-account`, `--cdp`, `--approve-draft`, `--accept-ui-date`. Menolak upload tanpa `--draft-only` (karena publish/distribusi dilarang keras selama riset).
  2. Dukungan tipe rilis `album` selain `single` di `toolost_uploader/live_draft.py`:
     - Modal Select release type: memilih button Album (`Album 6+ tracks`) saat `release_type == 'album'`.
     - Multi-track upload: mengizinkan multiple tracks (`len(tracks) >= 1`), multi-file upload di file chooser.
     - Per-track metadata: mengedit judul track independen dan AI toggle untuk tiap track.
     - Reorder tracks sesuai urutan manifest bila urutan ingest berbeda.
     - Readback Album: memeriksa `Album name` (pada Single adalah `Single name`), jumlah track, judul tiap track, dan status AI.
  3. Output JSON murni ke stdout bila `--json`, exit code deterministik: 0 (sukses draft subset), 2 (invalid input/argumen), 4 (reconciliation required), 5 (OS error).
  4. Unit test offline komprehensif menggunakan mock Playwright di `tests/test_cli.py` dan `tests/test_live_draft.py`.
- **Keluar:** publish/distribusi (PUB-01 tetap deferred), resume otomatis mutasi gagal (RES-01 tetap deferred), mutasi profil/artist baru, penerapan tanggal ke UI picker (tetap mewarisi kalender UI default dengan flag opt-in), eksekusi browser/akun live.
- **Acceptance:** CLI `toolost upload --help` tersedia; perintah `upload` tanpa `--draft-only` ditolak; alur draft Album multi-track tervalidasi offline dengan mock Playwright; seluruh test suite lolos regresi; `git diff --check` bersih.
- **Verifier:** `python3 -m unittest discover -s tests -q`, `python3 -m toolost_uploader upload --help`, `git diff --check`.
- **Hasil:** Subcommand `toolost upload --draft-only` terpasang di CLI; `live_draft.py` mendukung rilis Album multi-track lengkap dengan file chooser multi-file, editor metadata per-track, dan readback `Album name`; 161 tes unit offline lolos regresi.

## RES-01 — Resume mutasi produksi (superseded)

- **Sumber:** evaluasi pasca CLI-02 & LIVE-02; keputusan eksplisit pengguna 2026-10-26.
- **Alasan penutupan:**
  1. Eksekusi alur penuh live Playwright pembuatan draft Album multi-track dari nol terbukti sangat cepat (~50 detik total), sehingga resume parsial tidak memberikan nilai tambah signifikan.
  2. Retry/resume mutasi di tengah jalan (partial upload) berisiko tinggi memicu duplikasi track dan pergeseran urutan di UI Too Lost.
  3. Mekanisme rekonsiliasi pasca-Save (`--reconcile-readback-only`) dan proteksi idempotensi fail-stop via journal v2 sudah tersedia dan jauh lebih aman.
- **Status:** `superseded`. Tidak ada kode mutasi resume tambahan yang akan dibangun.

## LIVE-02 — Verifikasi live Playwright Album multi-track (done)

- **Sumber:** keputusan pengguna menguji rilis Album multi-track dengan subcommand CLI `toolost upload --draft-only` pada akun pengguna.
- **Masuk:**
  1. Eksekusi satu alur penuh Playwright draft-only Album multi-track via loopback CDP (port 9437).
  2. Preflight identitas akun `/api/auth/me` cocok dengan `--expected-account`.
  3. Pembuatan rilis tipe Album, pengisian judul rilis, upload artwork, upload multi-file audio tracks, pengaturan urutan track (drag reorder), pengisian metadata judul track dan toggle AI per-track.
  4. Penyimpanan draft (Save Changes) sekali dan konfirmasi Too Lost.
  5. Reopen draft via URL `/uploader/edit/<id>` dan readback verifikasi subset (Album name, artwork, jumlah track, nama track, dan AI status).
  6. Pelaporan progres real-time ke stderr dengan flag `-v, --verbose`.
- **Keluar:** aksi Publish atau distribusi (DILARANG KERAS), mutasi profile/artist baru, penerapan tanggal rilis spesifik di luar kalender default UI.
- **Acceptance:** seluruh langkah dari preflight hingga readback subset berhasil diselesaikan tanpa intervensi manual; exit code 0; JSON output berstatus `draft_saved_subset`; tidak ada klik Publish; seluruh test suite offline 100% lulus.
- **Verifier:** eksekusi live Playwright CDP exit 0; `python3 -m unittest discover -s tests -q`; `git diff --check`.
- **Hasil:** Selesai (`done`, [CP-011](CHECKPOINT-HISTORY.md#cp-011--selesai-live-02-verifikasi-live-playwright-draft-album-multi-track)). Rilis Album live terbuat (draft ID `2004317`), artwork dan 2 tracks MP3 terunggah serta ter-encode, metadata dan AI status terisi, Save Changes berhasil, dan readback verifikasi subset 100% cocok. Exit code 0.

## ENV-01 — Subcommand setup, check (readiness), dan auto-bootup Chrome CDP (done)

- **Sumber:** masukan dan persetujuan pengguna 2026-10-26: "perlu step setup dan check readyness dulu, dan bootup chrome masuk ke verbose bila diperlukan".
- **Masuk:**
  1. Modul pendukung browser `toolost_uploader/browser.py`:
     - Deteksi Google Chrome binary lintas platform (macOS/Linux/Windows).
     - Resolusi path direktori profil browser dan pembersihan stale lock PID.
     - Pengecekan ketersediaan port CDP loopback (HTTP `/json/version`).
     - Peluncuran proses Chrome (mode setup manual tanpa debugging, atau mode observe/CDP di latar belakang).
  2. Subcommand `toolost setup`:
     - Membuka Chrome biasa dengan profil yang ditentukan ke `https://toolost.com/login` untuk login manual operator.
     - Menunggu proses browser ditutup operator, memastikan profil siap.
  3. Subcommand `toolost check`:
     - Diagnosa kesiapan lingkungan: Chrome binary, profil, port CDP, dan pengecekan sesi auth `/api/auth/me` terhadap `--expected-account`.
     - Opsi `--auto-bootup` (opsional): menyalakan Chrome di port CDP bila belum berjalan.
     - Output human & JSON murni (`--json`), exit codes: 0 (ready), 2 (login_required / not_ready / mismatch), 5 (OS error).
  4. Auto-bootup pada `toolost upload`:
     - Bila port CDP belum aktif saat upload dijalankan, uploader memanggil auto-bootup Chrome CDP secara mulus.
     - Pelaporan log proses bootup dialirkan ke stderr via mode verbose `[toolost] ...`.
  5. Pengujian offline komprehensif menggunakan mock subprocess dan network di `tests/test_browser.py` dan `tests/test_cli.py`.
- **Keluar:** bypass autentikasi / CAPTCHA otomatis (tetap manual login), pembacaan cookie/password mentah dari file profil Chrome, modifikasi Chrome harian pengguna.
- **Acceptance:** `toolost setup --help` dan `toolost check --help` tersedia; `toolost check` menghasilkan JSON readiness deterministik; auto-bootup CDP terhubung dan memancarkan verbose log ke stderr; seluruh test suite offline 100% lulus; `git diff --check` bersih.
- **Verifier:** `python3 -m unittest discover -s tests -q`, CLI help & check offline tests, `git diff --check`.
- **Hasil:** Selesai (`done`, [CP-013](CHECKPOINT-HISTORY.md#cp-013--selesai-env-01-subcommand-setup-check-readiness-dan-auto-bootup-cdp)). Subcommand `setup`, `check`, dan auto-bootup pada `upload` terimplementasi dan teruji live & offline. 171 tes lulus, 2 skipped; `git diff --check` bersih.

## INT-01 — Rencana & spesifikasi adapter integrasi subprocess yt-to-flowmusic (ready)

- **Sumber:** arahan pengguna untuk membuat rencana integrasi uploader ke repo `yt-to-flowmusic`.
- **Masuk:**
  1. Spesifikasi adapter klien `TooLostClient` di `yt-to-flowmusic` berbasis `ProcessRunner`.
  2. Pemetaan model rilis Album/Track dari `production/album_designer.py` dan `production/workspace_cover.py` ke format manifest JSON `toolost-uploader` (schema v1).
  3. Penanganan eksekusi subprocess CLI (`toolost upload <manifest> --draft-only ... --json`).
  4. Penguraian output JSON, penanganan exit code (0, 2, 4, 5), logging progres, dan penyimpanan `draft_id` rilis pada workspace/state `yt-to-flowmusic`.
- **Keluar:** perubahan langsung ke publish/distribusi tanpa persetujuan; pengubahan binary pihak ketiga.
- **Acceptance:** dokumen rencana integrasi komprehensif tersedia di `docs/INTEGRATION-PLAN.md` mencakup arsitektur, pemetaan data, kontrak subprocess, error handling, dan tahapan implementasi bertahap.
- **Verifier:** review offline dokumen rencana integrasi.

## PKG-01 — Persiapan packaging, metadata, lisensi, sanitasi sdist/wheel, dan rilis PyPI (done)

- **Sumber:** permintaan pengguna 2026-10-26: "susun cli --help dan buat rencana packaging buat di up ke PyPI".
- **Masuk:**
  1. Penyusunan dokumen rencana packaging komprehensif di `docs/PACKAGING-PLAN.md`.
  2. Penataan metadata rilis di `pyproject.toml` (authors, license, keywords, project URLs, deskripsi).
  3. Pemindahan dependency `playwright` ke core dependencies agar paket siap pakai saat di-install pengguna.
  4. Pembuatan berkas `LICENSE` (MIT) dan `MANIFEST.in` untuk sanitasi sdist/wheel (mencegah folder privat `.local/`, fixture, dan testing masuk archive).
  5. Pengujian lokal build wheel & sdist via `python -m build`, verifikasi `twine check`, dan uji instalasi di virtualenv bersih.
  6. Dry-run publikasi ke TestPyPI sebelum rilis resmi ke PyPI produksi.
- **Keluar:** publish PyPI tanpa izin pengguna eksplisit; pengunggahan berkas kredensial/capture privat.
- **Acceptance:** dokumen `docs/PACKAGING-PLAN.md` tersedia; `pyproject.toml` valid; build sdist & wheel terisolasi; verifikasi twine lolos; upload PyPI hanya dieksekusi dengan izin pengguna terpisah.
- **Verifier:** `python3 -m unittest discover -s tests -q`, `git diff --check`, build sanitasi offline.
- **Hasil:** Selesai (`done`, [CP-014](CHECKPOINT-HISTORY.md#cp-014--selesai-pkg-01-metadata-lisensi-mit-sanitasi-manifest-build--twine-verification)). Berkas `LICENSE` dibuat, `MANIFEST.in` dan `pyproject.toml` diperbarui ke versi 0.1.0 berlisensi MIT. Wheel & sdist berhasil di-build tanpa warning deprecation, lolos `twine check` 100%, serta lulus uji instalasi & eksekusi clean-venv di `test_packaging.py`.

## LYR-01 — Dukungan tab Lyrics di Playwright live executor (done)

- **Sumber:** permintaan pengguna 2026-10-26: "ya implementasikan LYR-01".
- **Masuk:**
  1. Mengizinkan field opsional `lyrics` pada track di `toolost_uploader/live_draft.py`.
  2. Penanganan pembacaan berkas lirik teks UTF-8 lokal berdasarkan referensi `track['lyrics']['path']`.
  3. Navigasi ke tab `Lyrics` pada modal track editor Too Lost (`page.get_by_role('button', name='Lyrics', exact=True)`).
  4. Pengisian konten teks lirik ke textbox `Lyrics` (`page.get_by_role('textbox', name='Lyrics', exact=True)`).
  5. Readback verifikasi teks lirik pada pembukaan kembali track editor pasca-Save atau reopen draft.
  6. Unit testing mock Playwright di `tests/test_live_draft.py` untuk alur sukses dan penanganan mismatch.
- **Keluar:** otomatisasi pembersihan section markers (ditangani oleh penyedia lirik), manipulasi switch explicit/clean tanpa deklarasi.
- **Acceptance:** Manifest dengan field `lyrics` diterima dan dijalankan di live executor; teks lirik terisi ke UI Too Lost; verifikasi readback mencocokkan teks lirik; seluruh test suite offline 100% lulus; `git diff --check` bersih.
- **Verifier:** `python3 -m unittest discover -s tests -q`, `git diff --check`.
- **Hasil:** Selesai (`done`, [CP-018](CHECKPOINT-HISTORY.md#cp-018--selesai-lyr-01-otomasi-tab-lyrics-playwright--live-verification-profil-aidoto)). Otomasi tab Lyrics terimplementasi dan teruji live dengan profil `aidoto` (draft ID `2009368`), mengisi lirik 2 lagu dan lulus verifikasi readback 100%. 173 unit tests offline lulus.

## TAB-01 — Optimalisasi tab browser CDP: reuse tab aktif & tutup tab redundan (done)

- **Sumber:** Permintaan pengguna 2026-10-26: "untuk boot up jangan selalu open new tab, periksa dulu ada tab yang aktif gak, kalau ada pakai tab yang aktif, jika ada banyak tab pilih salah satu lalu tutup tab lainnya, ini menghemat memory".
- **Masuk:**
  1. Helper `acquire_active_page(browser, domain="toolost.com", default_url=None, log=None) -> Page` di `toolost_uploader/browser.py`:
     - Memeriksa seluruh tab yang masih terbuka di semua context browser.
     - Jika ada tab yang sudah terbuka:
       - Memprioritaskan tab yang URL-nya mengandung domain target (`toolost.com`).
       - Memilih salah satu tab tersebut sebagai tab target aktif.
       - Menutup seluruh tab terbuka lainnya (`page.close()`) untuk menghemat konsumsi memori.
     - Jika tidak ada tab terbuka sama sekali:
       - Membuka tab baru (`context.new_page()`) dan menavigasikan ke `default_url` bila diberikan.
  2. Penerapan di `toolost_uploader/browser.py` (`check_auth_identity`): menggunakan `acquire_active_page` agar tab aktif di-reuse dan tab lain ditutup.
  3. Penerapan di `toolost_uploader/live_draft.py` (`execute`): mengganti batasan kaku `len(pages) != 1` (yang memicu error `ambiguous_browser_target`) dengan `acquire_active_page`, sehingga jika ada banyak tab Too Lost atau tab lain yang aktif, satu tab dipilih dan tab redundan ditutup secara otomatis untuk efisiensi memori.
  4. Pengujian unit offline di `tests/test_browser.py` dan `tests/test_live_recovery.py`.
- **Keluar:** Memodifikasi proses launch OS Chrome di luar parameter CDP standar.
- **Acceptance:**
  - Browser CDP tidak membuka tab baru jika tab aktif sudah tersedia.
  - Tab berlebih ditutup (`page.close()`) dan menyisakan satu tab aktif.
  - Menghindari kegagalan `ambiguous_browser_target` saat terdapat lebih dari 1 tab Too Lost aktif.
  - Seluruh test suite offline lulus regresi; `git diff --check` bersih.
- **Verifier:** `python3 -m unittest discover -s tests -q`, `git diff --check`.
- **Hasil:** Selesai (`done`, [CP-019](CHECKPOINT-HISTORY.md#cp-019--selesai-tab-01-optimalisasi-manajemen-tab-browser-cdp-reuse-tab-aktif--tutup-tab-redundan)). Helper `acquire_active_page` terpasang di `browser.py` dan `live_draft.py`, 5 unit test baru memvalidasi skenario tab tunggal, multi-tab redundan, non-domain tab reuse, dan fallback new_page. Verifikasi live pada profil `aidoto` membuktikan pembersihan otomatis tab ekstra menjadi 1 tab aktif. 178 unit tests offline lulus.

## CDP-02 — Dukungan unggah berkas audio besar (>50MB) via is_local di CDP (done)

- **Sumber:** Laporan error pengguna: `FileChooser.set_files: Cannot transfer files larger than 50Mb to a browser not co-located with the server` saat mengunggah berkas audio nyata.
- **Masuk:**
  1. Helper `is_local_endpoint(endpoint: str) -> bool` di `toolost_uploader/browser.py` untuk mendeteksi apakah endpoint CDP berjalan di host loopback lokal (`127.0.0.1`, `localhost`, `::1`).
  2. Penggunaan flag `is_local=is_local_endpoint(endpoint)` pada pemanggilan `p.chromium.connect_over_cdp(...)` di:
     - `toolost_uploader/live_draft.py` (`execute`)
     - `toolost_uploader/browser.py` (`check_auth_identity`)
  3. Memungkinkan Chromium membaca berkas audio lokal langsung via path OS (`DOM.setFileInputFiles`) alih-alih mentransfer buffer Base64 lewat WebSocket, sehingga batas 50MB Playwright terangkat sepenuhnya.
  4. Unit test offline di `tests/test_browser.py` dan regresi test suite.
  5. Version bump ke `0.1.3` dan rilis baru ke PyPI.
- **Keluar:** Pengunggahan ke remote host non-lokal di luar subnet loopback (tetap mematuhi limit keamanan Playwright).
- **Acceptance:**
  - `is_local=True` diaktifkan otomatis saat endpoint adalah IP loopback lokal (`127.0.0.1`, `localhost`).
  - Berkas audio besar (>50MB) tidak lagi memicu error `Cannot transfer files larger than 50Mb`.
  - Seluruh unit tests offline 100% lulus; `git diff --check` bersih.
- **Verifier:** `python3 -m unittest discover -s tests -q`, `git diff --check`.
- **Hasil:** Selesai (`done`, [CP-021](CHECKPOINT-HISTORY.md#cp-021--selesai-cdp-02--rilis-013-dukungan-unggah-berkas-audio-besar-50mb-via-is_local-di-cdp)). `is_local_endpoint` diterapkan pada `connect_over_cdp`, lolos uji upload 60MB live CDP, 179 unit tests offline lulus, paket `toolost-uploader==0.1.3` terbit di PyPI dan diverifikasi di clean-venv.

## FIN-01 — Finalisasi step pasca-readback: Done track terakhir, Save Changes, & kembali ke portal (done)

- **Sumber:** Feedback pengguna 2026-10-26: "sudah sukses upload, sayangnya di step terakhir setelah verifikasi track tidak click done, save changes dan kembali ke https://toolost.com/user-portal/releases/manage/1. segera perbaiki".
- **Masuk:**
  1. Di `toolost_uploader/live_draft.py` (`readback`):
     - Memastikan tombol `Done` SELALU diklik pada setiap track, termasuk track terakhir (`i == track_count - 1`), sehingga modal track editor tertutup secara rapi.
     - Menyimpan perubahan (`Save Changes`) pasca-verifikasi readback jika tombol `Save Changes` terlihat dan aktif.
     - Melakukan navigasi kembali ke `https://toolost.com/user-portal/releases/manage/1` dan menunggu hingga tombol `Create New Release` terlihat.
  2. Pengujian unit offline di `tests/test_live_draft.py`.
  3. Version bump ke `0.1.4` dan rilis baru ke PyPI.
- **Keluar:** Membuka draft lain, menghapus draft, atau memicu publish distribusi.
- **Acceptance:**
  - Tombol `Done` selalu diklik untuk track terakhir dalam readback.
  - Alur `Save Changes` dan navigasi kembali ke `https://toolost.com/user-portal/releases/manage/1` terpanggil setelah readback selesai.
  - Seluruh test suite offline 100% lulus; `git diff --check` bersih.
- **Verifier:** `python3 -m unittest discover -s tests -q`, `git diff --check`.
- **Hasil:** Selesai (`done`, [CP-022](CHECKPOINT-HISTORY.md#cp-022--selesai-fin-01--rilis-014-finalisasi-step-pasca-readback-done-track-terakhir-save-changes--kembali-ke-portal)). Tombol Done track terakhir selalu diklik, Save Changes dipicu pasca-readback, navigasi kembali ke portal releases terpasang, unit test memvalidasi 100%, dan versi 0.1.4 live di PyPI.

## UPD-01 — Fitur update komprehensif metadata & append track ke draft existing (done)

- **Sumber:** Permintaan pengguna 2026-10-26: "tambahin update aja kali ya?? jadi gak cuman append doang, tapi update juga", "kalau judul album/release, gambar juga diganti masukkin juga ke update dong", "tanggal release juga, pokokknya kalau dari manifest terdeteksi ada perubahan ikuti yang terbaru".
- **Masuk:**
  1. CLI: Menambahkan argumen `--update` dan `--append` pada subcommand `upload` di `toolost_uploader/cli.py`.
  2. Storage: Memperluas `update_checkpoint` di `toolost_uploader/storage.py`:
     - Memvalidasi kontinuitas dan melarang penghapusan track atau penggantian audio track lama.
     - Mengizinkan pembaruan judul rilis, tanggal rilis, artwork, metadata track (judul, AI toggle, lirik), dan penambahan lagu baru (append).
     - Menaikkan nomor revisi lokal (`revision + 1`) atomik.
  3. Live Journal: Memperluas `toolost_uploader/live_journal.py` agar menyelaraskan binding checkpoint baru (`update_for_append`) dan memvalidasi operasi: `update_title`, `update_date`, `update_artwork`, `append_audio`, `update_metadata`, `save`, dan `readback`.
  4. Live Executor: Di `toolost_uploader/live_draft.py`:
     - `update_title`: memperbarui nama album di tab Basic Information.
     - `update_date`: memperbarui tanggal rilis via navigasi Vuetify datepicker di tab Release Information.
     - `update_artwork`: memperbarui cover artwork via tombol Replace di tab Artwork.
     - `append_tracks`: mengunggah audio lagu susulan via tombol Upload di tab Manage Tracks.
     - `metadata_update_and_append`: memperbarui metadata lagu lama yang direvisi dan mengisi metadata lagu baru.
     - `update_run_steps`: alur sinkronisasi berurutan, Save Changes, readback verifikasi seluruh isi rilis, dan navigasi kembali ke portal.
     - Idempotent: langsung melaporkan `draft_up_to_date` jika manifest identik.
  5. Pengujian unit offline di `tests/test_storage.py`, `tests/test_cli.py`, `tests/test_live_draft.py`, dan `tests/test_live_recovery.py` (total 188 tests lolos 100%).
  6. Version bump ke `0.1.5` dan publikasi rilis PyPI baru.
- **Keluar:** Menghapus track yang sudah ada, mengubah urutan lagu lama secara destruktif, atau memicu publish distribusi.
- **Acceptance:**
  - `toolost upload manifest.json --draft-only --update` (atau `--append`) memproses pembaruan judul, tanggal rilis, artwork, lirik/AI/judul track lama, serta lagu susulan baru tanpa error `checkpoint_exists`.
  - Datepicker Too Lost diotomatisasi untuk memilih tanggal rilis target secara presisi.
  - Perubahan disimpan (*Save Changes*) dan diverifikasi lewat readback.
  - Seluruh test suite offline (188 tests) 100% lulus; `git diff --check` bersih.
- **Verifier:** `python3 -m unittest discover -s tests -q`, `git diff --check`.
- **Hasil:** Selesai (`done`, [CP-023](CHECKPOINT-HISTORY.md#cp-023--selesai-upd-01--rilis-015-fitur-update-komprehensif-judul-tanggal-rilis-artwork-metadata-track--append-lagu-susulan)); seluruh acceptance terpenuhi dan versi `0.1.5` dipublikasikan ke PyPI.

## UPD-02 — Dukungan penyisipan lagu di posisi sembarang & reordering track (done)

- **Sumber:** Laporan error pengguna 2026-10-27: `StorageError (update_track_id_mismatch)` saat flowstudio menambahkan lagu baru di tengah urutan rilis (posisi 5 dan 11).
- **Masuk:**
  1. Storage: Mengganti pengecekan kaku indeks array per-track (`track_id` lama vs baru) di `toolost_uploader/storage.py` dengan validasi himpunan hash integritas audio (`old_audio_hashes.issubset(new_audio_hashes)`). Hal ini memastikan kontinuitas rekaman audio terlindungi tanpa terikat oleh pergeseran penomoran urutan `track_id` flowstudio (`trk_{posisi}_{hash}`).
  2. Live Draft UI Reordering: Di `toolost_uploader/live_draft.py`:
     - Menambahkan method `sync_metadata_and_order` untuk menata urutan fisik track via drag & drop (`reorder_tracks`) berdasarkan nama berkas audio, lalu mengisi metadata (nama lagu, switch AI, dan lirik) sesuai nomor urut manifest terbaru.
     - Menyederhanakan argumen `update_run_steps` menjadi 6 argumen deterministik.
  3. Pengujian: Memperbarui tes offline di `tests/test_storage.py` dan `tests/test_live_draft.py` (188 tests lolos 100%).
  4. Version bump ke `0.1.6` dan publikasi rilis PyPI baru.
- **Keluar:** Menghapus audio lagu lama yang sudah ada di draft remote.
- **Acceptance:**
  - Penambahan lagu di posisi tengah maupun awal tidak lagi memicu `update_track_id_mismatch`.
  - Berkas audio yang belum ada diunggah, lalu seluruh daftar track diurutkan sesuai urutan manifest.
  - Seluruh test suite offline 100% lulus; `git diff --check` bersih.
- **Verifier:** `python3 -m unittest discover -s tests -q`, `git diff --check`.
- **Hasil:** Selesai (`done`, [CP-024](CHECKPOINT-HISTORY.md#cp-024--selesai-upd-02--rilis-016-dukungan-penyisipan-lagu-di-posisi-sembarang--reordering-track)); kontinuitas berbasis audio hash terpasang, reorder track terintegrasi, 188 unit tests lolos, dan rilis `0.1.6` live di PyPI.

## PUB-01 — Publish/distribusi (deferred)

- **Sumber:** arah produk final, bukan izin implementasi/eksekusi; [RELEASE-CONTRACT](../RELEASE-CONTRACT.md) masih proposal.
- **Gate:** keputusan user eksplisit terpisah sebelum scope/acceptance implementasi dirinci. Izin riset sampai Save tidak memenuhi gate ini.
- **Tidak dikerjakan:** klik Publish untuk riset, submit distribusi, hak/consent layanan otomatis.

## Template task baru

```text
ID / judul:
Sumber dan keputusan user:
Scope masuk / keluar; files kandidat:
Acceptance dan verifier:
Risiko / izin terpisah / stop condition:
Evidence / remaining:
```

Daftarkan status/prioritas/dependency pada current index dan claim sebelum edit implementasi. Cari overlap dahulu; child menaut parent dan tidak otomatis menutup parent.

## Template checkpoint

```text
CP-NNN — waktu — task — owner/session
Baseline: HEAD + dirty paths terkait
Status sebelum → sesudah; hasil/files
Evidence: command + hasil/exit/skips/batas, revision atau working tree
Remaining/blocker; claim dilepas/ditahan
Prioritas: perubahan + alasan, atau tetap
Next: satu ID + alasan; alternatif bila blocked; izin yang masih dibutuhkan
```

Gunakan nomor unik berikutnya; jangan renumber history. Evidence offline tidak menutup acceptance live/package/release. Tidak commit/push otomatis.
