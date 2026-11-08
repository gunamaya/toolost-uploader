# Antrean pekerjaan utama Toolost Uploader

Current index pekerjaan engineering, **bukan queue upload runtime**. Status, prioritas, dependency dan klaim hanya authoritative di sini. Detail acceptance ada di [TASK-DETAILS.md](backlog/TASK-DETAILS.md), bukti/checkpoint di [CHECKPOINT-HISTORY.md](backlog/CHECKPOINT-HISTORY.md). Dokumen riset/kontrak/plan lama adalah sumber, bukan antrean tandingan.

## Cara kerja

1. **Rencanakan:** baca indeks, klaim, maksimal lima checkpoint terbaru dan sumber task terkait. Cari overlap berdasarkan hasil/scope. Daftarkan ID stabil, scope masuk/keluar, dependency, acceptance, verifier dan izin sebelum implementasi.
2. **Antrekan:** prerequisite/izin mengalahkan prioritas. `ready` dapat diklaim; `blocked` menunggu blocker; `deferred` tidak otomatis diaktifkan. Task selesai tidak diulang tanpa regresi konkret.
3. **Kerjakan:** tandai `in_progress`, catat claim sebelum edit: owner/session, waktu, HEAD+dirty paths, exact files, tes dan stop condition. Satu implementation slice utama; reviewer read-only boleh paralel. Penulis indeks/checkpoint satu koordinator.
4. **Checkpoint:** saat scope berubah, tes gagal, blocker muncul atau handoff. Jangan mengambil perubahan/klaim tidak dikenal; tandai `needs_reconciliation` dan minta handoff jika ownership tidak jelas.
5. **Selesaikan:** `done` hanya bila seluruh acceptance task terpenuhi pada perubahan terakhir. Catat command/hasil/batas verifikasi, remaining dan satu rekomendasi berikutnya. Lepas claim sendiri saja. Selesai task bukan izin otomatis menjalankan task berikutnya.

Status: `ready`, `in_progress`, `blocked`, `needs_reconciliation`, `done`, `deferred`, `superseded`. Partial tetap aktif/blocked dengan sisa eksplisit atau dipecah child, bukan disebut done. Claim Markdown bukan atomic lock lintas agen.

## Urutan current

| ID | Prioritas | Status | Hasil pekerjaan | Prasyarat / gate |
|---|---|---|---|---|
| REC-07 | P1 | blocked | Binding ID remote, executor recovery dan successor terimplementasi | CP-055 offline selesai; verifikasi portal end-to-end belum dijalankan |
| REC-06 | P1 | done | Recovery existing offline: review judul toleran unik dan inspeksi aman | CP-048; mutasi tetap bergantung bukti identitas audio dan persistensi |
| UPD-05 | P1 | done | Perbaikan identitas label track berawalan angka | CP-043; verifikasi offline |
| REC-05 | P1 | blocked | Rekonsiliasi upload existing sebelum retry | CP-047; identitas audio dan persistensi remote belum terbukti, retry belum terintegrasi |
| UPD-04 | P1 | needs_reconciliation | Perbaikan viewport dan hit test untuk adjacent drag | User mengonfirmasi tidak ada agent aktif; validasi final tersendiri belum dilakukan |
| REC-04 | P1 | done | Verifikasi akun non-navigation terbatas untuk page draft | CP-040; provenance profile/manifest tetap di luar scope |
| REC-03 | P1 | blocked | Recovery review dua tahap offline, tanpa reupload | Provenance account/profile/draft dari page aktif belum terbukti; fail closed |
| REC-02 | P1 | blocked | Inspeksi recovery read-only tanpa navigasi | CP-038: pembanding snapshot saja; provenance account/profile browser belum terbukti |
| TMO-01 | P1 | done | Timeout audio adaptif ukuran untuk batch dan append | CP-037 offline; bukan bukti live |
| UPD-03 | P1 | blocked | Reorder-only berhenti pre-drag karena existing dialog kosong CP-034 | Perlu review/tutup dialog oleh user; tanpa reload/Save/upload |
| UPL-01 | P1 | blocked | Upload serial opt-in dan journal per-track; boundary buffer | REM-22 integrator; offline only, no resume mutasi |
| GOV-01 | P1 | done | Adopsi lifecycle task/backlog/checkpoint dari yt-to-flowmusic | CP-003; docs-only |
| REC-01 | P1 | done | Hardening recovery executor + regresi offline | Implementasi 684acd6; batas offline CP-001 |
| CLI-01 | P2 | done | Review subset draft CLI dan kontrak integrator yang benar-benar didukung | Hasil di CLI-REVIEW.md; CP-005 |
| CLI-02 | P2 | done | Subcommand CLI toolost upload --draft-only untuk Album (multi-track) | Implementasi CLI & live_draft; 161 tes; CP-007 |
| RES-01 | P2 | superseded | Resume mutasi produksi | Tidak diperlukan; fail-stop idempotensi + eksekusi ~50s lebih aman; CP-012 |
| LIVE-02 | P2 | done | Verifikasi live Playwright Album multi-track sesudah implementasi CLI-02 | Sukses live draft Album exit 0; 162 tes; CP-011 |
| ENV-01 | P2 | done | Subcommand setup, check (readiness), dan auto-bootup Chrome CDP | Sukses check readiness & 171 unit tests; CP-013 |
| INT-01 | P2 | ready | Rencana & spesifikasi adapter integrasi subprocess yt-to-flowmusic | Selesainya CLI-02 & LIVE-02; integrasi manifest JSON & ProcessRunner |
| PKG-01 | P2 | done | Persiapan packaging, metadata, lisensi, sanitasi sdist/wheel, dan rilis PyPI | Build sdist/wheel bersih, lolos twine check & 171 tes; CP-014 |
| LYR-01 | P2 | done | Dukungan tab Lyrics di Playwright live executor | Sukses live draft Album dengan lirik profil aidoto; CP-018 |
| TAB-01 | P2 | done | Optimalisasi tab browser CDP: reuse tab aktif & tutup tab redundan | Sukses reuse tab & cleanup redundan; 178 tes; CP-019 |
| CDP-02 | P2 | done | Dukungan unggah berkas audio besar (>50MB) via is_local di CDP | Sukses bypass limit 50MB; 179 tes; rilis 0.1.3; CP-021 |
| FIN-01 | P2 | done | Finalisasi step pasca-readback: Done track terakhir, Save Changes, & kembali ke portal | Sukses Done, Save, & navigasi portal; 180 tes; rilis 0.1.4; CP-022 |
| UPD-01 | P2 | done | Fitur update metadata & append track otomatis ke draft existing | Sukses update & append; 188 tes; rilis 0.1.5; CP-023 |
| UPD-02 | P2 | done | Dukungan penyisipan lagu di posisi sembarang & reordering track | Sukses validasi audio subset & reorder; 188 tes; rilis 0.1.6; CP-024 |
| PUB-01 | P3 | deferred | Implementasi publish/distribusi | Persetujuan eksplisit terpisah; tidak masuk executor saat ini |

Alasan urutan: tata kerja dulu, kemudian review command/integrasi sesuai arah produk. Tidak menambah hardening/refactor otomatis. Smoke draft sukses tidak diulang. Resume dan publish belum diaktifkan; rights/artist/services/AI Documentation otomatis di luar scope.

## Register klaim aktif

REC-07: assistant/recovery-finish-20261108 dilepas CP-055. Implementasi offline selesai; acceptance portal tidak diklaim. HEAD d71851c + dirty handoff dipertahankan.

REC-07: assistant/rec07-receipt-20261108 dilepas CP-054; GUI dan retry tetap blocked.

REC-07: assistant/rec07-collision-20261108 dilepas CP-053; receipt dan retry tetap blocked.

REC-07: assistant/rec07-integration-20261108 dilepas CP-052; receipt dan retry masih blocked.

REC-07: assistant/rec07-guard-20261108 dilepas CP-050; runtime binding belum tersedia.

REC-07: assistant/rec07-20261108 dilepas CP-049; klaim awal HEAD d71851c, dirty paths tercatat di history.

REC-06: assistant/rec06-20261108 dilepas CP-048; klaim awal HEAD d71851c dan dirty paths dicatat di history.

REC-05: assistant/rec05-takeover-20261108 dilepas CP-047; resume mutasi tetap blocked.

UPD-04: klaim lama dilepas berdasarkan konfirmasi user bahwa tidak ada agent aktif; acceptance tetap needs_reconciliation.

UPD-05: assistant/takeover-20261108 selesai CP-043; klaim dilepas.

REC-04: assistant/rec04-20261106 selesai CP-040; claim dilepas. Verifikasi non-navigation hanya pada page draft yang dipanggil, GET same-origin `/api/auth/me`, exact origin/draft, response bounded/fail-closed, tanpa CLI atau eksekusi.

REC-03: assistant/recovery-20261106 dilepas setelah CP-039; status blocked pada gate provenance identity non-navigation.

## Checkpoint terbaru

- CP-055: recovery CLI/receipt/ID ledger/successor terintegrasi, snapshot relocatable termasuk lirik; 275 tests, 273 passed, 2 skipped. GUI REC-08 terhubung; live belum diverifikasi.
- CP-051: REC-07 tetap blocked; tidak ditemukan kontrak endpoint track respons 200 pada evidence lokal yang diperiksa, tidak mengarang API atau menjalankan portal.
- CP-049: REC-07 helper review binding offline parsial; belum terintegrasi, retry tidak tersedia, suite sistem gagal karena Playwright tidak terpasang.
- CP-048: REC-06 inspeksi page tanpa navigasi dan review judul unik lolos offline; retry tetap blocked.
- CP-047: REC-05 perbaikan ambiguitas akhiran Edit lolos offline; retry belum terintegrasi dan tetap blocked.
- CP-046: REC-05 account verified pada konteks sama; track panel dan identitas audio belum terbukti.






Maksimal lima ringkasan terbaru di sini; history lengkap append-only. Jangan memasukkan path privat, ID akun/draft, aset, token, capture atau isi checkpoint runtime ke backlog.

## FIX-30 — in_progress
- Claim assistant/fix-review-path-20261109: HEAD 0c39eb1, clean baseline. Files validation.py, tests/test_cli.py, backlog; intended unittest suite, read-only review source/frozen dan installed signature. Root cause load_manifest(str) memanggil str.open pada wrapper review-binding --profile. Tanpa mutasi portal atau commit/push.
- FIX-30 done CP-056; assistant/fix-review-path-20261109 dilepas. CLI berprofil source/frozen/installed berhasil, app rebuilt dan dipasang; proses lama perlu reopen.

## FIX-33 — in_progress
- assistant/crash-binding-20261109, HEAD0c39eb1+dirty FIX30 dipertahankan. Active Vue editor transfer observation and deferred numeric binding after normal Save; no duplicate on unsaved state. Backend281tests279passed2skipped. No portal mutation/commit; rebuild/install.
- FIX-33 done CP-057 offline/package; active unsaved state observed without navigation, binding after normal Save;281tests279passed2skipped; rebuilt installed. Claim released; no automatic retry existing unsaved draft.
