# Fake Save terpadu dengan gate approval

## Update: upload persisten bergate

Coordinator kini juga menyediakan `upload_plan`, `execute_upload` dan `reconcile_upload` untuk fixture fake_upload. Plan diambil dari batch exact snapshot checkpoint, operation hanya fake.upload. Target dibaca dari fake server saat execute; approval diverifikasi sebelum prepare, consumed sebelum fake ingest. Mode/revisi salah tidak mengonsumsi approval. Recovery memakai receipt consumed dan hash batch intent, tidak mengulang upload atau consume.

Tes mencakup approval Save ditolak untuk upload, token salah, consume gagal, crash antara consume/execute, before-send not_applied, perubahan identitas setelah ingest, dan subprocess baru yang reconcile pending lalu ready dengan upload_calls tetap satu. Prepared yang stranded tetap fail-closed; tidak ada reset/retry otomatis.

Upload dan Save adalah **dua alur alternatif satu-operasi**, bukan workflow gabungan. Satu approval file per checkpoint membuat keduanya belum dapat dijalankan berantai pada run yang sama. Low-level helper fixture tetap bisa dipanggil langsung; gate bukan security boundary. Membuat rencana multi-operasi/approval history memerlukan keputusan berikutnya, bukan overwrite approval consumed. Semua deskripsi Save-only di bawah merupakan baseline tahap sebelumnya yang tetap berlaku untuk fungsi Save.

Verifikasi update upload bergate: build wheel melalui sdist berhasil, suite lengkap dengan schema/instalasi bersih **100/100 lulus tanpa skip** pada macOS/Python 3.14.7; `git diff --check` bersih. Tidak ada browser atau akun diakses.

`fake_flow.py` menghubungkan approval + journal + exact FakeUI dalam satu coordinator internal. Scope hanya Save atas staging sintetis yang sudah disiapkan; upload/edit staging di fixture masih dilakukan sebelumnya dan **belum tercakup approval coordinator**. Bukan uploader end-to-end, tidak ada browser/network/akun atau command CLI baru.

## Urutan

1. Caller menyiapkan fixture UI, checkpoint, binding sintetis reviewed dan approval untuk `fake_flow.plan(ui)`. Plan hanya fake.save + hash desired projection (title, order, metadata digest).
2. execute mengambil desired dari UI yang siap, memverifikasi exact approval/account/draft/checkpoint/plan. Invalid token/identity/hash menghentikan tanpa Save dan tanpa attempt baru.
3. Prepare intent lokal lewat journal, kemudian consume approval atomik. Jika consume gagal, attempt prepared ditinggalkan; tidak menjalankan Save atau menimpa attempt.
4. journal.execute memeriksa ulang target/baseline, menyimpan unknown sebelum memanggil Save. Outcome/read-back sama dengan OFFLINE-JOURNAL.md. Approval consumed tidak dihidupkan ulang pada timeout/error/crash.
5. fake_flow.reconcile memverifikasi receipt consumed, exact run/checkpoint dan plan yang dibangun dari **desired hash dalam intent**, bukan staging setelah reload. Lalu hanya journal.reconcile; Save tidak dipanggil lagi. Account/draft observation yang berubah menjadi conflict; unknown/incomplete tetap mengikuti jurnal.

verify pada approval.py kini memisahkan validasi receipt dari consume. `consumed=True` hanya verifikasi receipt, bukan approval baru atau izin mutasi. Coordinator tidak menerima FakeAdapter arbitrer, upload/delete/publish atau arbitrary plan.

## Crash dan batas

Approval consume dan intent adalah dua atomic writes, bukan transaksi lintas file. Crash setelah prepare/sebelum consume atau setelah consume/sebelum journal.execute dapat meninggalkan prepared yang tidak dapat dijalankan ulang lewat coordinator. Ini fail-closed, perlu review/recovery policy berikutnya; tidak otomatis mengulang Save. Unknown setelah Save dapat direconcile tanpa consume ulang bila receipt cocok.

Profile lock tetap wajib dan akun/fingerprint nyata masih unresolved. FakeUI persisted hanya object memori; reopen profile bukan server persistence lintas proses. Upload fixture persisten sebelumnya belum dihubungkan ke coordinator ini. Token/hash/boolean review bukan security boundary terhadap proses user yang sama. CLI tetap validate; tidak ada draft_saved produksi, live smoke, publish atau izin commit/push otomatis.

Tes mencakup approved Save sekali, token/plan/identity/revision mismatch nol Save, consume write failure meninggalkan prepared, response hilang + reopen + read-only reconciliation, crash sesudah consume sebelum execute, dan error/conflict read-back. Lihat tests/test_fake_flow.py.

Verifikasi sesi ini pada macOS/Python 3.14.7: build wheel melalui sdist berhasil; suite lengkap dengan schema independen dan instalasi wheel bersih **93/93 lulus tanpa skip**. `git diff --check` bersih. Tidak ada browser atau akun diakses.
