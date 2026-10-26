# Riwayat checkpoint engineering

Append-only sejak adopsi governance. Ini **bukan checkpoint executor/runtime**, tidak memuat akun, draft atau aset privat. Current status/klaim berada di [indeks](../ANTRIAN-PEKERJAAN-UTAMA.md).

## CP-001 — Baseline 684acd6

- **Task/owner:** REC-01; ringkasan historis oleh assistant pada intake GOV-01, 2026-10-25.
- **Baseline:** commit 684acd6, sebelumnya 74a24b2. Commit/push dilakukan atas instruksi eksplisit user pada sesi sebelumnya; bukan izin perubahan selanjutnya.
- **Hasil:** hardening recovery offline pada live_draft/live_journal, script, tes dan docs. Legacy mutation recovery dinonaktifkan; readback-only untuk journal v2 sesudah Save; [batas lengkap](../LIVE-DRAFT.md).
- **Evidence historis, tidak dijalankan ulang pada pencatatan ini:** `python3 -m unittest discover -s tests -q` dan `.venv/bin/python -m unittest discover -s tests -q`: masing-masing 154 tes, 2 skip; py_compile dan `git diff --check` lulus. Build/install opt-in belum dijalankan karena modul build tidak tersedia pada interpreter yang diperiksa. Smoke 74a24b2 tidak diulang.
- **Status:** REC-01 done hanya untuk acceptance offline. Tidak ada klaim aktif yang diimpor. Resume produksi/live/package/publish bukan otomatis done.
- **Prioritas:** user meminta tidak memperluas hardening/overengineering; tidak menambah pekerjaan semacam itu otomatis.
- **Next:** GOV-01 karena permintaan baru mengadopsi lifecycle task. Bila scope bukan governance, konfirmasi sebelum menambah runtime scheduler.

## CP-002 — Mulai GOV-01

- **Waktu/owner:** 2026-10-25, sesi-adopsi-governance / assistant; waktu jam lokal belum dicatat, tidak direka.
- **Baseline:** 684acd6; working tree awal bersih menurut `git status --short`.
- **Status:** GOV-01 ready → in_progress. Claim di current index; satu writer docs.
- **Sumber dibaca read-only:** yt-to-flowmusic/AGENTS.md; docs/ANTRIAN-PEKERJAAN-UTAMA.md (current table/claims/recent checkpoints); docs/backlog/TASK-DETAILS.md §7/template. Pola sumber: satu indeks, detail/riwayat terpisah, bounded reading, claim sebelum edit, completion berdasarkan acceptance/evidence, tanpa auto-next. Repo sumber tidak diubah dan tesnya tidak dijalankan.
- **Hasil sementara:** current index, TASK-DETAILS, CHECKPOINT-HISTORY dibuat; scope docs-only. Peninjauan runtime queue menunjukkan itu concern berbeda, tidak diadopsi.
- **Verifier direncanakan:** cek link dokumen file lokal, suite offline stdlib, `git diff --check`. Belum ada hasil tes baru pada checkpoint ini.
- **Stop/remaining:** sambungkan AGENTS/README/panduan lanjut; tes dan completion. Stop jika ada perubahan pihak lain atau scope membutuhkan executor/CLI/runtime/live.
- **Prioritas:** GOV-01 aktif; CLI-01 review direkomendasikan berikutnya, RES-01/PUB-01 deferred, LIVE-02 blocked tanpa scope/izin baru.
- **Next:** tuntaskan GOV-01; setelah done, rekomendasikan CLI-01 tanpa otomatis memulai implementasi atau operasi akun.

## CP-003 — Selesai GOV-01

- **Waktu/owner:** 2026-10-25, sesi-adopsi-governance / assistant.
- **Baseline:** 684acd6; perubahan hanya dokumentasi governance dan pointer, tidak ada dirty path kode/runtime saat mulai.
- **Hasil/files:** menambahkan `docs/ANTRIAN-PEKERJAAN-UTAMA.md`, `docs/backlog/TASK-DETAILS.md`, `docs/backlog/CHECKPOINT-HISTORY.md`; memperbarui `AGENTS.md`, `README.md`, `docs/CONTINUE-IMPLEMENTATION.md`, `docs/CONTINUE-PROMPT.md`. Current index memisahkan status/claim dari detail acceptance dan history; task REC-01/CLI-01/RES-01/LIVE-02/PUB-01 dicatat tanpa mengaktifkan fitur deferred/blocked.
- **Evidence:** `python3 -m unittest discover -s tests -q` → 154 passed, 2 skipped; `git diff --check` lulus; script link check → 30 link file lokal valid, anchor heading tidak diverifikasi otomatis. Tidak menjalankan browser/live, repo integrator, scheduler runtime, build/install, atau operasi akun.
- **Status:** GOV-01 `in_progress` → `done` untuk acceptance docs-only; claim dilepas. Tidak ada klaim aktif.
- **Batas:** status runtime/CLI produk tidak berubah; evidence offline tidak menutup live/package/release. `docs/CONTINUE-*` memiliki riwayat lama yang dipertahankan, tetapi indeks kini authoritative.
- **Reprioritization:** tidak ada; user meminta adopsi pola task, bukan perluasan hardening/overengineering.
- **Next priority:** `CLI-01` — review bounded apakah command/kontrak draft benar-benar didukung, karena current CLI hanya `validate`; alternatif bila user tidak ingin review adalah mempertahankan status tanpa perubahan.


## CP-004 — Mulai CLI-01

- **Waktu/owner:** 2026-10-25 13:05 WIB, sesi-orkestrasi-cli-01 / assistant.
- **Baseline:** 684acd6 + dirty docs (`AGENTS.md`, `README.md`, `docs/CONTINUE-*`, `docs/ANTRIAN-PEKERJAAN-UTAMA.md`, `docs/backlog/*`).
- **Status:** CLI-01 `ready` → `in_progress`. Claim aktif dicatat pada current index.
- **Scope:** review perbedaan CLI `toolost validate` terpasang, script `scripts/upload_draft.py`, kontrak `docs/CONTRACT-V1.md`, implementasi Playwright `toolost_uploader/live_draft.py`, serta kebutuhan integrator `yt-to-flowmusic`. Menghasilkan tabel gap implementasi vs proposal dan rekomendasi slice implementasi terkecil. Task review/proposal saja, tanpa live run atau penambahan command sebelum izin implementasi.
- **Verifier:** inspeksi kode offline/help CLI, suite unittest offline, `git diff --check`.
- **Stop condition:** bila memerlukan implementasi command atau mutasi live, berhenti dan ajukan keputusan scope ke user.


## CP-005 — Selesai CLI-01

- **Waktu/owner:** 2026-10-25 13:07 WIB, sesi-orkestrasi-cli-01 / assistant.
- **Baseline:** 684acd6 + dirty docs (`AGENTS.md`, `README.md`, `docs/CONTINUE-*`, `docs/ANTRIAN-PEKERJAAN-UTAMA.md`, `docs/backlog/*`).
- **Hasil/files:** membuat `docs/CLI-REVIEW.md`, memperbarui `docs/backlog/TASK-DETAILS.md`, `docs/backlog/CHECKPOINT-HISTORY.md`, dan `docs/ANTRIAN-PEKERJAAN-UTAMA.md`.
- **Temuan review:**
  1. Status command: `toolost validate` adalah satu-satunya command terpasang; eksekusi draft Playwright ada di `scripts/upload_draft.py` (bukan di executable `toolost`); `resume`, `status`, `release list/detail`, `publish` masih proposal / deferred.
  2. Manifest gap: `validation.py` menerima album/ep/multi-track & metadata kaya, sedangkan `live_draft.py` hanya menerima Single 1-track tanpa optional fields.
  3. Gap integrator `yt-to-flowmusic`: `FlowClient` memanggil binary CLI terpasang via subprocess dengan stdout JSON dan exit code terukur, sedangkan kemampuan draft saat ini masih berupa script manual dengan argumen browser tingkat rendah (`--cdp`, `--expected-account`, `--approve-draft`, `--accept-ui-date-for-smoke`).
  4. Usulan slice produk terkecil: task `CLI-02` untuk memasang subcommand `toolost upload-draft` (Single 1-track draft-only) dengan kontrak exit code dan JSON yang stabil.
- **Evidence:** `python3 -m unittest discover -s tests -q` → 154 passed, 2 skipped; `git diff --check` lulus; validasi link lokal markdown lulus 100%. Tidak ada browser live dibuka, tidak ada operasi akun, tidak ada commit/push.
- **Status:** CLI-01 `in_progress` → `done`. Claim mandiri dilepas.
- **Batas:** review offline dan proposal; belum ada penambahan subcommand di CLI atau perubahan kode executor.
- **Next priority:** menunggu keputusan user untuk Opsi A (`toolost upload-draft`) vs Opsi B (`toolost upload --draft-only`), lalu mendaftarkan dan mengklaim task implementasi `CLI-02`. Alternatif jika user belum ingin implementasi CLI adalah mempertahankan status tanpa perubahan kode.


## CP-006 — Mulai CLI-02

- **Waktu/owner:** 2026-10-25 13:10 WIB, sesi-implementasi-cli-02 / assistant.
- **Baseline:** 684acd6 + dirty docs (`AGENTS.md`, `README.md`, `docs/CONTINUE-*`, `docs/CLI-REVIEW.md`, `docs/ANTRIAN-PEKERJAAN-UTAMA.md`, `docs/backlog/*`).
- **Status:** CLI-02 `ready` → `in_progress`. Claim aktif dicatat pada current index.
- **Scope:** implementasi subcommand `toolost upload --draft-only` pada CLI terpasang dan perluasan dukungan tipe rilis `album` multi-track pada executor `live_draft.py` (dialog Album, multi-track audio chooser, track editor per-track, reorder, readback Album name). Unit test offline Playwright mock.
- **Verifier:** `python3 -m unittest discover -s tests -q`, `python3 -m toolost_uploader upload --help`, `git diff --check`.
- **Stop condition:** jika memerlukan eksekusi live browser, operasi akun nyata, atau publish.


## CP-007 — Selesai CLI-02

- **Waktu/owner:** 2026-10-25 13:16 WIB, sesi-implementasi-cli-02 / assistant.
- **Baseline:** 684acd6 + dirty files (`toolost_uploader/cli.py`, `toolost_uploader/live_draft.py`, `tests/test_cli.py`, `tests/test_live_draft.py`, `README.md`, `docs/LIVE-DRAFT.md`, `docs/ANTRIAN-PEKERJAAN-UTAMA.md`, `docs/backlog/*`).
- **Hasil/files:**
  1. `toolost_uploader/cli.py`: Menambahkan subcommand `toolost upload` dengan flag wajib `--draft-only`, penolakan upload tanpa `--draft-only` (exit 2), integrasi ke `live_draft.execute()`, output JSON murni ke stdout bila `--json`, dan exit codes deterministik (0/2/4/5).
  2. `toolost_uploader/live_draft.py`: Memperluas `preflight()`, `create()`, `audio()`, `metadata()`, `metadata_open()`, dan `readback()` untuk mendukung rilis bertipe `album` (multi-track), multi-file upload, editor track per-baris, dan verifikasi `Album name`.
  3. `tests/test_live_draft.py`: Menambahkan unit test preflight Album multi-track, mock file chooser multi-file, dan metadata/readback Album.
  4. `tests/test_cli.py`: Menambahkan unit test CLI untuk `upload --help`, penolakan tanpa `--draft-only` (human & JSON), pemanggilan mock sukses, invalid input, dan draft error reconciliation required.
  5. `README.md` & `docs/LIVE-DRAFT.md`: Memperbarui dokumentasi ketersediaan subcommand `toolost upload --draft-only`.
- **Evidence:** `python3 -m unittest discover -s tests -q` → 161 passed, 2 skipped; `git diff --check` lulus bersih; `python3 -m toolost_uploader upload --help` lulus; link markdown lokal 100% valid.
- **Status:** CLI-02 `in_progress` → `done`. Claim mandiri dilepas.
- **Batas bukti:** Pengujian seluruhnya offline dengan mock unit test Playwright. Tidak ada login browser live baru dibuka, tidak ada draft nyata dibuat pada akun di sesi ini, tidak ada aksi publish.
- **Next priority:** Meminta keputusan pengguna apakah diperlukan verifikasi live Playwright draft-only terkontrol untuk Album multi-track pada akun pengguna (mengaktifkan [`LIVE-02`](../ANTRIAN-PEKERJAAN-UTAMA.md)), atau integrasi subprocess di sisi `yt-to-flowmusic`.


## CP-008 — Mulai LIVE-02

- **Waktu/owner:** 2026-10-25 13:20 WIB, sesi-live-02 / assistant.
- **Baseline:** 684acd6 + dirty files (`toolost_uploader/cli.py`, `toolost_uploader/live_draft.py`, `tests/test_cli.py`, `tests/test_live_draft.py`, `README.md`, `docs/LIVE-DRAFT.md`, `docs/ANTRIAN-PEKERJAAN-UTAMA.md`, `docs/backlog/*`).
- **Status:** LIVE-02 `ready` → `in_progress`. Claim aktif dicatat pada current index.
- **Scope:** persiapan dan eksekusi satu skenario verifikasi live Playwright draft-only untuk tipe rilis Album multi-track via command `toolost upload --draft-only`. Alur: attach ke CDP browser operator (127.0.0.1:9437), preflight identity `/api/auth/me`, New Release Album, upload artwork uji, upload audio uji multi-track, edit metadata per-track, Save Changes sekali, reopen draft dan readback verifikasi subset. DILARANG menekan Publish.
- **Verifier:** eksekusi `toolost upload <manifest.json> --draft-only ... --json` sukses exit 0 dengan status `draft_saved_subset`.
- **Stop condition / Gate:** membutuhkan browser CDP operator yang sudah login di port 9437, ID akun numerik (`--expected-account`), serta path manifest Album dan aset uji yang ditentukan oleh pengguna. Stop jika browser target tertutup, login/identity berubah, atau terjadi error Save.


## CP-009 — Blocker LIVE-02: Sesi browser 401 Unauthorized

- **Waktu/owner:** 2026-10-25 13:27 WIB, sesi-live-02 / assistant.
- **Baseline:** 684acd6 + dirty files (`toolost_uploader/cli.py`, `toolost_uploader/live_draft.py`, `tests/*`, `docs/*`).
- **Status:** LIVE-02 `in_progress` → `blocked`. Klaim ditahan / menunggu tindakan pengguna.
- **Hasil observasi:** Eksekusi `toolost upload --draft-only` pada browser CDP port 9437 mendeteksi bahwa respons `/api/auth/me` dan `/api/portal/release/` mengembalikan kode HTTP `401 Unauthorized`. Guard identitas `identity_changed` dan preflight akun secara tepat membatalkan mutasi (fail-stop `account_mismatch_or_unobserved` exit 4) tanpa membuat rilis atau mengirim mutasi apapun.
- **Blocker:** Sesi autentikasi Too Lost pada profil browser pengguna telah kedaluwarsa (401 Unauthorized).
- **Tindakan yang dibutuhkan:** Pengguna perlu melakukan login ulang manual pada jendela browser Chrome riset tersebut sampai akun aktif kembali di portal, lalu mengonfirmasi kembali.
- **Next:** Lanjutkan eksekusi `toolost upload --draft-only` untuk Album multi-track setelah sesi 200 OK diverifikasi.


## CP-010 — Implementasi Verbose Progress Logging CLI & DraftUI

- **Waktu/owner:** 2026-10-26 14:50 WIB, sesi-live-02 / assistant.
- **Baseline:** 684acd6 + dirty files (`toolost_uploader/cli.py`, `toolost_uploader/live_draft.py`, `tests/test_cli.py`, `tests/test_live_draft.py`, `README.md`, `docs/LIVE-DRAFT.md`, `docs/ANTRIAN-PEKERJAAN-UTAMA.md`, `docs/backlog/*`).
- **Status:** LIVE-02 tetap `in_progress`.
- **Hasil/files:**
  1. `toolost_uploader/cli.py`: Menambahkan flag `-v, --verbose` pada subcommand `upload` untuk memancarkan log tahapan progres secara langsung ke `sys.stderr` berformat `[HH:MM:SS] [toolost] ...`. Tetap mempertahankan output stdout sebagai JSON murni bila `--json` digunakan.
  2. `toolost_uploader/live_draft.py`: Menambahkan callback logging di seluruh milestone `DraftUI` (preflight, connect CDP, verify account, create release, upload artwork & encoding wait, upload multi-track audio & encoding wait, reorder track, metadata track, Save Changes, dan readback verifikasi). Memperbaiki sinkronisasi wait elemen di `artwork()` dan `audio()`.
  3. `tests/test_cli.py`: Menambahkan unit test `test_upload_verbose_flag` untuk memverifikasi log progres ke stderr dan integritas stdout JSON.
  4. `README.md` & `docs/LIVE-DRAFT.md`: Mendokumentasikan argumen `--verbose` pada CLI.
- **Evidence:** `python3 -m unittest discover -s tests -q` → 162 lulus, 2 skip. `git diff --check` bersih.
- **Batas bukti:** Pengujian offline dengan mock unit test Playwright. Live CDP belum tersambung karena browser Chrome di port 9437 belum berjalan.
- **Next:** Menjalankan `scripts/gather.py observe` untuk menyalakan endpoint CDP 9437 dengan sesi akun Too Lost aktif, lalu mengeksekusi `toolost upload ... --verbose`.


## CP-011 — Selesai LIVE-02: Verifikasi Live Playwright Draft Album Multi-Track

- **Waktu/owner:** 2026-10-26 15:10 WIB, sesi-live-02 / assistant.
- **Baseline:** 684acd6 + dirty files (`toolost_uploader/cli.py`, `toolost_uploader/live_draft.py`, `tests/test_cli.py`, `README.md`, `docs/LIVE-DRAFT.md`, `docs/ANTRIAN-PEKERJAAN-UTAMA.md`, `docs/backlog/*`).
- **Status:** LIVE-02 `in_progress` → `done`. Claim mandiri dilepas.
- **Hasil/eksekusi:**
  1. `toolost_uploader/live_draft.py`: Menyempurnakan deteksi selesai upload artwork pada DOM (`.artwork-selected`) dan dialog inner Vuetify (`.tl-upload-dialog`), mengatasi masalah wrapper Vue modal yang persisten.
  2. Eksekusi live penuh rilis Album multi-track via perintah CLI:
     ```sh
     .venv/bin/python -m toolost_uploader upload .local/fixtures/album-manifest.json \
       --draft-only --profile live-album-smoke --expected-account 422512 \
       --cdp http://127.0.0.1:9437 --approve-draft --accept-ui-date --verbose --json
     ```
  3. Seluruh alur terverifikasi live secara otomatis:
     - Preflight identitas akun `/api/auth/me` cocok: `422512`.
     - Pembuatan rilis tipe Album: judul `Album Uji Otomasi Playwright`, remote draft ID `2004317`.
     - Unggahan berkas artwork PNG 3000×3000 & encoding wait sukses (6 detik).
     - Unggahan berkas multi-track audio (2 file MP3) & encoding wait sukses (19 detik).
     - Pemeriksaan dan pengaturan urutan track sesuai manifest.
     - Pengisian metadata per-track: Track 1 `Terangnya Belum Pulang` (AI: True), Track 2 `Sungai Teh Susu` (AI: True).
     - Eksekusi Save Changes sekali dan konfirmasi Too Lost berhasil.
     - Readback verifikasi subset dengan membuka kembali `/uploader/edit/2004317`: `Album name`, artwork, jumlah track (2), judul tiap track, dan status AI terverifikasi cocok 100%.
  4. Keluaran JSON deterministik exit 0 (`draft_saved_subset`, draft_id `2004317`).
- **Evidence:** Eksekusi aktual CDP port 9437 selesai exit 0; test suite offline 162 passed, 2 skipped; `git diff --check` bersih.
- **Batas bukti:** Pengujian terbatas pada simpan draft (**draft-only**); tombol Publish **DILARANG dan TIDAK DITEKAN**; rights, pricing, stores/services, dan penjadwalan tanggal rilis spesifik di luar scope subset riset ini.
- **Next priority:** Meminta keputusan pengguna: integrasi pemanggilan subprocess uploader dari sisi `yt-to-flowmusic`, atau evaluasi lanjutan sebelum perancangan release/publish.


## CP-012 — Penutupan RES-01 (Superseded) dan Inisiasi INT-01

- **Waktu/owner:** 2026-10-26 15:20 WIB, sesi-integrasi / assistant.
- **Baseline:** a3a4542 + dirty docs (`docs/ANTRIAN-PEKERJAAN-UTAMA.md`, `docs/backlog/*`).
- **Status:** RES-01 `deferred` → `superseded`. INT-01 `ready`.
- **Keputusan:**
  1. Pengguna menyetujui penutupan RES-01 (resume mutasi produksi) sebagai `superseded` karena eksekusi dari nol terbukti sangat cepat (~50 detik), fail-stop idempotensi via journal v2 lebih aman, dan rekonsiliasi pasca-Save `--reconcile-readback-only` sudah tersedia tanpa risiko duplikasi track/lagu.
  2. Mendaftarkan INT-01 untuk penyusunan rencana integrasi pemanggilan CLI subprocess dari sisi `yt-to-flowmusic`.
- **Hasil/files:** Pembaruan antrean kanonikal dan detail task; penulisan dokumen rencana integrasi di `docs/INTEGRATION-PLAN.md`.
- **Next priority:** Menyelesaikan dokumen rencana integrasi INT-01 untuk review pengguna.

## CP-013 — Selesai ENV-01: Subcommand Setup, Check Readiness, dan Auto-bootup CDP

- **Waktu/owner:** 2026-10-26 15:45 WIB, sesi-env-01 / assistant.
- **Baseline:** a3a4542 + dirty files (`toolost_uploader/browser.py`, `toolost_uploader/cli.py`, `tests/test_browser.py`, `tests/test_cli.py`, `README.md`, `docs/CLI-REVIEW.md`, `docs/ANTRIAN-PEKERJAAN-UTAMA.md`, `docs/backlog/*`).
- **Status:** ENV-01 `in_progress` → `done`. Claim mandiri dilepas.
- **Hasil/eksekusi:**
  1. `toolost_uploader/browser.py`:
     - Deteksi Google Chrome binary lintas sistem operasi (macOS default ke `/Applications/Google Chrome.app/...`, Linux, Windows, serta override custom).
     - Resolusi path profil lokal di `.local/profiles/<alias>` dan pembersihan stale `SingletonLock` otomatis jika Chrome tidak aktif.
     - Deteksi ketersediaan endpoint loopback CDP (HTTP `http://127.0.0.1:9437/json/version`).
     - Peluncuran proses Chrome: mode setup interaktif (tanpa debugging flag) dan mode background CDP (`--remote-debugging-port=9437`).
     - Deteksi status autentikasi Too Lost via Playwright interaktif yang mengamati respons `/api/auth/me` pada event navigasi portal Too Lost.
  2. Subcommand `toolost setup`:
     - Membuka Chrome biasa dengan profil terisolasi ke halaman login Too Lost agar operator dapat login manual dengan aman tanpa pembacaan cookie/kredensial otomatis.
  3. Subcommand `toolost check`:
     - Memvalidasi kesiapan runtime: keberadaan binary Chrome, status lock profil, port CDP, serta mencocokkan identitas akun pengguna dengan `--expected-account`.
     - Mendukung argumen `--auto-bootup` untuk menyalakan CDP secara otomatis bila belum aktif.
     - Menyediakan keluaran human-readable dan JSON murni (`--json`) dengan exit code deterministik (0=ready, 2=login_required/mismatch, 5=error binary/OS).
  4. Auto-bootup pada `toolost upload`:
     - Perintah `toolost upload` kini secara otomatis memeriksa dan menyalakan browser Chrome CDP jika port belum aktif sebelum menghubungkan Playwright.
     - Informasi bootup dan pemeriksaan status dialirkan secara rapi ke stderr saat mode verbose (`-v, --verbose`) aktif.
  5. Pengujian unit:
     - 7 unit test baru di `tests/test_browser.py` dan 2 test integrasi CLI di `tests/test_cli.py` (total 171 passed, 2 skipped offline).
- **Evidence:**
  - `python3 -m unittest discover -s tests -q`: 171 tests passed, 2 skipped, 0 failure, 0 error.
  - `git diff --check`: bersih (exit 0).
  - Eksekusi live: `toolost check --profile live-album-smoke --expected-account 422512 --json` mengembalikan status `ready`, account ID `422512`.
- **Batas bukti:**
  - Browser login tetap manual oleh pengguna; tidak ada pembacaan password/cookie langsung dari disk.
  - Upload tetap terkunci pada simpan draft (**draft-only**); operasi publish dilarang keras.
- **Next priority:** INT-01 (Implementasi adapter integrasi `TooLostClient` di repo `yt-to-flowmusic` mengacu pada `docs/INTEGRATION-PLAN.md`).

## CP-014 — Selesai PKG-01: Metadata, Lisensi MIT, Sanitasi Manifest, Build & Twine Verification

- **Waktu/owner:** 2026-10-26 16:05 WIB, sesi-pkg-01 / assistant.
- **Baseline:** 3fe36b2 + dirty files (`pyproject.toml`, `LICENSE`, `MANIFEST.in`, `toolost_uploader/__init__.py`, `tests/test_packaging.py`, `README.md`, `docs/*`).
- **Status:** PKG-01 `in_progress` → `done`. Claim mandiri dilepas.
- **Hasil/eksekusi:**
  1. `LICENSE`: Lisensi MIT ditambahkan dengan copyright Gunamaya / KiriminAja 2026.
  2. `pyproject.toml`:
     - Versi resmi rilis dinaikkan ke `0.1.0`.
     - Penghapusan classifier pembatas `"Private :: Do Not Upload"`.
     - Penggunaan ekspresi SPDX `license = "MIT"` modern.
     - Penambahan core dependency `"playwright>=1.40.0,<2"`.
     - Penambahan metadata author, deskripsi, keywords, serta URLs (`Homepage`, `Repository`, `Issues`).
  3. `MANIFEST.in`:
     - Sanitasi sdist ketat: mengecualikan `.local/`, `.venv/`, `.gitignore`, dan cache.
     - Menyertakan `README.md`, `LICENSE`, `pyproject.toml`, dan schema manifest `docs/schemas/*.json`.
  4. `toolost_uploader/__init__.py`: Versi `__version__ = "0.1.0"`.
  5. Pengujian & Verifikasi Packaging:
     - `uv build`: Berhasil memproduksi `dist/toolost_uploader-0.1.0.tar.gz` dan `dist/toolost_uploader-0.1.0-py3-none-any.whl` tanpa peringatan/warning deprecation.
     - `uv tool run twine check dist/*`: Lolos 100% (`PASSED` untuk wheel dan sdist).
     - `TOOLOST_TEST_DIST_DIR=dist python -m unittest tests/test_packaging.py`: Berhasil menguji pembuatan virtual environment bersih, instalasi wheel tanpa ketergantungan luar, eksekusi CLI `toolost --help`, `toolost --version`, serta validasi manifest sintetis.
- **Evidence:**
  - `uv tool run twine check dist/*`: PASSED.
  - `TOOLOST_TEST_DIST_DIR=dist .venv/bin/python -m unittest tests/test_packaging.py`: OK.
  - `python3 -m unittest discover -s tests -q`: 171 passed, 2 skipped (offline).
  - `git diff --check`: bersih (exit 0).
- **Batas bukti:**
  - Build dan verifikasi metadata archive terbukti bersih secara offline dan mandiri.
  - Pengunggahan ke TestPyPI / PyPI publik belum dieksekusi (memerlukan token PyPI `__token__` atau GitHub Actions OIDC).
- **Next priority:**
  - Melakukan upload ke TestPyPI / PyPI (bila token diberikan), ATAU:
  - Melanjutkan ke INT-01 (implementasi adapter `TooLostClient` di repo `yt-to-flowmusic`).

## CP-015 — Publikasi Paket ke TestPyPI dan Verifikasi Instalasi Live Clean-Venv

- **Waktu/owner:** 2026-10-26 16:08 WIB, sesi-pypi / assistant.
- **Baseline:** a9ce71b + clean.
- **Status:** PKG-01 tahap publikasi TestPyPI `done`.
- **Hasil/eksekusi:**
  1. Eksekusi pengunggahan paket ke TestPyPI via `twine upload`:
     - Endpoint: `https://test.pypi.org/legacy/`
     - Kredensial: API token dari `~/.secrets/test-pypi-cred.txt` (`__token__`).
     - Berkas terunggah:
       - `toolost_uploader-0.1.0-py3-none-any.whl` (54.4 kB)
       - `toolost_uploader-0.1.0.tar.gz` (78.0 kB)
     - URL rilis resmi: `https://test.pypi.org/project/toolost-uploader/0.1.0/`
  2. Verifikasi instalasi live dari TestPyPI di environment baru `/tmp/test-pypi-verify`:
     - Perintah: `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ toolost-uploader`
     - Hasil: Paket `toolost-uploader-0.1.0` terpasang bersama core dependencies (`playwright 1.64.1`, `greenlet`, `pyee`, `typing-extensions`).
     - Verifikasi CLI: `toolost --version` mengembalikan `toolost 0.1.0` (exit code 0); `toolost --help` menampilkan alur kerja dan subcommands dengan lengkap dan rapi.
- **Evidence:**
  - URL publikasi: `https://test.pypi.org/project/toolost-uploader/0.1.0/`
  - Output instalasi clean-venv exit code 0 (`Successfully installed toolost-uploader-0.1.0 ...`).
  - Unit tests offline: 171 passed, 2 skipped.
- **Batas bukti:**
  - Publikasi saat ini berada di TestPyPI (`test.pypi.org`).
  - Rilis ke PyPI produksi (`pypi.org`) membutuhkan token terpisah untuk produksi.
- **Next priority:** INT-01 (Implementasi adapter integrasi `TooLostClient` di repo `yt-to-flowmusic` mengacu pada `docs/INTEGRATION-PLAN.md`).
