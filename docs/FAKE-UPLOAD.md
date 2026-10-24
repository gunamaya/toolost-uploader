# Recovery fake upload persisten offline

Tahap lanjutan sesudah commit fake UI `476512b`: `toolost_uploader/fake_upload.py` + tes offline. Tidak ada browser/akun/network, audio tidak dikirim atau dibaca oleh fixture. CLI tetap validate. Ini modul fixture internal, bukan adapter layanan atau kontrak integrator.

## Model kecil

- Batch berasal dari snapshot manifest checkpoint: track_id, basename path audio, SHA-256 lokal. Tidak menerima arbitrary payload/kredensial. Identitas track di sini tersedia secara sintetis; tidak membuktikan remote ID Too Lost atau hash media remote.
- `initialize` membuat fake-server JSON privat kosong, terikat exact run/checkpoint hash. Existing/corrupt fixture tidak ditimpa. Fake server dan intent terpisah dalam directory checkpoint ber-lock yang sama.
- `prepare` memerlukan checkpoint validated dan exact revision, identitas sintetis cocok, server kosong/belum upload. Satu upload-attempt per checkpoint; tidak ada reset/retry/history.
- `execute` memeriksa ulang identity/baseline, menyimpan unknown atomik/fsync **sebelum** menulis ingest fake. Fault intent write termasuk outcome unknown menghentikan upload. Existing unknown/applied/not_applied/conflict tidak boleh execute lagi.
- Modes pending/lost_response menulis batch terbalik dengan encoding pending dan upload_calls=1; partial hanya menulis sebagian; before_send tidak menulis server. Pending/lost_response sengaja setara pada persistent state: response bukan bukti ingest/encoding selesai.
- `settle` adalah aksi fixture-only eksplisit yang memajukan pending→ready/failed, bukan proses rekonsiliasi. Failed tidak dipromosikan menjadi ready oleh settle ulang. Tidak ada timer otomatis.
- `reconcile` hanya membaca server, tidak upload atau memajukan encoding. Semua track harus lengkap, cocok batch dan ready agar applied. Basename/ID duplikat, partial ingest atau pending/failed tetap unknown; foreign track/identity mismatch conflict. Kosong dan upload_calls=0 menjadi not_applied, tetap tanpa izin retry otomatis.
- Applied hanya mencakup batch upload sintetis, **bukan urutan sesuai manifest, metadata tersimpan, artwork atau Save release**. Urutan terbalik tetap teramati; tidak disortir diam-diam. FakeUI/Save journal sebelumnya belum disatukan dengan fixture upload ini menjadi executor multi-operation.

## Persistence dan keamanan

Record memakai storage 0700/0600, owner/symlink/hardlink guards, lock per profile, canonical record hash dan atomic write yang sama. Unknown/duplicate keys dan corruption ditolak. SHA-256 mendeteksi korupsi bukan autentikasi terhadap proses user yang sama. Tidak ada endpoint, cookie, path audio lengkap atau lyrics dalam server/jurnal; basename adalah metadata privat dari manifest.

Fake-server bertahan lintas proses karena JSON lokal, bukan proses layanan sungguhan. Ini menguji recovery control flow setelah journal dan simulated ingest terpisah; tidak membuktikan transaksi server atau power-loss filesystem. Checkpoint berubah/cancelled/run mismatch menutup akses fixture lama. Asset snapshot belum immutable; executor nyata nanti tetap harus verifikasi/snapshot aset dan identitas akun.

## Tes

Verifikasi sesi ini: build wheel melalui sdist berhasil; suite lengkap `TOOLOST_TEST_DIST_DIR=dist .local/packaging-venv/bin/python -m unittest discover -s tests -q` **79/79 lulus tanpa skip** pada macOS/Python 3.14.7. `git diff --check` bersih. Tidak ada browser atau akun diakses.

Tes subprocess baru membaca pending dari disk, settle fixture, reconcile applied, lalu memastikan upload_calls tetap 1. Fault injection sesudah ingest commit dan sebelum respons, fsync intent gagal sesudah rename, write sebelum intent, read-only reconcile berulang, partial/failed encoding, duplicate basename, identity mismatch, run/attempt/batch/format/corruption guards semuanya offline dengan temporary directory.

Tidak ada create recovery, multi-batch/multi-attempt, account binding, approval, Playwright atau live smoke. Tahap berikutnya yang masuk akal: review kontrak binding/approval dan skenario fake multi-operation sebelum menambahkan executor nyata. Tidak ada izin commit/push baru otomatis.
