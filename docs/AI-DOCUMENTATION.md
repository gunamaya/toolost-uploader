# AI Documentation: reproduksi issue tanpa respons

Observasi 2026-10-25 melalui Chrome profil riset + Playwright CDP. Tidak menekan Publish/distribusi dan tidak mengisi bukti hak palsu.

## Reproduksi

- Draft riset tersimpan awalnya memiliki AI-assisted=false dan 1 issue Release Format.
- Dibuka Edit track, Information; AI-assisted diaktifkan via fokus + Space dan Done.
- Sidebar menjadi 2 issues: Release Format dan AI Documentation / AI assistance details required.
- Klik AI Documentation dilakukan melalui tombol UI normal.
- ARIA snapshot body sebelum/sesudah identik setelah menunggu 1 detik. Tidak ada pageerror JavaScript tertangkap selama reproduksi. Ini tidak membuktikan tidak ada masalah network/console atau backend; belum merekam jaringan.
- Tidak ada form AI Documentation yang terlihat muncul. Bukan kesalahan pengguna yang sudah terbukti.

## Temuan read-only DOM

- Ada Release review notes dengan teks yang menyebut beat licenses, sample clearances, generative AI approvals, label waivers, capitalization requests.
- Berisi switch No, Note, dan Attach optional file (Image, Text or PDF); accept aktual PNG/JPEG/PDF. Teks label vs accept juga tidak sepenuhnya konsisten.
- Seluruh bagian berada di `.distribution-page--preview` dengan display:none, bersama heading Publish your release dan tombol Publish release.
- Preview Release yang pernah diuji membuka modal ringkasan, bukan otomatis menampilkan panel lama ini. Belum diketahui apakah review notes dipakai validator AI Documentation atau panel tidak aktif/legacy.
- TIDAK memaksa menampilkan DOM tersembunyi, memanggil handler internal, mencoba endpoint, atau menekan Publish untuk membuka bagian itu. Tidak boleh menyarankan panel tersebut sebagai solusi terverifikasi.

## Dampak AI-assisted lain

Release Information menampilkan alert AI-assisted tracks detected / some platforms automatically excluded. Content ID, Meta Rights Manager, Udio dan Managed Media menjadi disabled dengan alasan AI-assisted. Counter masih menampilkan 479/479 pada sesi ini; counter tidak cukup sebagai bukti exclusions sudah tersimpan/diterapkan. Keadaan layanan bisa berubah otomatis ketika deklarasi diubah; integrator harus membaca ulang state efektif, bukan hanya checkbox AI.

## State akhir dan langkah aman

AI-assisted=true dalam state editor saat observasi; agen belum menekan Save Changes/Save untuk perubahan sesi ini. Efek autosave internal belum dipisahkan. Jangan menyebutnya sudah persisted tanpa reload/read-back.

Langkah berikutnya: laporkan ke Too Lost Support bahwa issue AI Documentation tidak membuka form, sertakan teks issue dan screenshot yang disensor bila pengguna mengizinkan. Minta lokasi resmi pengisian serta dokumen yang dibutuhkan untuk provider/model yang benar-benar digunakan. Izin komersial provider, identitas akun/plan dan ketentuan tidak boleh direka.

Sumber resmi yang ditemukan: https://help.toolost.com/hc/en-us/articles/42469065275924-Does-Too-Lost-Distribute-AI-Music . Fetch langsung403; indeks mengonfirmasi AI music diterima dengan QC dan tidak dijamin semua DSP. Persyaratan dokumen lengkap belum diperoleh.

Bukti privat: `.local/captures/ai-documentation/` (before.yml, after.yml, release-information.yml). Jangan commit/share data akun.

## Perbaikan script observasi

Chrome sempat meninggalkan SingletonLock yang menunjuk PID mati di hostname lokal. Pemeriksaan script kini membiarkan Chrome menangani stale lock tersebut tanpa menghapusnya, dan tetap menolak pemilik hidup/tidak dikenal/host lain. Empat tes unittest offline lulus. Lock native Chrome tetap otoritas terakhir terhadap race/PID reuse.
