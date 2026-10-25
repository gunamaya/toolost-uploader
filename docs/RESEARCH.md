# Too Lost uploader — catatan riset

Riset dimulai: 2026-10-24. Diperbarui: 2026-10-25. Status: observasi uploader dan draft parsial sudah diuji; validator dan CLI offline terpasang tersedia, uploader/operasi akun belum diimplementasikan.

## Peta dokumen

- [LIVE-DRAFT.md](LIVE-DRAFT.md): smoke draft-only subset sukses sampai Save/reopen; hardening journal/identity dan rekonsiliasi readback-only sesudahnya diuji offline, bukan resume produksi.

- [READ-ONLY.md](READ-ONLY.md): observasi list/detail live terbatas dan parser snapshot; identitas akun/track masih unknown.

- [FAKE-WORKFLOW.md](FAKE-WORKFLOW.md): pilihan approval immutable pengguna dan workflow sintetis tiga langkah; bukan bukti akun.

- [FAKE-FLOW.md](FAKE-FLOW.md): satu alur fake Save dengan gate dan recovery receipt; bukan bukti layanan.

- [OFFLINE-APPROVAL.md](OFFLINE-APPROVAL.md): aturan binding/review dan approval sintetis yang disetujui; identity UI nyata tetap unresolved.

- [FAKE-UPLOAD.md](FAKE-UPLOAD.md): recovery upload sintetis tersimpan di disk dan tes restart; bukan bukti upload akun.

- [FAKE-UI.md](FAKE-UI.md): model state UI sintetis + tes Save/read-back; tidak menambah bukti live/selector.

- [OFFLINE-JOURNAL.md](OFFLINE-JOURNAL.md): intent sebelum fake save, unknown outcome dan read-only reconciliation sintetis; bukan bukti UI/akun baru.

- [LOCAL-STATE.md](LOCAL-STATE.md): implementasi internal profil privat, lock dan checkpoint atomik offline; tidak menambah bukti akun/remote.

- [OFFLINE-VALIDATION.md](OFFLINE-VALIDATION.md): keputusan review pengguna, schema/validator stdlib offline yang tersedia dan batas implementasi; tidak ada tindakan akun baru.

- [CONTRACT-V1.md](CONTRACT-V1.md): proposal konkret command, manifest, hasil JSON, exit code dan state; belum disetujui final atau diimplementasikan.
- [RELEASE-CONTRACT.md](RELEASE-CONTRACT.md): proposal release list/detail dan publish dua tahap. Publish belum diuji dan execution disabled selama riset; permintaan dokumentasi bukan izin distribusi.
- [CONTRACT-PLAN.md](CONTRACT-PLAN.md): parameter AI, profil, kontrak integrator dan prioritas uji. Rancangan belum merupakan schema/command yang tersedia.
- [BROWSER.md](BROWSER.md): login manual dan observasi CDP.
- [UI-MAP.md](UI-MAP.md), [RELEASE-MODES.md](RELEASE-MODES.md): navigasi dan empat mode.
- [MEDIA-DRAFT.md](MEDIA-DRAFT.md): aset uji, editor track dan save/read-back.
- [PROFILE-DEFAULTS.md](PROFILE-DEFAULTS.md): baseline akun vs pengisian manual.
- [AI-DOCUMENTATION.md](AI-DOCUMENTATION.md): issue AI dan state observasi terakhir.
- [DRAFT-LIFECYCLE.md](DRAFT-LIFECYCLE.md): penghapusan draft lama, pembuatan draft pengganti dan defaults yang diverifikasi setelah reopen.
- [MULTI-TRACK.md](MULTI-TRACK.md): upload dua audio berbeda, default per-track, reorder dan save/reopen.
- [RESUME.md](RESUME.md): restart browser terkontrol dan rekonsiliasi draft tersimpan tanpa upload ulang; batas pencocokan track dan failure recovery.
- [UNSAVED-STATE.md](UNSAVED-STATE.md): perubahan judul release tanpa Save dan judul track+Done hilang setelah reload; baseline kembali dan dua track tetap utuh.
- [SAVE-FAILURE.md](SAVE-FAILURE.md): request mutasi Save diblokir sebelum terkirim; UI error dan pemulihan lewat reload/read-back, tanpa retry/upload ulang.
- [TRACK-REMOVAL.md](TRACK-REMOVAL.md): hapus Sungai Teh Susu dengan izin, Save/reopen memverifikasi satu track tersisa. Baseline dua track sebelumnya historis.

## Tujuan yang dikonfirmasi pengguna

- Membuat CLI album release uploader untuk Too Lost.
- Akun pengguna hanya memiliki uploader biasa; akses API/CSV belum tersedia.
- CLI akan diintegrasikan dengan `~/Documents/projects/cover/yt-to-flowmusic`.
- Langkah pertama: pahami interface dan operasi Too Lost melalui browser Playwright; pengguna login sendiri.
- Izin riset terbaru: boleh upload audio/artwork uji dan menyimpan draft. Batas akhir mutlak selama riset adalah simpan draft; DILARANG menekan Publish atau mengirim distribusi, termasuk untuk mengetes validasi/error. File uji harus ditentukan pengguna sebelum dipilih.
- Scope produk final mencakup sampai publish/release, bukan draft-only. Dukungan publish nanti membutuhkan persetujuan eksplisit terpisah dari izin riset; mekanisme konfirmasi belum dirancang.
- Pengguna membatasi fokus pada release, bukan pengelolaan library Too Lost. Dampak library yang tidak diketahui cukup menjadi batas bukti, bukan agenda riset tambahan.

## Keputusan stack yang dikonfirmasi

- Pengguna memilih Python secara eksplisit, dengan pertimbangan integrasi yt-to-flowmusic dan kemungkinan distribusi melalui PyPI.
- Gunakan Python + Playwright untuk eksplorasi browser dan CLI uploader. Pemilihan stack bukan izin publish paket ke PyPI ataupun publish/distribusi musik.
- Packaging CLI nantinya menggunakan pyproject.toml dan console entry point; nama paket, dependency, dan versi minimum Python ditentukan setelah pemetaan UI. Jangan scaffold uploader dulu.
- Sebelumnya TypeScript direkomendasikan untuk project browser standalone; rekomendasi berubah setelah memeriksa proyek sumber.

## Rancangan sementara — belum final
- `yt-to-flowmusic` berbasis Python/Textual, punya modul produksi album dan referensi artefak audio ber-hash. `flow_service.py` mencontohkan integrasi subprocess dengan hasil JSON dan pembatalan.
- CLI uploader tetap terpisah. Jangan bergantung langsung pada internal/database proyek sumber.
- Usulan kontrak: manifest JSON berversi berisi metadata rilis, urutan track, artwork, path dan hash audio final yang dipilih.
- Usulan command (BELUM diimplementasikan): validate, upload, status; stdout JSON, stderr progres, exit code konsisten.
- Jangan membangun adapter/manifest final sebelum memetakan form dan operasi nyata.
- Hindari agent LLM untuk setiap klik rutin. AI membantu eksplorasi/development; alur berulang sebaiknya deterministik.
- Tidak perlu Rust, hybrid runtime, GUI, cloud browser, atau framework agent untuk langkah awal.

## Riset publik dan keterbatasan bukti

Akses HTTP langsung ke situs Too Lost dan Help Center mendapat 403. Informasi Too Lost berikut diperoleh dari indeks pencarian halaman resmi, BUKAN pengujian akun atau kontrak API.

- Halaman Developers mengiklankan REST API, katalog/rilis, distribusi dan webhook. Contoh POST /v2/releases bukan kontrak terverifikasi. Auth, upload media, rate limit dan ketersediaan akun belum diketahui.
- Enterprise Suite mengiklankan CSV bulk import dan DDEX; bukan jalur yang tersedia pada akun pengguna saat ini.
- Panduan publik menggambarkan pembuatan rilis/artist, basic information, artwork, release information, manage tracks, preview/publish dan QC.
- Panduan artwork menyebut persegi 3000–5000 px, RGB, JPG/TIFF/PNG, maksimum 36 MB.
- Panduan audio merekomendasikan WAV/FLAC 16/24-bit, 44.1 kHz, stereo. Format lain dan batas aktual perlu dicek pada UI terbaru; jangan mengunci validator berdasarkan cuplikan pencarian saja.
- Upload selesai pada browser tidak membuktikan ingest/proses server selesai.
- Tidak ada benchmark yang membuktikan bahasa tertentu paling dikuasai semua AI. Waktu upload terutama dipengaruhi jaringan dan server, bukan Python vs TypeScript.

## Bukti lokal proyek integrasi

Dibaca secara read-only: README.md, requirements.txt, flow_service.py, production/artifacts.py, production/album_designer.py dan sebagian nama model production/domain.py.

- Python 3.10+ menurut README; dependensi antara lain Textual, httpx, keyring, platformdirs, mutagen.
- README membedakan aplikasi TUI dari antarmuka argumen CLI yang belum didokumentasikan.
- Graphify tersedia tetapi hasilnya tampak lebih tua daripada kode produksi; jangan menjadikannya otoritas tunggal.
- Manifest distribusi Too Lost belum ditemukan pada area yang diperiksa. Ini bukan audit menyeluruh seluruh repo.

## Aturan eksplorasi dan keamanan

- Login/2FA/CAPTCHA oleh pengguna. Jangan membaca password, mengekspor cookie, atau melewati proteksi.
- Profil Chrome khusus project, bukan profil Chrome sehari-hari.
- Script gather hanya membuka browser dan menyediakan capture manual; tindakan riset terpisah telah membuat draft dan upload sesuai izin. Tidak ada Publish/distribusi.
- Navigasi yang membuat draft/menyimpan data perlu dikomunikasikan dan disetujui sebelum dilakukan. Publish/distribusi tidak termasuk izin eksplorasi.
- Capture lokal bisa mengandung data akun/katalog; jangan commit atau bagikan. Jangan merekam form login.
- Trace jaringan tidak diaktifkan secara default karena dapat menyimpan data sensitif.
- Periksa ketentuan/izin otomasi sebelum penggunaan operasional; browser yang berhasil dibuka bukan bukti otomasi diizinkan.

## Checklist pemetaan setelah login

1. Navigasi dashboard, daftar rilis, status dan tindakan yang tersedia.
2. Bedakan navigasi read-only dari pembuatan draft, autosave dan operasi mutasi.
3. Dengan izin, petakan tiap langkah uploader: label, required/optional, jenis input, conditional field, pilihan dan validasi.
4. Artist dan mapping profil DSP; metadata rilis/track; credit dan hak; kode ISRC/UPC; jadwal/zona waktu; stores/territories jika tersedia.
5. Audio/artwork: input file, urutan track, progress, completion, error, pemrosesan server.
6. Draft/reopen/edit, review, batas publish dan status QC/delivery. Jangan publish untuk riset.
7. Session expired, pembatalan, kegagalan parsial dan risiko duplikasi; recovery harus rekonsiliasi state remote, bukan retry buta.
8. Baru tetapkan manifest, command CLI dan tes offline berdasarkan bukti UI.

## Sumber

- https://toolost.com/developers
- https://toolost.com/suite/enterprise
- https://toolost.com/terms
- https://help.toolost.com/hc/en-us/articles/360060686252-How-to-Upload-a-Release
- https://help.toolost.com/hc/en-us/articles/360054816371-What-Audio-File-Format-Should-I-Upload
- https://help.toolost.com/hc/en-us/articles/360054808451-Cover-Artwork-Requirements
- https://playwright.dev/docs/languages
- https://playwright.dev/python/docs/library
- https://playwright.dev/docs/auth
- https://playwright.dev/docs/input#upload-files
- https://playwright.dev/agent-cli/introduction
- https://pptr.dev/
- https://docs.stagehand.dev/
- https://docs.browser-use.com/introduction

## Lanjutan sesi

Login manual Chrome biasa dan observasi CDP berhasil. Pengguna menyelesaikan setup artist sendiri. Satu draft riset dibuat; empat mode dibandingkan, lalu satu WAV dan artwork sintetis diupload, judul/lirik dimasukkan dan hasil save diverifikasi reload. Tidak ada Publish/distribusi. Matriks mode di RELEASE-MODES.md; riwayat navigasi di UI-MAP.md; uji media di MEDIA-DRAFT.md.

Peluncuran awal memakai Playwright langsung dan pengguna mengalami kesulitan login Gmail (pesan persis belum dikonfirmasi). Dipisahkan menjadi login Chrome biasa tanpa debugging, lalu observe via CDP mengikuti pola Studiowright. Petunjuk di docs/BROWSER.md. Tidak ada stealth atau bypass autentikasi.

Setelah pengisian manual pengguna, satu issue format tersisa dan AI-assisted sempat false (PROFILE-DEFAULTS.md). Browser kemudian dibuka ulang; AI-assisted diaktifkan kembali untuk reproduksi issue. Klik AI Documentation tidak mengubah snapshot UI; perubahan AI sesi terakhir belum disimpan eksplisit oleh agen atau diverifikasi reload (AI-DOCUMENTATION.md). Jangan menganggap state browser saat ini diketahui tanpa pemeriksaan ulang.

Pengguna menyetujui AI-assisted sebagai parameter per track; tidak diberikan bukan otomatis false. Integrator diusulkan memilih profil browser lokal, terpisah dari artist akun. Default akun dipertahankan bila tidak dioverride dan hasil efektif dibaca ulang. Keputusan, proposal yang belum final dan daftar uji berikutnya dirinci dalam CONTRACT-PLAN.md.

Update lifecycle: atas permintaan eksplisit pengguna draft riset lama dihapus lewat ikon trash → Remove; reload daftar menunjukkan No releases yet. Satu draft Album pengganti dibuat untuk uji defaults dan dibuka ulang: artist, genre/language, label/C/P terisi tanpa input manual; belum ada media. Save Changes kali ini kembali ke daftar tanpa dialog Save. State akhir dan bukti ada di DRAFT-LIFECYCLE.md; catatan state akhir draft lama pada dokumen sebelumnya kini historis. Writer defaults per track, multi-track/resume, schema final dan CLI belum diuji/diimplementasikan.

Update sesudah lifecycle: pengguna mengizinkan uji dua track berbeda. Dua MP3 ready diupload ke draft pengganti; urutan ingest terbalik dibanding urutan pilihan file. Drag berhasil memulihkan urutan, Save Changes→Save dan reopen membuktikan tepat dua track dengan urutan yang dimaksud. Artist/writer default terisi, title dari filename, lyrics kosong, AI-assisted defaultfalse; belum metadata siap distribusi. Lihat MULTI-TRACK.md. State akhir terbaru: draft pengganti dengan dua MP3 tanpa artwork; hanya resume/failure recovery, schema final dan CLI yang masih belum diuji/diimplementasikan pada cakupan ini.

Update resume: atas izin pengguna browser khusus ditutup terkontrol, port/profile bebas diverifikasi, lalu browser baru dibuka dengan profil sama. Daftar menunjukkan satu draft yang sama; Edit target memuat tepat dua track dengan urutan tersimpan. Tidak Create Release/Upload/Save/Publish ulang. Lihat RESUME.md. Ini hanya resume draft tersimpan setelah restart; partial upload, crash saat Save, session expired, account mismatch dan duplicate filenames belum diuji. CLI/schema produk belum diimplementasikan.

Update unsaved state: judul release sementara tanpa Save serta judul track sementara+Done diuji satu per satu dengan blur, tunggu2.5detik dan reload. Keduanya kembali baseline asli; tidak ada probe tersisa, dua track/urutan tetap utuh. Lihat UNSAVED-STATE.md. Jangan checkpoint metadata sebagai persisted setelah Done saja; perlu Save+read-back. Hasil ini tidak membuktikan semua field bebas autosave atau upload/Save failure recovery selesai.

Update Save failure: page.route menolak sementara request non-read sebelum terkirim, kemudian Save Changes→Save memunculkan error saving dengan Cancel/Try again. Tidak Try again; guard dilepas dan reload/read-back memastikan judul baseline dan dua track/urutan tetap utuh. Lihat SAVE-FAILURE.md. Tidak menyamakan ini dengan server-saved-response-lost, partial upload, atau expired session; kasus tersebut masih belum diuji.

State TERKINI setelah permintaan hapus track: Sungai Teh Susu dihapus dari draft pengganti lewat konfirmasi Remove track, lalu Save Changes→Save. Reopen memverifikasi tepat satu track Terangnya Belum Pulang tersisa; draft tetap ada dan kedua audio sumber lokal masih ada. Tidak upload/publish. Lihat TRACK-REMOVAL.md; jangan mereplay checkpoint dua track lama atau otomatis mengupload track yang sengaja dihapus. Library remote deletion belum diverifikasi.

Update dokumen ini dan docs/UI-MAP.md setelah mendapat bukti baru; jangan mengubah asumsi menjadi fakta.
