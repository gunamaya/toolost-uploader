# Toolost uploader

- Gunakan bahasa Indonesia. Baca docs/RESEARCH.md sebelum merencanakan implementasi agar keputusan tidak drift.
- Target: CLI terpisah untuk integrasi yt-to-flowmusic. Pengguna sudah memilih Python + Playwright, dengan kemungkinan distribusi PyPI. Jangan scaffold uploader sebelum pemetaan UI; jangan publish paket tanpa permintaan eksplisit.
- Login manual. Jangan membaca password/cookie, melewati CAPTCHA/2FA, atau memakai profil Chrome harian.
- Riset kini diizinkan membuat draft, upload audio/artwork uji yang ditentukan pengguna, dan Save Changes. Batas akhir riset adalah simpan draft: JANGAN klik Publish atau memicu distribusi, termasuk untuk menguji validasi. Mutasi profil/artist, generasi berbayar dan operasi lain tetap perlu izin terpisah.
- Tool final ditargetkan mendukung sampai publish/release, tetapi implementasi/eksekusi publish harus memakai persetujuan eksplisit terpisah; izin riset bukan izin publish.
- .local/ berisi session dan capture privat; jangan commit atau bagikan. Jangan capture halaman login. Tes default offline.
- Jangan commit/push tanpa permintaan eksplisit.
- Fokus operasi release/draft; jangan memperluas riset ke pengelolaan library Too Lost. Kontrak v1 di docs/CONTRACT-V1.md masih proposal untuk review, bukan implementasi tersedia.

## Lifecycle pekerjaan agen

- Antrean canonical: `docs/ANTRIAN-PEKERJAAN-UTAMA.md`. Baca tabel current, klaim aktif, maksimal lima checkpoint terbaru dan section task terkait di `docs/backlog/TASK-DETAILS.md` sebelum merencanakan. Buka history hanya untuk evidence yang relevan.
- Daftarkan task sebelum implementasi: ID stabil, scope masuk/keluar, dependency, priority/status, acceptance, verifier dan izin. Cari overlap berdasarkan hasil; plan/riset lama referensi, bukan antrean lain. Jangan aktifkan deferred/superseded tanpa keputusan user.
- Sebelum edit, baca ulang current index; claim `in_progress` dengan owner/session, waktu, HEAD+dirty paths, exact files, intended tests dan stop condition. Satu implementation slice utama; reviewer read-only boleh paralel. Penulis indeks/checkpoint satu koordinator. Jangan mengambil alih perubahan/klaim tak dikenal; `needs_reconciliation` dan minta handoff bila perlu. Markdown bukan atomic lock.
- Checkpoint saat scope berubah, blocker/tes gagal atau handoff. Selesai/blocked wajib update status/klaim dan append `docs/backlog/CHECKPOINT-HISTORY.md`: hasil/files, exact command/revision/evidence/batas, remaining dan satu rekomendasi berikutnya beserta alasan/alternatif bila blocked. Indeks hanya maksimal lima ringkasan terbaru; detail/history tidak disalin panjang ke indeks.
- `done` perlu seluruh acceptance pada perubahan terakhir. Tes offline bukan bukti live/package/release; child selesai tidak menutup parent. Lepas hanya klaim sendiri. Selesai/rencana bukan izin menjalankan task berikutnya, live, instalasi atau commit/push. Jangan mengulang smoke sukses atau menambah hardening/refactor tanpa kebutuhan task konkret.
- Tes default: `python3 -m unittest discover -s tests -q` dengan timeout tool; jalankan `git diff --check` setelah perubahan. Gunakan temporary paths/data sintetis; laporkan skips dan verifier yang belum dijalankan. Jawaban akhir menyebut ID/status, checkpoint, batas verifikasi dan next priority.
