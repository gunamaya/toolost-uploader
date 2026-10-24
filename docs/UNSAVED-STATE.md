# Uji unsaved state: judul release dan Done track

Observasi 2026-10-25. Pengguna meminta lanjut uji resume. Sebelum tindakan dikomunikasikan bahwa uji memakai perubahan judul sementara dan reload, bukan upload/distribusi. Tidak Publish, Create Release, upload, delete, modifikasi profil, atau logout.

## Baseline

Browser CDP awal tidak tersedia; panggilan gagal sebelum mutasi. Mode observe dibuka ulang memakai profil riset. Draft target dipilih melalui daftar rilis dan ID Edit yang sudah diketahui; judul baseline harus cocok tepat atau script berhenti. Dua track serta urutan baseline dari MULTI-TRACK.md dipakai untuk assert akhir.

## Release title tanpa Save

1. Basic Information: baca judul asli dan simpan baseline privat.
2. Tambahkan suffix ` - UNSAVED PROBE` pada Album name, Tab untuk blur, tunggu2.5detik.
3. Verifikasi input lokal berubah; tidak klik Save Changes.
4. Reload; tunggu field visible dan baca ulang.
5. Judul kembali persis baseline asli. Dua track dan urutan tetap cocok.

Hasil: perubahan judul release tidak bertahan setelah reload pada window uji2.5detik ini. Tidak perlu menulis ulang baseline karena reload sudah memulihkannya. Ini bukan bukti bahwa semua field tidak pernah autosave atau debounce yang lebih lama tidak ada.

## Track title + Done tanpa Save Changes

1. Edit track pertama yang basename judulnya cocok baseline.
2. Tambahkan suffix probe pada Track name, blur, klik Done.
3. Daftar track lokal menunjukkan judul probe; tunggu2.5detik. Tidak Save Changes.
4. Reload dan buka Manage Tracks.
5. Judul pertama kembali baseline asli, tepat dua track dalam urutan semula.

Hasil: Done menampilkan perubahan pada state daftar lokal tetapi perubahan judul itu tidak bertahan reload pada uji ini. Done BUKAN bukti metadata tersimpan ke server. Tidak Save tambahan atau modifikasi pemulihan karena baseline sudah kembali.

## Implikasi checkpoint dan resume

- Pisahkan staged/local edits, editor Done, permintaan Save, dan read-back remote terverifikasi.
- Jangan menulis checkpoint metadata persisted setelah fill/blur/Done saja.
- Setelah restart/reload, bandingkan desired manifest dengan state tersimpan; perubahan yang belum Save mungkin perlu diterapkan kembali setelah konflik perubahan manual diperiksa.
- State judul yang pulih tidak menguji apakah file upload sudah masuk library secara independen. Jangan menerapkan ulang Upload sebagai bagian umum replay metadata.
- Tidak sengaja memutus transfer/Save, tidak crash browser, tidak merusak sesi. Failure recovery lainnya tetap unknown.
- Sebelum mengubah state nyata, simpan baseline minimal privat dan hentikan jika identitas/state tidak cocok. Jika probe bertahan, perlu pemulihan dan read-back; cabang pemulihan itu tidak dieksekusi karena kedua probe tidak bertahan.

## State akhir

Draft pengganti sama, judul release asli, dua track berjudul basename asli dalam urutan Terangnya Belum Pulang → Sungai Teh Susu; tanpa artwork. Tidak ada judul probe tersisa dalam read-back. Metadata final termasuk lirik/AI masih belum diterapkan; bukan release-ready.

Bukti privat `.local/captures/unsaved-resume/`: baseline.json, before-reload.yml, after-reload.yml, result.json, track-after-done.yml, track-result.json, track-final.yml. Dua skenario live read-back lulus. Tidak ada tes pemulihan upload atau Publish dilakukan.
