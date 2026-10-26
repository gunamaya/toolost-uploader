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

## RES-01 — Resume mutasi produksi (deferred)

- **Masuk setelah aktivasi user:** tentukan bounded operasi yang boleh dilanjutkan, identitas remote yang diperlukan dan perilaku unknown/conflict. Reuse executor/journal existing; jangan menyalin scheduler FlowStudio.
- **Keluar:** implementasi otomatis hanya karena REC-01 selesai; retry buta create/upload/Save; izin live/publish implisit.
- **Acceptance sebelum mulai implementasi:** scope konkret dipilih user, plan/field/target jelas, verifier offline dan izin live terpisah bila diperlukan. Detail belum ditetapkan, bukan task implementasi siap jalan.

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
