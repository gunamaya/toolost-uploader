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

## PKG-01 — Persiapan packaging, metadata, lisensi, sanitasi sdist/wheel, dan rilis PyPI (ready)

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
