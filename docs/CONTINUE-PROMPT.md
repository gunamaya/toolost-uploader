# Prompt untuk melanjutkan pengembangan toolost-uploader

Salin bagian berikut sebagai prompt sesi pengembangan selanjutnya. Status handoff: 25 Oktober 2026. Dokumen riset menyimpan sejarah; verifikasi state aktual sebelum tindakan akun.

Update packaging berikutnya: pengguna mengizinkan package minimal. Kini tersedia `pyproject.toml`, modul `toolost_uploader`, entry point `toolost validate`, `python -m toolost_uploader`, dan wrapper script lama dengan validator tunggal. Runtime stdlib, Python minimum deklaratif 3.10, versi lokal 0.1.0a0, classifier Private :: Do Not Upload. Extra dev build/jsonschema dan tes wheel bersih tersedia; lihat README/OFFLINE-VALIDATION untuk cara menjalankan. Operasi akun tetap belum tersedia. Pernyataan packaging belum dibuat di riwayat bawah sudah historis. Tidak ada izin commit/push baru otomatis.

Update setelah review offline pada tanggal yang sama: pengguna menyetujui tahap schema/validator offline, nama distribusi `toolost-uploader`, modul `toolost_uploader`, executable `toolost`, field minimal dan AI boolean wajib pada manifest normal. Kini tersedia `scripts/validate.py`, schema manifest/result validate di `docs/schemas/`, serta `tests/test_validate.py`. Baca `docs/OFFLINE-VALIDATION.md` untuk cakupan/batas lokal. Packaging, command terpasang, profile manager dan operasi akun/publish belum dibuat/diizinkan oleh persetujuan offline. Bagian implementasi dan angka empat tes di bawah adalah baseline handoff sebelum update ini, bukan state kode terbaru. Lanjutkan packaging hanya setelah scope tahap tersebut disepakati; jangan mengulang review minimal yang sudah disetujui.

---

Update setelah commit gate 9054f97 (belum push; fake upload 2eca961 juga lokal): task lanjutan fake_flow.py + test_fake_flow.py menyatukan exact FakeUI Save dengan verify→prepare→consume→journal.execute. Reconcile memverifikasi receipt consumed dan desired intent, bukan staging reload. Scope Save-only; upload/edit staging belum bergate. Baca FAKE-FLOW.md untuk crash antar-file fail-closed dan batas recovery. CLI tetap validate, tidak ada browser/akun. Kode coordinator baru belum otomatis di-commit/push.

Update gate offline setelah commit fake upload 2eca961 (belum push pada sesi ini): pengguna menyetujui binding pertama direview, mismatch/unavailable fail-closed, approval terikat target/hash/rencana. approval.py + test_approval.py tersedia hanya untuk identity sintetis, token satu-pakai disimpan atomik; belum terhubung fake executor/CLI, tidak membuktikan fingerprint UI nyata. Baca OFFLINE-APPROVAL.md. Berikutnya satu bounded alur fake dengan gate sebelum mutasi, bukan browser/live. Tidak ada izin commit/push otomatis untuk kode gate baru.

Update setelah commit/push fake UI 476512b: dilanjutkan fixture recovery upload persisten offline di fake_upload.py dan test_fake_upload.py. Intent batch terikat checkpoint ditulis unknown sebelum fake ingest JSON, encoding diprogresikan eksplisit dengan settle, restart lintas proses reconcile tanpa upload ulang; partial/failed/duplicate identity tetap unknown. Baca FAKE-UPLOAD.md. Belum terintegrasi dengan FakeUI/Save sebagai executor multi-operation. Tidak ada browser/akun diakses atau izin commit/push otomatis untuk perubahan baru.

Update fake UI offline: pengguna menyetujui model UI sintetis. `fake_ui.py` dan test_fake_ui.py memodelkan upload dialog/chooser, tick encoding, reverse ingest/reorder, delayed fields, mismatch ARIA/native, staging/Done, Save dialog/navigation/error/lost-response/metadata-loss. Jurnal menerima exact FakeUI dengan metadata digest; hanya Save dijurnal, upload belum recovery-safe lintas proses. Baca FAKE-UI.md. Tidak ada HTML/Playwright adapter atau bukti akun baru. CLI tetap validate; tidak ada izin commit/push otomatis.

Update attempt journal: pengguna mengizinkan jurnal + rekonsiliasi dengan fake adapter offline. `journal.py` dan `tests/test_journal.py` kini menyimulasikan satu fake.save, prepared→unknown sebelum mutasi, complete read-back ke applied/not_applied/conflict, timeout/partial/ambiguity tetap unknown, tanpa retry otomatis. Jurnal terpisah terikat exact checkpoint hash/run. Baca OFFLINE-JOURNAL.md; belum ada executor browser, attempt history atau binding remote. Baseline lama yang menyebut jurnal belum tersedia adalah histori untuk produksi. Tidak ada izin commit/push baru otomatis.

Update storage setelah packaging: pengguna meminta konfigurasi profil aman + checkpoint atomik dengan tes offline. Helper internal `toolost_uploader/storage.py` tersedia: default root macOS/Linux per user, alias tervalidasi, 0700/0600/owner/symlink guards, flock satu penulis, snapshot create/read dan cancel lokal dengan run/revision/hash guard. Baca LOCAL-STATE.md; account_fingerprint dan remote_draft_id tetap null, CLI masih hanya validate. Belum ada attempt journal, binding UI, browser profile manager atau remote resume. Riwayat di bawah yang menyebut checkpoint belum dibuat hanya baseline lama. Tidak ada izin commit/push otomatis.

Lanjutkan pengembangan project **toolost-uploader**, CLI Python + Playwright yang terpisah dan dapat dipanggil integrator `yt-to-flowmusic`. Gunakan bahasa Indonesia. Repo GitHub private: https://github.com/gunamaya/toolost-uploader.

## Baca sebelum bertindak

1. `AGENTS.md` dan `docs/RESEARCH.md`.
2. `docs/CONTRACT-V1.md`, `docs/RELEASE-CONTRACT.md`, dan contoh JSON terkait.
3. `docs/CONTRACT-PLAN.md` untuk keputusan vs proposal, lalu hanya laporan riset yang relevan dengan pekerjaan berikutnya.
4. `README.md` untuk status implementasi dan `docs/BROWSER.md` jika memang perlu browser.

Jangan menganggap command contoh atau kontrak sudah diimplementasikan. Kontrak/schema_version1 belum dirilis, masih proposal untuk review. Jika menemukan kontradiksi atau bagian belum jelas, jelaskan dan minta keputusan yang diperlukan; jangan diam-diam mengubah kontrak atau mengarang perilaku Too Lost.

## Tujuan dan keputusan

- Stack dipilih eksplisit: Python + Playwright; kemungkinan distribusi PyPI nanti. Tidak perlu Rust/hybrid, GUI, cloud browser atau LLM per klik.
- Integrasi melalui CLI/subprocess dan JSON manifest, bukan impor internal/database `yt-to-flowmusic`. Proyek integrator berbasis Python; jika perlu, periksa langsung instruction files proyek itu sebelum mengubahnya. Jangan mengubah repo integrator tanpa permintaan.
- CLI mengelola **release/draft**, bukan library Too Lost.
- Parameter release_type: album/ep/single/compilation; metadata track terpisah dari metadata rilis.
- Profil browser/login dapat dipilih lewat alias lokal; tidak sama dengan profil artist. Satu penulis per profil, identitas akun/draft harus diverifikasi.
- AI-assisted menjadi parameter eksplisit per track, bukan default false untuk menghilangkan issue. Tidak ditentukan berarti unknown; asal generate yang bertentangan perlu warning/review. Penyelesaian AI Documentation masih unresolved/manual support.
- Field omitted tidak boleh mengosongkan baseline akun. Read-back nilai efektif, bedakan inherited/explicit/ui_adjusted. Hak/credit/consent layanan tidak boleh ditebak.
- Input/hasil JSON stabil; progress stderr; exit code dan perbedaan draft_saved vs submission_confirmed vs live mengacu kontrak proposal.

## Batas izin yang wajib dipertahankan

- Riset live hanya sampai upload dan **simpan draft**. DILARANG klik Publish, Publish release atau memicu distribusi, termasuk untuk mengintip confirmation/tes validasi.
- Scope produk final boleh sampai release. Permintaan kontrak publish bukan izin implementasi/eksekusi publish. Kontrak publish dua tahap future; capability belum terverifikasi dan execution disabled selama riset.
- Login/CAPTCHA/2FA manual. Tidak membaca/mengekspor cookie/password, memakai Chrome harian, menyamarkan automation atau bypass proteksi.
- `.local/` berisi profil, aset/capture/checkpoint privat; `.venv/` environment lokal. Keduanya tidak boleh commit/push/share. Jangan capture login atau menyimpan network credentials. Jangan menyalin lirik/identitas legal pengguna ke docs/fixtures publik.
- Mutasi profil/artist, generasi berbayar, logout/session expiry, destructive failure injection dan publish perlu izin terpisah. Jangan retry upload/create/delete membabi buta.
- Tidak publish paket PyPI atau commit/push berikutnya tanpa permintaan eksplisit baru. Izin commit pada sesi handoff tidak otomatis berlaku selanjutnya.
- ToS/izin operasional automasi belum terverifikasi; berhasil menjalankan browser bukan bukti izin layanan.

## Implementasi yang benar-benar tersedia

Hanya harness riset `scripts/gather.py` dan `tests/test_gather.py`; belum ada uploader produk, package CLI, schema formal atau validator. Harness memakai satu profil riset macOS dan Chrome terpasang, dua tahap login biasa tanpa debugging lalu observe via loopback CDP. Jangan menganggap harness ini multi-profile manager produksi.

Tes offline stdlib:

```sh
python3 -m unittest discover -s tests -v
```

Terakhir 4 tes lulus. Tes ini memeriksa helper harness, bukan keseluruhan kontrak atau kemampuan upload produk. Tidak perlu membuka browser untuk menjalankannya. Playwright ada di `.venv/` lokal sesi riset, tetapi jangan mengandalkan environment tersedia pada clone baru atau melakukan instalasi tanpa menjelaskan kebutuhan.

## Bukti UI yang harus memengaruhi desain

- Uploader: Basic Information, Artwork, Release Information, Manage Tracks. Compilation otomatis Various Artists; title label/pricing berbeda per mode.
- Label jumlah Album6+/EP4–6 beririsan; jangan hardcode validasi DSP dari label. Detail artwork juga bertentangan antar sidebar/dialog; laporkan batas bukti.
- Profil lengkap mengisi artist/genre/language/label/C/P pada draft baru. Writer satu nama/dua role juga terisi pada dua track uji, tetapi legal authority tidak diverifikasi. Sebagian additional delivery default aktif; bukan alasan CLI mengaktifkan consent otomatis.
- Upload audio: dialog perantara → browse → pilih file → Upload N files. Progress100% tidak berarti encoding selesai.
- Dua MP3 berbeda berhasil diupload. Urutan ingest TERBALIK dari input file chooser; drag mengoreksi dan Save/reopen membuktikan urutan bertahan.
- Track title dari basename, lyrics kosong, AI defaultfalse; jangan anggap default final benar. ID track remote tidak terlihat pada atribut/link baris yang diperiksa; duplicate basename matching unresolved.
- Field dinamis dan transisi panel bisa memberi pembacaan keliru; tunggu visible/stable dan scope main/dialog/menu aktif.
- Native checked/is_checked bisa false sementara aria-checked true. Gunakan semantik UI+panel read-back, bukan force click atau modifikasi DOM.
- Save Changes kadang konfirmasi Save, kadang kembali ke daftar. Done track/local fill bukan bukti server sudah menyimpan.
- Restart browser terkontrol berhasil memuat draft/two-track state tanpa reupload. Unsaved title release serta track+Done hilang setelah reload pada uji2.5detik.
- Save request diblokir sebelum network menghasilkan error/Cancel/Try again; guard dibersihkan, reload kembali baseline. Ini BUKAN server-saved-response-lost/partial-upload recovery.
- Delete draft: trash scoped ke kartu ID/status/judul → Remove irreversible → reload memastikan absent. Remove track: dialog menyebut track → Remove → Save/reopen; tidak menyelidiki library.
- AI Documentation issue tidak merespons klik; tidak ada pageerror teramati. Hidden review-notes markup bukan solusi yang sudah terbukti; jangan paksa menampilkan DOM atau klik Publish untuk mencarinya.

## State riset terakhir (bukan asumsi untuk eksekusi)

Draft riset lama sudah dihapus. Draft pengganti berjudul `RESEARCH ONLY - Profile Defaults - 2026-10-25`, ID tersimpan pada bukti privat. Sesudah izin hapus Sungai Teh Susu, baseline terkini **satu track Terangnya Belum Pulang** berjudul basename MP3, tanpa artwork; state ini sudah Save/reopen. Checkpoint lama dua track adalah sejarah, jangan digunakan untuk otomatis mengupload track yang sengaja dihapus.

Remote state dapat berubah oleh pengguna; browser/port/background job juga belum tentu masih hidup. Cek ulang sebelum mutasi dan stop jika target tidak cocok. Tidak hardcode ID akun/draft riset ke produk/tes publik. Sumber audio yang pernah diizinkan berada di proyek FlowStudio lokal; jangan upload ulang atau mengeksplorasi folder pengguna di luar kebutuhan/izin.

## Langkah pengembangan berikutnya

1. Review gap kontrak dengan pengguna: command/nama package, field minimal, ID akun/track, default/override, artist/writer/rights serta approval draft/publish. Jangan mengklaim semua ini final.
2. Setelah review/izin implementasi, mulai **offline dahulu**: formal JSON schema/validator manifest/result dan fixture sintetis anonim. Dokumentasikan bagian unsupported, bukan menerima field lalu mengabaikannya.
3. Tambahkan package Python minimal `pyproject.toml` dan console entry point hanya setelah scope implementasi disepakati. Tidak publish PyPI. Utamakan stdlib dan dependency seperlunya, riset API dependency dari docs resmi.
4. Implementasikan parser/validate, JSON stdout/progress stderr/exit code, profile configuration aman dan atomic checkpoint secara incremental. Uji hash mismatch, unknown/duplicate keys, relative path, duplicate track IDs, missing ai_assisted dan redaction.
5. Fake UI/adapter offline untuk modal, delayed fields, aria/native mismatch, reverse ingest, Save dialog/navigasi/error. Journal attempt sebelum mutasi; unknown outcome harus reconcile, tidak retry buta.
6. Read-only release list/detail dapat dibangun bertahap dengan coverage/unknown yang jujur; paging/filter/non-Draft statuses belum terverifikasi live. Jangan empty/not_found untuk auth/timeout.
7. Live draft-only smoke hanya dengan persetujuan, target dan aset jelas. Operasi publish belum boleh tersedia pada executor riset. Partial upload/session expiry/server-saved-response-lost masih perlu fixture offline dan izin bounded live terpisah bila perlu.

Untuk tiap langkah: jelaskan intent sebelum tools, rencanakan proporsional, buat perubahan kecil yang bisa dites, laporkan tes yang benar-benar dijalankan, dan update catatan setelah bukti baru. Jangan menjalankan ulang eksperimen sukses atau memperluas scope hanya untuk menambah riset. Fokus menyelesaikan kontrak lalu implementasi yang diuji, bukan mendesain framework besar.
