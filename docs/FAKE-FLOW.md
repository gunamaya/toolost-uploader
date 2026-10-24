# Fake Save terpadu dengan gate approval

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
