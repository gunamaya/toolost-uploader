# Fake UI draft offline

`toolost_uploader/fake_ui.py` adalah model state Python deterministik, bukan halaman HTML/DOM, Playwright adapter atau layanan Too Lost. Pengguna menyetujui tahap offline ini; tidak ada browser, akun, upload aset nyata atau publish. CLI tetap hanya `validate`.

## Yang dimodelkan

- Main → upload dialog → browse/file chooser → selected → Upload sekali. Progress langsung 100% tetapi encoding belum selesai; `tick()` eksplisit menyelesaikan encoding setelah jumlah tick konfigurasi, tanpa sleep/network.
- Ingest dibalik dari urutan pilihan untuk fixture adversarial, bukan klaim aturan sorting layanan. Reorder memerlukan pemetaan ID sintetis yang lengkap dan unik.
- Title awal dari basename dan AI false hanya baseline sintetis. Basename duplikat memblokir mapping/desired/reorder/save dengan `reconciliation_required`, bukan ditebak atau diupload ulang. Ini tidak menyelesaikan remote track identity.
- Track editor dan main memiliki visibility delay; read/write sebelum tick yang diperlukan atau scope panel salah ditolak. ID track disimpan terpisah dari nama panel. `native_checked` tetap false ketika ARIA/panel AI true: tes memakai read-back semantik, tidak force click/DOM mutation.
- Edit/Done dan release title hanya staged. `reopen()` mengembalikan persisted baseline, sehingga Done tanpa Save bukan bukti tersimpan. Ingest pada model ini juga staged dan hilang saat reopen sebelum Save: sengaja sederhana, bukan janji perilaku ingest remote yang bisa bertahan terpisah.
- Save route: dialog (satu konfirmasi sintetis), navigation, error-before-save, lost-response-after-save, metadata-loss. Tidak ada tombol Try again otomatis atau Publish.

## Integrasi jurnal

Jurnal menerima hanya exact `FakeAdapter` atau `FakeUI`, bukan duck-typed browser adapter. Operasi tetap `fake.save`; format jurnal/checkpoint lama tidak berubah. Proyeksi FakeUI menambah `metadata_sha256` pada `{title, track_ids}`. Digest metadata meliputi title track, AI, basename dan ID sintetis, sehingga urutan cocok tetapi AI gagal persist menghasilkan conflict, bukan applied.

Prepare/read-only baseline memakai persisted state, bukan staged. Desired diambil dari staging yang sudah siap dan tidak ambigu. Execute wajib menyimpan unknown sebelum save; save response sukses diikuti observasi persisted. Save error/lost response menghasilkan unknown lalu reconcile tanpa save kedua. Incomplete/ambiguous read-back tetap unknown; mismatch account/draft memblokir atau conflict. Checkpoint tetap validated dan remote binding null: tidak mengklaim `draft_saved` produksi.

Upload dan reorder **belum dijurnal** oleh model ini: jurnal hanya membungkus Save. `upload_attempted` mencegah pengulangan upload dalam object yang sama, bukan recovery upload aman lintas proses. Tick, object persisted, dialog confirmation dan read-back adalah mekanisme sintetis dalam memori; tidak membuktikan selector, event browser, timing server atau persistence lintas proses. Observation tidak otomatis reopen UI; ia membaca salinan persisted sintetis, sementara tes reopen memeriksa field/order kembali.

## Tes dan batas berikutnya

Update lanjutan: fixture upload terpisah dengan server JSON persisten + intent atomik tersedia, lihat FAKE-UPLOAD.md. FakeUI ini tetap in-memory; belum diubah menjadi executor multi-operation atau adapter browser.

Verifikasi sesi ini pada macOS/Python 3.14.7: build wheel melalui sdist berhasil; `TOOLOST_TEST_DIST_DIR=dist .local/packaging-venv/bin/python -m unittest discover -s tests -q` **70/70 lulus tanpa skip**, termasuk schema independen dan instalasi wheel bersih. `git diff --check` bersih.

Tes `tests/test_fake_ui.py`: modal/scope, progress vs encoding, reverse ingest/reorder, delayed fields, ARIA/native mismatch, unsaved Done, Save dialog/navigation/error/lost response, metadata persistence, duplicate names, incomplete/identity mismatch, no retry/reupload, dan journal write-before-save. Semua media/state sintetis dan temporary directory.

Belum ada upload/create journal multi-operation, browser adapter, UI selector fixture HTML, approval, binding akun/remote track, partial encoding recovery lintas proses atau live smoke. Tahap berikutnya perlu memilih cakupan itu secara eksplisit; jangan menghubungkan FakeUI ke akun nyata. Referensi bukti historis: MULTI-TRACK.md, SAVE-FAILURE.md dan UNSAVED-STATE.md.
