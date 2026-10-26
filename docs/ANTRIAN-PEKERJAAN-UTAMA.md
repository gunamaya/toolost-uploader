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
| GOV-01 | P1 | done | Adopsi lifecycle task/backlog/checkpoint dari yt-to-flowmusic | CP-003; docs-only |
| REC-01 | P1 | done | Hardening recovery executor + regresi offline | Implementasi 684acd6; batas offline CP-001 |
| CLI-01 | P2 | done | Review subset draft CLI dan kontrak integrator yang benar-benar didukung | Hasil di CLI-REVIEW.md; CP-005 |
| CLI-02 | P2 | done | Subcommand CLI toolost upload --draft-only untuk Album (multi-track) | Implementasi CLI & live_draft; 161 tes; CP-007 |
| RES-01 | P2 | deferred | Resume mutasi produksi | User memilih scope setelah CLI-01/02; bukan perluasan hardening otomatis |
| LIVE-02 | P2 | done | Verifikasi live Playwright Album multi-track sesudah implementasi CLI-02 | Sukses live draft Album exit 0; 162 tes; CP-011 |
| PUB-01 | P3 | deferred | Implementasi publish/distribusi | Persetujuan eksplisit terpisah; tidak masuk executor saat ini |

Alasan urutan: tata kerja dulu, kemudian review command/integrasi sesuai arah produk. Tidak menambah hardening/refactor otomatis. Smoke draft sukses tidak diulang. Resume dan publish belum diaktifkan; rights/artist/services/AI Documentation otomatis di luar scope.

## Register klaim aktif

Tidak ada klaim aktif saat ini. Seluruh task ready/in_progress pada siklus ini telah selesai.

## Checkpoint terbaru

- [CP-007](backlog/CHECKPOINT-HISTORY.md#cp-007--selesai-cli-02): CLI-02 done; toolost upload --draft-only Album multi-track; 161 tes.
- [CP-008](backlog/CHECKPOINT-HISTORY.md#cp-008--mulai-live-02): claim intake LIVE-02 verifikasi live draft Album multi-track.
- [CP-009](backlog/CHECKPOINT-HISTORY.md#cp-009--blocker-live-02-sesi-browser-401-unauthorized): blocker 401 Unauthorized pada preflight akun; ditahan.
- [CP-010](backlog/CHECKPOINT-HISTORY.md#cp-010--implementasi-verbose-progress-logging-cli--draftui): penambahan flag --verbose CLI & logging progress DraftUI ke stderr; 162 tes.
- [CP-011](backlog/CHECKPOINT-HISTORY.md#cp-011--selesai-live-02-verifikasi-live-playwright-draft-album-multi-track): LIVE-02 done; verifikasi live draft Album multi-track sukses exit 0 (draft ID 2004317); 162 tes.

Maksimal lima ringkasan terbaru di sini; history lengkap append-only. Jangan memasukkan path privat, ID akun/draft, aset, token, capture atau isi checkpoint runtime ke backlog.
