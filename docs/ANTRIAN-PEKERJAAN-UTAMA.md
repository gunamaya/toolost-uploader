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

REC-04: assistant/rec04-20261106 selesai CP-040; claim dilepas. Verifikasi non-navigation hanya pada page draft yang dipanggil, GET same-origin `/api/auth/me`, exact origin/draft, response bounded/fail-closed, tanpa CLI atau eksekusi.

REC-03: assistant/recovery-20261106 dilepas setelah CP-039; status blocked pada gate provenance identity non-navigation.

## Checkpoint terbaru

- CP-039: REC-03 blocked; fingerprint review dan approval snapshot offline, execution disabled; 217 tes 2 skip.
- CP-040: REC-04 selesai offline; helper same-origin non-navigation dan fake failure tests; 221 tes 2 skip, diff check bersih. Profile/manifest provenance, persisted state, remote hash dan live browser tetap belum terbukti.
- CP-038: REC-02 blocked; pembanding snapshot offline bukan inspeksi browser terikat identity, 216 tes 2 skip; CLI tidak ditambahkan.
- CP-037: TMO-01 selesai offline; adaptive timeout chooser dan deadline observasi batch/append, 213 tes 2 skip, diff check bersih. Tidak live/install/commit.
- CP-036: tes fixture batch/append gagal guard login fake; diperbaiki sebelum CP-037.
- CP-035: tes awal gagal Python sistem tanpa Playwright dan fixture count; diperbaiki sebelum CP-037.






Maksimal lima ringkasan terbaru di sini; history lengkap append-only. Jangan memasukkan path privat, ID akun/draft, aset, token, capture atau isi checkpoint runtime ke backlog.
