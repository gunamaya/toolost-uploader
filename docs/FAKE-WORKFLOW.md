# Workflow fake tiga langkah dengan satu approval

Pengguna memilih satu approval untuk rencana immutable berurutan. `fake_workflow.py` mengikat checkpoint/run, target sintetis, urutan fake.upload→fake.edit→fake.save dan hash desired ke satu token yang dikonsumsi saat start. Ledger terpisah menyimpan receipt tiap langkah; checkpoint dan approval lama tidak diubah formatnya. CLI tetap validate, tanpa browser/akun/publish.

## Cakupan eksplisit

Model memetakan title release, title track, AI eksplisit dan urutan track dari snapshot manifest. Optional metadata yang belum dipetakan ditolak dengan unsupported_workflow_fields. Artwork, release_type, tanggal adalah input checkpoint yang diikat hash, **bukan field yang diterapkan atau diverifikasi oleh workflow fake ini**. Tidak ada klaim seluruh manifest sudah diupload/tersimpan. FakeUI dan fake server adalah model berbeda dengan handoff eksplisit; bukan DOM atau layanan.

## Alur bounded

- initialize fake server dan binding reviewed dilakukan fixture caller. approve memakai `plan` yang tepat. start memverifikasi token, membuat prepared upload intent serta ledger pending, lalu consume approval; belum upload.
- advance hanya satu langkah: upload menulis ledger unknown sebelum fake ingest. Encoding pending menghentikan langkah berikutnya. settle adalah progression fixture eksplisit, bukan bagian reconcile.
- reconcile upload hanya membaca server dan memperbarui receipt; partial/failed/duplicate identity tetap unknown. Applied upload hanya berarti batch ready, bukan urutan sudah cocok.
- advance edit memverifikasi batch/identity terbaru, menulis unknown, kemudian handoff fixture ke staging metadata/urutan manifest dan menyimpan receipt applied. Bukan action browser/DOM. Edit receipt bukan Save/persistence.
- advance Save memverifikasi staging masih tepat, membuat intent Save dan ledger unknown, menjalankan jurnal Save lalu mencatat outcome. Unknown tidak menjalankan langkah berikutnya atau retry.
- reconcile Save menerima terminal receipt jurnal yang sudah tersimpan walau update ledger gagal; tidak Save ulang. Jika receipt masih unknown, jalankan read-back jurnal. Satu token consumed diverifikasi ulang terhadap rencana/checkpoint pada setiap operasi.

## Crash dan batas keamanan

Tidak ada transaksi lintas approval, ledger dan intent: crash saat start/prepare Save dapat meninggalkan prepared stranded. Fail-closed, tidak auto-adopt/reset. Crash edit atau kegagalan receipt edit meninggalkan unknown: staging memori bukan bukti persistensi dan tidak dipromosikan otomatis. Reopen UI setelah edit membuat staging hilang/berubah dan memblokir Save, bukan merekonstruksi edit diam-diam. Upload persisted lintas proses; Save/UI persisted tetap object memori. Bukan workflow recovery lengkap lintas proses.

Ledger hash/permission/lock mengikuti storage. Approval adalah aturan caller kooperatif, bukan capability terhadap proses user yang sama. Helper low-level tetap fixture internal; tidak ada executor nyata atau account binding UI terverifikasi. Tidak ada renewal/replan/retry otomatis, create/delete/publish, atau approval history. Terminal not_applied/conflict juga menghentikan workflow.

Tes: satu token/tiga receipt, pending blok edit, resume profile setelah upload, staging hilang, respons Save hilang/reconcile read-only, write sebelum upload, not_applied tanpa retry, token consumed/identity mismatch, unmapped field ditolak, receipt Save tersimpan tetapi ledger gagal, dan receipt edit gagal tetap unknown. Semua temporary/sintetis.

Verifikasi sesi ini pada macOS/Python 3.14.7: build wheel melalui sdist berhasil; suite lengkap dengan schema independen dan instalasi wheel bersih **110/110 lulus tanpa skip**. `git diff --check` bersih. Tidak ada browser atau akun diakses.
