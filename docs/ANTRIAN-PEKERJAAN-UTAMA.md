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

*(Tidak ada klaim aktif — seluruh task telah diselesaikan)*

## Checkpoint terbaru

- [CP-020](backlog/CHECKPOINT-HISTORY.md#cp-020--publikasi-rilis-012-ke-pypi-optimalisasi-tab-memory--tab-lyrics): Rilis 0.1.2 ke PyPI produksi; menyertakan fitur optimalisasi memori tab dan otomasi lirik.
- [CP-021](backlog/CHECKPOINT-HISTORY.md#cp-021--selesai-cdp-02--rilis-013-dukungan-unggah-berkas-audio-besar-50mb-via-is_local-di-cdp): CDP-02 done; dukungan is_local di connect_over_cdp mengangkat batas 50MB Playwright; rilis 0.1.3 live di PyPI.
- [CP-022](backlog/CHECKPOINT-HISTORY.md#cp-022--selesai-fin-01--rilis-014-finalisasi-step-pasca-readback-done-track-terakhir-save-changes--kembali-ke-portal): FIN-01 done; tombol Done track terakhir selalu diklik, Save Changes pasca-verifikasi dijalankan, dan browser dinavigasikan kembali ke portal daftar rilis; rilis 0.1.4 live di PyPI.
- [CP-023](backlog/CHECKPOINT-HISTORY.md#cp-023--selesai-upd-01--rilis-015-fitur-update-komprehensif-judul-tanggal-rilis-artwork-metadata-track--append-lagu-susulan): UPD-01 done; dukungan sinkronisasi update komprehensif (judul album, tanggal rilis, artwork, perbaikan lirik/AI/judul lagu, serta append lagu susulan); 188 tes; rilis 0.1.5 live di PyPI.
- [CP-024](backlog/CHECKPOINT-HISTORY.md#cp-024--selesai-upd-02--rilis-016-dukungan-penyisipan-lagu-di-posisi-sembarang--reordering-track): UPD-02 done; kontinuitas update berbasis integritas audio hash (subset) mendukung penyisipan lagu di tengah urutan dan penataan posisi fisik track via drag & drop; rilis 0.1.6 live di PyPI.

Maksimal lima ringkasan terbaru di sini; history lengkap append-only. Jangan memasukkan path privat, ID akun/draft, aset, token, capture atau isi checkpoint runtime ke backlog.
