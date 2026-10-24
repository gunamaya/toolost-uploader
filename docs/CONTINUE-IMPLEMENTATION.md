# Prioritas kelanjutan implementasi

Pengguna menegaskan agar membuat script nyata, bukan mengulang riset UI/fake framework. `scripts/upload_draft.py` + `live_draft.py` sekarang tersedia, lihat LIVE-DRAFT.md. Belum diuji end-to-end live. Jangan kembali ke eksperimen manual terpisah tanpa kebutuhan debugging spesifik script.

Current live stop: modal Name your release setelah memilih Single; Create belum diklik, upload/Save belum dilakukan. Target yang disetujui: draft baru RESEARCH ONLY - Draft Upload Smoke, satu WAV Terangnya Belum Pulang + PNG sintetis terpilih dalam source-selection privat, AI=true, tanpa lyrics/rights/services/publish. Jangan membatalkan atau membuat draft lain otomatis. Script sekarang membutuhkan start portal tanpa modal; penanganan modal existing perlu rekonsiliasi eksplisit sebelum eksekusi.

Lanjutkan menguji/memperbaiki script bounded dan verifikasi hasil sebenarnya, bukan menambah fake lapis baru. Semua live mutation berhenti pada Save, tanpa Publish. Account ID diambil dari respons asli aplikasi /api/auth/me, tidak direct fetch yang sebelumnya 403. Jangan hardcode user/artist/draft ID atau private paths ke produk/fixtures.
