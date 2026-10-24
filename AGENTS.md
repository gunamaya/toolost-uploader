# Toolost uploader

- Gunakan bahasa Indonesia. Baca docs/RESEARCH.md sebelum merencanakan implementasi agar keputusan tidak drift.
- Target: CLI terpisah untuk integrasi yt-to-flowmusic. Pengguna sudah memilih Python + Playwright, dengan kemungkinan distribusi PyPI. Jangan scaffold uploader sebelum pemetaan UI; jangan publish paket tanpa permintaan eksplisit.
- Login manual. Jangan membaca password/cookie, melewati CAPTCHA/2FA, atau memakai profil Chrome harian.
- Riset kini diizinkan membuat draft, upload audio/artwork uji yang ditentukan pengguna, dan Save Changes. Batas akhir riset adalah simpan draft: JANGAN klik Publish atau memicu distribusi, termasuk untuk menguji validasi. Mutasi profil/artist, generasi berbayar dan operasi lain tetap perlu izin terpisah.
- Tool final ditargetkan mendukung sampai publish/release, tetapi implementasi/eksekusi publish harus memakai persetujuan eksplisit terpisah; izin riset bukan izin publish.
- .local/ berisi session dan capture privat; jangan commit atau bagikan. Jangan capture halaman login. Tes default offline.
- Jangan commit/push tanpa permintaan eksplisit.
- Fokus operasi release/draft; jangan memperluas riset ke pengelolaan library Too Lost. Kontrak v1 di docs/CONTRACT-V1.md masih proposal untuk review, bukan implementasi tersedia.
