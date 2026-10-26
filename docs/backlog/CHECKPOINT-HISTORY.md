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
- **Next priority:** PKG-01 (Persiapan packaging, metadata, lisensi MIT, build wheel & sdist, dan rilis PyPI).

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
- **Next priority:** Publikasi ke PyPI produksi (pypi.org).

## CP-016 — Publikasi Resmi ke PyPI Produksi dan Integrasi Dependency

- **Waktu/owner:** 2026-10-26 16:11 WIB, sesi-pypi / assistant.
- **Baseline:** c7b3163 + dirty docs (`docs/INTEGRATION-PLAN.md`, `docs/ANTRIAN-PEKERJAAN-UTAMA.md`, `docs/backlog/*`).
- **Status:** Publikasi PyPI produksi `done`.
- **Hasil/eksekusi:**
  1. Eksekusi pengunggahan paket ke PyPI produksi via `twine upload`:
     - Endpoint: `https://upload.pypi.org/legacy/`
     - Kredensial: API token produksi dari `~/.secrets/pypi-cred.txt` (`__token__`).
     - Berkas terunggah:
       - `toolost_uploader-0.1.0-py3-none-any.whl` (54.4 kB)
       - `toolost_uploader-0.1.0.tar.gz` (78.0 kB)
     - URL rilis resmi: `https://pypi.org/project/toolost-uploader/0.1.0/`
  2. Verifikasi instalasi live dari PyPI produksi di virtual environment bersih:
     - Perintah: `pip install toolost-uploader`
     - Hasil: Paket `toolost-uploader-0.1.0` terpasang sukses bersama core dependencies (`playwright-1.64.1`).
     - Verifikasi CLI: `toolost --version` ➔ `toolost 0.1.0`; `toolost --help` exit code 0.
  3. Pembaruan Dokumen Integrasi `docs/INTEGRATION-PLAN.md`:
     - Menetapkan pengambilan paket langsung via PyPI (`pip install toolost-uploader` / `"toolost-uploader>=0.1.0"` pada `pyproject.toml` `yt-to-flowmusic`).
     - Deteksi binary `toolost` via `shutil.which("toolost")` tanpa manipulasi path lokal.
- **Evidence:**
  - URL publikasi: `https://pypi.org/project/toolost-uploader/0.1.0/`
  - Output instalasi live pip exit code 0 (`Successfully installed toolost-uploader-0.1.0 ...`).
  - Unit tests offline: 171 passed, 2 skipped.
  - `git diff --check`: bersih (exit 0).
- **Batas bukti:**
  - Paket publikasi resmi aktif di PyPI publik.
  - Alur eksekusi draft uploader tetap terkunci pada simpan draft (**draft-only**); operasi publish dilarang keras.
- **Next priority:** LYR-01 (Dukungan tab Lyrics di Playwright live executor).

## CP-017 — Rilis PyPI 0.1.1: Perbaikan Metadata Author, Broken Links, dan Desain Mandiri

- **Waktu/owner:** 2026-10-26 16:28 WIB, sesi-pypi / assistant.
- **Baseline:** c0b492d + dirty files (`README.md`, `LICENSE`, `pyproject.toml`, `toolost_uploader/__init__.py`).
- **Status:** Publikasi PyPI 0.1.1 `done`.
- **Hasil/eksekusi:**
  1. `pyproject.toml` & `LICENSE`:
     - Metadata author dan lisensi diperbarui: nama `Anggi Gunamaya`, email `anggi@gunamanya.id`.
     - Copyright resmi: `Copyright (c) 2026 Anggi Gunamaya`.
     - Versi dinaikkan ke `0.1.1`.
  2. `README.md`:
     - Menghapus keterikatan dan penyebutan proyek integrator internal (`yt-to-flowmusic`), menegaskan posisi paket sebagai CLI & library mandiri untuk orkestrasi rilis Too Lost.
     - Memperbaiki seluruh broken links di PyPI: tautan relatif ke `LICENSE` dan `docs/*` diubah menjadi tautan absolut GitHub (`https://github.com/gunamaya/toolost-uploader/blob/main/...`).
  3. Publikasi & Verifikasi PyPI 0.1.1:
     - `uv build`: Memproduksi `toolost_uploader-0.1.1-py3-none-any.whl` dan `toolost_uploader-0.1.1.tar.gz`.
     - `twine check dist/*`: Lolos `PASSED` 100%.
     - `twine upload`: Berhasil diunggah ke PyPI produksi.
     - URL rilis resmi: `https://pypi.org/project/toolost-uploader/0.1.1/`
- **Evidence:**
  - URL publikasi: `https://pypi.org/project/toolost-uploader/0.1.1/`
  - `twine check dist/*`: PASSED.
  - Test suite offline: 171 passed, 2 skipped.
  - `git diff --check`: bersih (exit 0).
- **Batas bukti:**
  - Rilis 0.1.1 aktif dan live di PyPI produksi.
  - Draft-only guard tetap terkunci.
- **Next priority:** LYR-01 (Dukungan tab Lyrics di Playwright live executor).

## CP-018 — Selesai LYR-01: Otomasi Tab Lyrics Playwright & Live Verification Profil Aidoto

- **Waktu/owner:** 2026-10-26 21:45 WIB, sesi-lyr-01 / assistant.
- **Baseline:** b84727f + dirty files (`toolost_uploader/live_draft.py`, `toolost_uploader/browser.py`, `tests/test_live_draft.py`, `docs/*`).
- **Status:** LYR-01 `in_progress` → `done`. Claim mandiri dilepas.
- **Hasil/eksekusi:**
  1. `toolost_uploader/live_draft.py`:
     - Memperluas validasi field track live executor untuk mengizinkan `'lyrics'` secara opsional: `{'track_id', 'title', 'audio', 'ai_assisted', 'lyrics'}`.
     - Menambahkan method `lyrics_text(track)` untuk membaca konten lirik teks UTF-8 lokal.
     - Mengotomatisasi navigasi ke tab `Lyrics` pada modal track editor Too Lost (`page.get_by_role('button', name='Lyrics', exact=True)`), mengisi teks ke textbox `Lyrics`, serta memvalidasi input teks.
     - Memperluas alur `readback()` untuk memvalidasi kesesuaian teks lirik pada tiap track yang memiliki lirik setelah reload/reopen uploader draft.
     - Memperbaiki selector tombol New Release agar memakai `.first` saat portal menampilkan empty state (`a[href="/uploader"]:visible`).
  2. `toolost_uploader/browser.py`:
     - Memperbarui `resolve_profile_dir` agar mengenali path absolut dan direktori profil user standar di `~/Library/Application Support/toolost-uploader/chrome-profiles/<alias>`, termasuk profil `aidoto`.
  3. Verifikasi Live Penuh Playwright pada Profil `aidoto`:
     - Perintah eksekusi:
       ```sh
       .venv/bin/python -m toolost_uploader upload .local/fixtures/album-lyrics-manifest.json \
         --draft-only --profile aidoto --expected-account 422512 \
         --approve-draft --accept-ui-date --verbose --json
       ```
     - Hasil: Exit code 0!
       - Preflight akun `422512` cocok.
       - Pembuatan rilis Album: judul `Album Uji Lirik Otomasi`, remote draft ID `2009368`.
       - Unggahan artwork 3000×3000px & 2 berkas audio multi-track sukses.
       - Track 1 `Terangnya Belum Pulang` (AI: True): lirik terisi 322 karakter.
       - Track 2 `Sungai Teh Susu` (AI: True): lirik terisi 135 karakter.
       - Save Changes sukses dan readback verifikasi membuktikan judul, artwork, 2 tracks, status AI, dan teks lirik kedua lagu cocok 100%.
       - Keluaran JSON: `{"status": "draft_saved_subset", "draft_id": "2009368", ...}`.
  4. Pengujian Unit Offline:
     - 173 tests passed, 2 skipped offline (`Ran 173 tests in 2.129s`).
- **Evidence:**
  - Eksekusi aktual CDP port 9437 profil `aidoto` selesai exit code 0 (draft ID `2009368`).
  - Unit tests: 173 passed, 2 skipped.
  - `git diff --check`: bersih (exit 0).
- **Batas bukti:**
  - Pengujian live tetap berada dalam mode aman simpan draft (**draft-only**); tombol Publish **DILARANG dan TIDAK DITEKAN**.
- **Next priority:** INT-01 (Implementasi adapter integrasi `TooLostClient` di repo `yt-to-flowmusic` mengacu pada `docs/INTEGRATION-PLAN.md`).

## CP-021 — Selesai CDP-02 & Rilis 0.1.3: Dukungan Unggah Berkas Audio Besar (>50MB) via is_local di CDP

- **Waktu/owner:** 2026-10-26 22:12 WIB, sesi-cdp-02 / assistant.
- **Baseline:** 1bee2a3 + dirty files (`toolost_uploader/browser.py`, `toolost_uploader/live_draft.py`, `tests/test_browser.py`, `toolost_uploader/__init__.py`, `README.md`, `docs/*`).
- **Status:** CDP-02 `in_progress` → `done`. Claim mandiri dilepas.
- **Hasil/eksekusi:**
  1. Helper `is_local_endpoint`:
     - Menambahkan fungsi helper `is_local_endpoint(endpoint: str) -> bool` di `toolost_uploader/browser.py` untuk mendeteksi apakah koneksi CDP mengarah ke loopback host (`127.0.0.1`, `localhost`, `::1`, subnet `127.*`).
  2. Integrasi `is_local=True` pada `connect_over_cdp`:
     - `toolost_uploader/live_draft.py`: `browser = p.chromium.connect_over_cdp(endpoint, is_local=is_local_endpoint(endpoint))`.
     - `toolost_uploader/browser.py`: `browser = p.chromium.connect_over_cdp(endpoint, is_local=is_local_endpoint(endpoint))`.
     - Efek: Mengangkat batas hardcoded 50MB Playwright (`fileUploadSizeLimit`) saat mengontrol browser CDP lokal, sehingga Chromium membaca path berkas langsung dari filesystem OS (`DOM.setFileInputFiles`). Menghilangkan error `Cannot transfer files larger than 50Mb to a browser not co-located with the server`.
  3. Verifikasi & Pengujian:
     - Tes langsung live CDP dengan file dummy 60MB: terbukti berhasil diunggah tanpa error (`SUCCESS: File >50MB uploaded without error!`).
     - Unit test baru `test_is_local_endpoint` di `tests/test_browser.py` memvalidasi berbagai skenario host loopback dan non-loopback.
     - Seluruh test suite offline lulus 100% (**179 passed**, 2 skipped).
  4. Rilis PyPI 0.1.3:
     - Versi dinaikkan ke `0.1.3` di `toolost_uploader/__init__.py` dan badge `README.md`.
     - `uv build`: Memproduksi `toolost_uploader-0.1.3-py3-none-any.whl` (56.3 kB) dan `toolost_uploader-0.1.3.tar.gz` (81.1 kB).
     - `twine check dist/*`: Lolos `PASSED` 100%.
     - `twine upload`: Berhasil dipublikasikan ke https://pypi.org/project/toolost-uploader/0.1.3/.
- **Evidence:**
  - URL publikasi: `https://pypi.org/project/toolost-uploader/0.1.3/`
  - `twine check dist/*`: PASSED.
  - 179 unit tests offline lulus (2 skipped).
  - `git diff --check`: bersih (exit 0).
- **Batas bukti:**
  - Perbaikan `is_local` berlaku saat endpoint adalah loopback host lokal. Rilis tetap terkunci aman pada batas **draft-only** (tombol Publish dilarang ditekan).
- **Next priority:** INT-01 (Implementasi adapter integrasi `TooLostClient` di repo `yt-to-flowmusic` mengacu pada `docs/INTEGRATION-PLAN.md`).

## CP-020 — Publikasi Rilis 0.1.2 ke PyPI: Optimalisasi Tab Memory & Tab Lyrics

- **Waktu/owner:** 2026-10-26 22:02 WIB, sesi-release-0.1.2 / assistant.
- **Baseline:** b84727f + dirty files (`pyproject.toml`, `toolost_uploader/__init__.py`, `README.md`, `toolost_uploader/browser.py`, `toolost_uploader/live_draft.py`, `tests/*`, `docs/*`).
- **Status:** Publikasi PyPI 0.1.2 `done`.
- **Hasil/eksekusi:**
  1. Version Bump:
     - `toolost_uploader/__init__.py`: dinaikkan ke `0.1.2`.
     - `README.md`: badge PyPI diperbarui ke versi 0.1.2.
  2. Distribusi & Verifikasi Integritas:
     - `uv build`: Memproduksi `toolost_uploader-0.1.2-py3-none-any.whl` (56.0 kB) dan `toolost_uploader-0.1.2.tar.gz` (80.7 kB).
     - `twine check dist/*`: Lolos `PASSED` 100%.
     - `test_packaging.py`: Uji instalasi wheel dan eksekusi clean-venv lulus 100%.
  3. Publikasi Resmi ke PyPI:
     - Mengunggah paket ke https://upload.pypi.org/legacy/ menggunakan API token resmi dari `~/.secrets/pypi-cred.txt`.
     - URL rilis resmi: `https://pypi.org/project/toolost-uploader/0.1.2/`
  4. Verifikasi Live Instalasi Bersih dari PyPI:
     - Diuji di clean venv baru via `uv pip install toolost-uploader==0.1.2`.
     - `toolost --version` mengembalikan `toolost 0.1.2` exit code 0.
     - `toolost --help` menampilkan alur kerja dan subcommands lengkap.
- **Evidence:**
  - URL publikasi: `https://pypi.org/project/toolost-uploader/0.1.2/`
  - `twine check dist/*`: PASSED.
  - Verifikasi instalasi clean-venv PyPI live: OK.
  - 178 unit tests offline lulus (2 skipped).
  - `git diff --check`: bersih (exit 0).
- **Batas bukti:**
  - Rilis 0.1.2 aktif dan live di PyPI produksi dengan fitur optimalisasi memori tab dan otomasi lirik.
  - Alur eksekusi tetap aman dalam batas draft-only; tombol Publish dilarang keras ditekan.
- **Next priority:** INT-01 (Implementasi adapter integrasi `TooLostClient` di repo `yt-to-flowmusic` mengacu pada `docs/INTEGRATION-PLAN.md`).

## CP-021 — Selesai CDP-02 & Rilis 0.1.3: Dukungan Unggah Berkas Audio Besar (>50MB) via is_local di CDP

- **Waktu/owner:** 2026-10-26 22:12 WIB, sesi-cdp-02 / assistant.
- **Baseline:** 1bee2a3 + dirty files (`toolost_uploader/browser.py`, `toolost_uploader/live_draft.py`, `tests/test_browser.py`, `toolost_uploader/__init__.py`, `README.md`, `docs/*`).
- **Status:** CDP-02 `in_progress` → `done`. Claim mandiri dilepas.
- **Hasil/eksekusi:**
  1. Helper `is_local_endpoint`:
     - Menambahkan fungsi helper `is_local_endpoint(endpoint: str) -> bool` di `toolost_uploader/browser.py` untuk mendeteksi apakah koneksi CDP mengarah ke loopback host (`127.0.0.1`, `localhost`, `::1`, subnet `127.*`).
  2. Integrasi `is_local=True` pada `connect_over_cdp`:
     - `toolost_uploader/live_draft.py`: `browser = p.chromium.connect_over_cdp(endpoint, is_local=is_local_endpoint(endpoint))`.
     - `toolost_uploader/browser.py`: `browser = p.chromium.connect_over_cdp(endpoint, is_local=is_local_endpoint(endpoint))`.
     - Efek: Mengangkat batas hardcoded 50MB Playwright (`fileUploadSizeLimit`) saat mengontrol browser CDP lokal, sehingga Chromium membaca path berkas langsung dari filesystem OS (`DOM.setFileInputFiles`). Menghilangkan error `Cannot transfer files larger than 50Mb to a browser not co-located with the server`.
  3. Verifikasi & Pengujian:
     - Tes langsung live CDP dengan file dummy 60MB: terbukti berhasil diunggah tanpa error (`SUCCESS: File >50MB uploaded without error!`).
     - Unit test baru `test_is_local_endpoint` di `tests/test_browser.py` memvalidasi berbagai skenario host loopback dan non-loopback.
     - Seluruh test suite offline lulus 100% (**179 passed**, 2 skipped).
  4. Rilis PyPI 0.1.3:
     - Versi dinaikkan ke `0.1.3` di `toolost_uploader/__init__.py` dan badge `README.md`.
     - `uv build`: Memproduksi `toolost_uploader-0.1.3-py3-none-any.whl` (56.3 kB) dan `toolost_uploader-0.1.3.tar.gz` (81.1 kB).
     - `twine check dist/*`: Lolos `PASSED` 100%.
     - `twine upload`: Berhasil dipublikasikan ke https://pypi.org/project/toolost-uploader/0.1.3/.
- **Evidence:**
  - URL publikasi: `https://pypi.org/project/toolost-uploader/0.1.3/`
  - `twine check dist/*`: PASSED.
  - 179 unit tests offline lulus (2 skipped).
  - `git diff --check`: bersih (exit 0).
- **Batas bukti:**
  - Perbaikan `is_local` berlaku saat endpoint adalah loopback host lokal. Rilis tetap terkunci aman pada batas **draft-only** (tombol Publish dilarang ditekan).
- **Next priority:** INT-01 (Implementasi adapter integrasi `TooLostClient` di repo `yt-to-flowmusic` mengacu pada `docs/INTEGRATION-PLAN.md`).

## CP-019 — Selesai TAB-01: Optimalisasi Manajemen Tab Browser CDP (Reuse Tab Aktif & Tutup Tab Redundan)

- **Waktu/owner:** 2026-10-26 21:58 WIB, sesi-tab-01 / assistant.
- **Baseline:** b84727f + dirty files (`toolost_uploader/browser.py`, `toolost_uploader/live_draft.py`, `tests/test_browser.py`, `tests/test_live_recovery.py`, `docs/*`).
- **Status:** TAB-01 `in_progress` → `done`. Claim mandiri dilepas.
- **Hasil/eksekusi:**
  1. `toolost_uploader/browser.py`:
     - Menambahkan fungsi helper terpadu `acquire_active_page(browser, domain="toolost.com", default_url=None, log=None) -> Page`.
     - Logika penanganan:
       - Memeriksa seluruh tab aktif yang terbuka pada seluruh context Playwright CDP (`not _is_closed(p)`).
       - Memprioritaskan tab yang URL-nya mengandung domain target (`toolost.com`), khususnya rute portal atau uploader rilis.
       - Jika ada banyak tab aktif (misal tab portal + tab lain atau tab sisa session restore), memilih satu tab utama dan menutup seluruh tab redundan lainnya (`p.close()`) untuk menghemat konsumsi memori browser.
       - Jika tidak ada tab domain target namun terdapat tab terbuka lain (misal `about:blank`), menggunakan tab tersebut tanpa membuka tab baru (`new_page()` dihindari).
       - Hanya membuka tab baru via `context.new_page()` jika sama sekali tidak ada tab terbuka.
     - Mengintegrasikan `acquire_active_page` ke dalam `check_auth_identity()`.
  2. `toolost_uploader/live_draft.py`:
     - Menggantikan batasan kaku `len(pages) != 1` (yang memicu `ambiguous_browser_target`) dengan pemanggilan `acquire_active_page(browser, domain='toolost.com', default_url=DEFAULT_PORTAL_URL, log=log)`.
     - Tab redundan dibersihkan secara transparan sehingga alur live upload tidak gagal saat terdapat multi-tab Too Lost aktif.
  3. Pengujian Unit Offline:
     - Menambahkan 4 unit tests komprehensif di `tests/test_browser.py`:
       - `test_acquire_active_page_reuses_single_active_tab`: tab tunggal di-reuse tanpa `new_page()` atau `close()`.
       - `test_acquire_active_page_multiple_tabs_closes_redundant`: tab portal dipilih, tab redundan ditutup via `close()`.
       - `test_acquire_active_page_reuses_non_domain_tab_when_no_match`: tab kosong di-reuse dan dinavigasikan ke `default_url` tanpa `new_page()`.
       - `test_acquire_active_page_opens_new_tab_only_when_empty`: hanya membuka tab baru bila daftar tab kosong.
     - Menambahkan 1 unit test di `tests/test_live_recovery.py`:
       - `test_execute_with_multiple_tabs_reuses_portal_and_closes_redundant`: membuktikan `execute` multi-tab membersihkan tab redundan dan menjalankan langkah-langkah draft dengan sukses.
     - Seluruh test suite (178 unit tests) lulus 100% (2 skipped).
  4. Pengujian Live Profiling:
     - Pengujian pembukaan 2 tab (termasuk dummy tab eksternal `example.com` dan multiple tab `toolost.com`) via CDP loopback:
     - Eksekusi `toolost check --profile aidoto --json` sukses exit code 0; tab ekstra otomatis terdeteksi dan ditutup, menyisakan tepat 1 tab portal rilis aktif (`Active pages after check: 1`).
- **Evidence:**
  - `python3 -m unittest discover -s tests -q`: 178 tests passed, 2 skipped.
  - Live CDP verification pada profil `aidoto`: tab redundan ditutup, tersisa 1 tab aktif.
  - `git diff --check`: bersih (exit 0).
- **Batas bukti:**
  - Pengujian live draft tetap aman draft-only; tidak menyentuh tombol Publish.
- **Next priority:** INT-01 (Implementasi adapter integrasi `TooLostClient` di repo `yt-to-flowmusic` mengacu pada `docs/INTEGRATION-PLAN.md`).

## CP-021 — Selesai CDP-02 & Rilis 0.1.3: Dukungan Unggah Berkas Audio Besar (>50MB) via is_local di CDP

- **Waktu/owner:** 2026-10-26 22:12 WIB, sesi-cdp-02 / assistant.
- **Baseline:** 1bee2a3 + dirty files (`toolost_uploader/browser.py`, `toolost_uploader/live_draft.py`, `tests/test_browser.py`, `toolost_uploader/__init__.py`, `README.md`, `docs/*`).
- **Status:** CDP-02 `in_progress` → `done`. Claim mandiri dilepas.
- **Hasil/eksekusi:**
  1. Helper `is_local_endpoint`:
     - Menambahkan fungsi helper `is_local_endpoint(endpoint: str) -> bool` di `toolost_uploader/browser.py` untuk mendeteksi apakah koneksi CDP mengarah ke loopback host (`127.0.0.1`, `localhost`, `::1`, subnet `127.*`).
  2. Integrasi `is_local=True` pada `connect_over_cdp`:
     - `toolost_uploader/live_draft.py`: `browser = p.chromium.connect_over_cdp(endpoint, is_local=is_local_endpoint(endpoint))`.
     - `toolost_uploader/browser.py`: `browser = p.chromium.connect_over_cdp(endpoint, is_local=is_local_endpoint(endpoint))`.
     - Efek: Mengangkat batas hardcoded 50MB Playwright (`fileUploadSizeLimit`) saat mengontrol browser CDP lokal, sehingga Chromium membaca path berkas langsung dari filesystem OS (`DOM.setFileInputFiles`). Menghilangkan error `Cannot transfer files larger than 50Mb to a browser not co-located with the server`.
  3. Verifikasi & Pengujian:
     - Tes langsung live CDP dengan file dummy 60MB: terbukti berhasil diunggah tanpa error (`SUCCESS: File >50MB uploaded without error!`).
     - Unit test baru `test_is_local_endpoint` di `tests/test_browser.py` memvalidasi berbagai skenario host loopback dan non-loopback.
     - Seluruh test suite offline lulus 100% (**179 passed**, 2 skipped).
  4. Rilis PyPI 0.1.3:
     - Versi dinaikkan ke `0.1.3` di `toolost_uploader/__init__.py` dan badge `README.md`.
     - `uv build`: Memproduksi `toolost_uploader-0.1.3-py3-none-any.whl` (56.3 kB) dan `toolost_uploader-0.1.3.tar.gz` (81.1 kB).
     - `twine check dist/*`: Lolos `PASSED` 100%.
     - `twine upload`: Berhasil dipublikasikan ke https://pypi.org/project/toolost-uploader/0.1.3/.
- **Evidence:**
  - URL publikasi: `https://pypi.org/project/toolost-uploader/0.1.3/`
  - `twine check dist/*`: PASSED.
  - 179 unit tests offline lulus (2 skipped).
  - `git diff --check`: bersih (exit 0).
- **Batas bukti:**
  - Perbaikan `is_local` berlaku saat endpoint adalah loopback host lokal. Rilis tetap terkunci aman pada batas **draft-only** (tombol Publish dilarang ditekan).
- **Next priority:** INT-01 (Implementasi adapter integrasi `TooLostClient` di repo `yt-to-flowmusic` mengacu pada `docs/INTEGRATION-PLAN.md`).

## CP-020 — Publikasi Rilis 0.1.2 ke PyPI: Optimalisasi Tab Memory & Tab Lyrics

- **Waktu/owner:** 2026-10-26 22:02 WIB, sesi-release-0.1.2 / assistant.
- **Baseline:** b84727f + dirty files (`pyproject.toml`, `toolost_uploader/__init__.py`, `README.md`, `toolost_uploader/browser.py`, `toolost_uploader/live_draft.py`, `tests/*`, `docs/*`).
- **Status:** Publikasi PyPI 0.1.2 `done`.
- **Hasil/eksekusi:**
  1. Version Bump:
     - `toolost_uploader/__init__.py`: dinaikkan ke `0.1.2`.
     - `README.md`: badge PyPI diperbarui ke versi 0.1.2.
  2. Distribusi & Verifikasi Integritas:
     - `uv build`: Memproduksi `toolost_uploader-0.1.2-py3-none-any.whl` (56.0 kB) dan `toolost_uploader-0.1.2.tar.gz` (80.7 kB).
     - `twine check dist/*`: Lolos `PASSED` 100%.
     - `test_packaging.py`: Uji instalasi wheel dan eksekusi clean-venv lulus 100%.
  3. Publikasi Resmi ke PyPI:
     - Mengunggah paket ke https://upload.pypi.org/legacy/ menggunakan API token resmi dari `~/.secrets/pypi-cred.txt`.
     - URL rilis resmi: `https://pypi.org/project/toolost-uploader/0.1.2/`
  4. Verifikasi Live Instalasi Bersih dari PyPI:
     - Diuji di clean venv baru via `uv pip install toolost-uploader==0.1.2`.
     - `toolost --version` mengembalikan `toolost 0.1.2` exit code 0.
     - `toolost --help` menampilkan alur kerja dan subcommands lengkap.
- **Evidence:**
  - URL publikasi: `https://pypi.org/project/toolost-uploader/0.1.2/`
  - `twine check dist/*`: PASSED.
  - Verifikasi instalasi clean-venv PyPI live: OK.
  - 178 unit tests offline lulus (2 skipped).
  - `git diff --check`: bersih (exit 0).
- **Batas bukti:**
  - Rilis 0.1.2 aktif dan live di PyPI produksi dengan fitur optimalisasi memori tab dan otomasi lirik.
  - Alur eksekusi tetap aman dalam batas draft-only; tombol Publish dilarang keras ditekan.
- **Next priority:** INT-01 (Implementasi adapter integrasi `TooLostClient` di repo `yt-to-flowmusic` mengacu pada `docs/INTEGRATION-PLAN.md`).

## CP-021 — Selesai CDP-02 & Rilis 0.1.3: Dukungan Unggah Berkas Audio Besar (>50MB) via is_local di CDP

- **Waktu/owner:** 2026-10-26 22:12 WIB, sesi-cdp-02 / assistant.
- **Baseline:** 1bee2a3 + dirty files (`toolost_uploader/browser.py`, `toolost_uploader/live_draft.py`, `tests/test_browser.py`, `toolost_uploader/__init__.py`, `README.md`, `docs/*`).
- **Status:** CDP-02 `in_progress` → `done`. Claim mandiri dilepas.
- **Hasil/eksekusi:**
  1. Helper `is_local_endpoint`:
     - Menambahkan fungsi helper `is_local_endpoint(endpoint: str) -> bool` di `toolost_uploader/browser.py` untuk mendeteksi apakah koneksi CDP mengarah ke loopback host (`127.0.0.1`, `localhost`, `::1`, subnet `127.*`).
  2. Integrasi `is_local=True` pada `connect_over_cdp`:
     - `toolost_uploader/live_draft.py`: `browser = p.chromium.connect_over_cdp(endpoint, is_local=is_local_endpoint(endpoint))`.
     - `toolost_uploader/browser.py`: `browser = p.chromium.connect_over_cdp(endpoint, is_local=is_local_endpoint(endpoint))`.
     - Efek: Mengangkat batas hardcoded 50MB Playwright (`fileUploadSizeLimit`) saat mengontrol browser CDP lokal, sehingga Chromium membaca path berkas langsung dari filesystem OS (`DOM.setFileInputFiles`). Menghilangkan error `Cannot transfer files larger than 50Mb to a browser not co-located with the server`.
  3. Verifikasi & Pengujian:
     - Tes langsung live CDP dengan file dummy 60MB: terbukti berhasil diunggah tanpa error (`SUCCESS: File >50MB uploaded without error!`).
     - Unit test baru `test_is_local_endpoint` di `tests/test_browser.py` memvalidasi berbagai skenario host loopback dan non-loopback.
     - Seluruh test suite offline lulus 100% (**179 passed**, 2 skipped).
  4. Rilis PyPI 0.1.3:
     - Versi dinaikkan ke `0.1.3` di `toolost_uploader/__init__.py` dan badge `README.md`.
     - `uv build`: Memproduksi `toolost_uploader-0.1.3-py3-none-any.whl` (56.3 kB) dan `toolost_uploader-0.1.3.tar.gz` (81.1 kB).
     - `twine check dist/*`: Lolos `PASSED` 100%.
     - `twine upload`: Berhasil dipublikasikan ke https://pypi.org/project/toolost-uploader/0.1.3/.
- **Evidence:**
  - URL publikasi: `https://pypi.org/project/toolost-uploader/0.1.3/`
  - `twine check dist/*`: PASSED.
  - 179 unit tests offline lulus (2 skipped).
  - `git diff --check`: bersih (exit 0).
- **Batas bukti:**
  - Perbaikan `is_local` berlaku saat endpoint adalah loopback host lokal. Rilis tetap terkunci aman pada batas **draft-only** (tombol Publish dilarang ditekan).
- **Next priority:** INT-01 (Implementasi adapter integrasi `TooLostClient` di repo `yt-to-flowmusic` mengacu pada `docs/INTEGRATION-PLAN.md`).
