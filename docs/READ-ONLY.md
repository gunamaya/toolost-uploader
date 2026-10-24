# Snapshot release read-only — bukti live terbatas

Pengguna mengizinkan observasi read-only pada sesi lanjutan setelah workflow fake. Chrome profil riset sudah aktif di loopback 9437; Playwright tersedia pada environment riset. Tidak ada login otomatis, pembacaan cookie/password, upload, Create, Save, Delete, Publish, perubahan profil atau library. Tidak memasang dependency baru.

## Observasi yang benar-benar dilakukan

- Discovery menemukan editor draft riset aktif. Inspeksi pasif memeriksa guard password/dialog dan struktur kontrol tanpa nilai input. Tidak ada screenshot/login capture.
- Link root yang teramati membuka situs publik, bukan dashboard; ini bukan bukti session expired. Kemudian jalur All Releases yang sudah diverifikasi UI-MAP.md dibuka langsung.
- Daftar awal belum siap; pembacaan ulang setelah landmark terlihat menghasilkan satu kartu release, title link detail dan link Edit/View. ID remote berasal dari href UI, bukan judul. Tidak klik Edit, trash, Create, filter atau pagination.
- Membuka detail melalui link View teramati menghasilkan hero title, exact edit href yang cocok target, dan satu track row. Tidak ada atribut data-ID track pada baris yang diperiksa. Tidak menebak ID track dari basename/judul.
- Collector baru diuji pasif pada detail: partial, satu track row, account_verified=false. Smoke list: partial, satu kartu dan ID teramati. Setelah smoke list, halaman dikembalikan ke detail View, bukan editor yang mungkin staged.
- Tidak ditemukan fingerprint akun stabil pada link/struktur yang diperiksa. Ini pencarian bounded, bukan bukti semua UI tidak memiliki identitas akun. Settings/profil tidak dibuka; nama artist tidak dipakai untuk binding. Remote status mapping belum diterapkan collector meskipun riwayat riset memverifikasi Draft.

Bukti mentah/proyeksi berisi identitas tetap privat di `.local/read-only/`, mode 0600, folder 0700. Tidak masuk git/fixtures. Tidak menyimpan header/body network/credentials. Satu discovery CDP memakai REA; collector utama memakai Playwright dan DOM evaluation read-only.

## Implementasi tersedia

### Follow-up sumber identitas akun

Sesudah commit/push adapter read-only, pengguna mengizinkan melanjutkan observasi. Link Settings yang tampak di detail diverifikasi menuju `/user-portal/profile`. Navigasi GET dibatasi pada halaman tersebut, tanpa klik atau membaca nilai input. Guard prompt autentikasi/dialog aktif menghentikan inspeksi sebelum struktur label disimpan; penyebab spesifik (prompt vs dialog) belum terklasifikasi. Tidak ada identity snapshot tersimpan dari percobaan ini, tidak ada modal ditutup/dilewati. `finally` mengembalikan halaman detail; guard sesudah kembali menunjukkan nol password terlihat dan nol dialog aktif.

Karena guard menghentikan observasi, **tidak ada kesimpulan bahwa Settings tidak memiliki account ID**. Binding masih unresolved dan tidak dibuat. Kelanjutan memerlukan operator membuka halaman akun non-login/non-modal yang aman atau mengidentifikasi sumber ID non-secret secara manual; jangan membaca cookie/storage/network auth atau memakai nama artist/email sebagai fallback diam-diam.

`toolost_uploader/read_only.py`: parser snapshot murni dan `observe_page(page)` untuk halaman list/detail **yang sudah terbuka**. Tidak ada connect/login/navigation/click/mutator atau Playwright import pada runtime module. Dependency Playwright tetap hanya environment riset; package runtime stdlib.

Allowlist URL https exact toolost.com/www.toolost.com dengan path manage/<page> atau view/<id>/info, tanpa query/fragment/userinfo. Guard DOM menolak password/OTP/login controls/form, iframe auth/CAPTCHA dan dialog aktif sebelum ekstraksi metadata. Guard bukan detektor autentikasi sempurna: operator tetap wajib memastikan halaman bukan login, termasuk modal/iframe. URL awal/akhir dibandingkan; ini tidak menjamin snapshot atomik saat DOM berubah serentak.

Selector list `.release-grid-card__title`, detail `.rs-hero__title`, `.release-track-item__title` dan edit href didukung observasi sesi ini, bukan API stabil layanan. Parser menolak title kosong, target edit mismatch, duplicate release ID, incomplete/login/dialog; empty cards bukan empty catalog/not_found. Hasil selalu partial dengan account_identity=null/account_verified=false, coverage false. Track ID null/identity false; status unknown, metadata/artwork/options/pagination/filter belum diklaim.

Belum ada CLI release list/detail, account binding, mutasi akun atau publish. Jangan memakai snapshot partial untuk mengotorisasi executor. Langkah berikutnya: keputusan sumber identitas akun terverifikasi (bisa review manual jika UI tidak cukup), baru read-only CLI berkontrak dan bounded paging; live draft smoke masih perlu izin target/aset terpisah.

Verifikasi sesi ini pada macOS/Python 3.14.7: smoke list/detail live berhasil pada target yang sudah dibuka; proyeksi tetap partial dan privat. Build wheel melalui sdist berhasil; suite lengkap dengan schema independen dan instalasi wheel bersih **117/117 lulus tanpa skip**. `git diff --check` bersih.
