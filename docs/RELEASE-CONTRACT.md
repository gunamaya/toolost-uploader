# Kontrak release list, detail dan publish

Status: PROPOSAL untuk review, bagian dari kontrak schema_version1 yang belum dirilis. Tidak ada command di dokumen ini yang sudah diimplementasikan. Read-only list/detail sebagian didukung bukti riset; alur Publish/confirmation/submission BELUM diuji. Permintaan menambah kontrak bukan izin menjalankan Publish. Scope hanya release, bukan library/tracks global Too Lost.

## Antarmuka usulan

```sh
toolost release list --profile <alias> --page 1 --page-size 20 --json
toolost release detail <remote-release-id> --profile <alias> --json
toolost release publish <remote-release-id> --profile <alias> --prepare --json
toolost release publish <remote-release-id> --profile <alias> --approval <approval-id> --json
```

Prepare dan approval mutually exclusive. Bare publish tidak melakukan mutasi: confirmation_required. `--approve-draft`, `--yes`, izin riset atau konfirmasi lama tidak dapat menggantikan approval publish. Nama remote-release-id bukan release_id lokal integrator/run_id. Alias harus cocok account binding yang telah diverifikasi.

Semua operasi memakai output envelope CONTRACT-V1.md. Untuk release remote tanpa run lokal: run_id, release_id dan draft_id nullable; `remote_release_id` adalah string ID target. draft_id diisi hanya jika diketahui target Draft. command: release.list | release.detail | release.publish.prepare | release.publish. Referensi ID jangan disintesis dari judul.

## Release list — read-only

Parameter:
- profile wajib.
- page integer>=1, default1; page-size integer1–100, default20. Ini pagination logis CLI, bukan janji UI memiliki ukuran yang sama.
- Optional query: pencarian judul literal, bukan regex atau JS; status filter hanya jika mapping terverifikasi. Bentuk CLI `--query <text>` dan `--status <normalized-status>`.
- Tidak ada `--all` v1 agar crawling tidak tak terbatas. Implementasi boleh berjalan lebih dari satu halaman UI untuk memenuhi halaman logis, tetapi wajib bounded dan mencatat cakupan.

Data:
- items: array {remote_release_id, url, title, release_type, artists, remote_status, issue_count, observed_at}.
- artists array nama tampilan, bukan legal owner IDs yang ditebak.
- remote_status: {normalized, raw}; normalized draft | submitted | in_review | scheduled | live | rejected | unknown. Hanya draft telah diverifikasi riset. Label lain membutuhkan mapping bukti sebelum dipakai; jangan memetakan label asing ke live.
- Field yang tidak tersedia null, bukan string kosong/0 rekaan. issue_count hanya ringkasan UI dan bisa berbeda dari editor.
- pagination: {page,page_size,returned,next_page,total,complete,consistency}. total/next_page nullable bila tidak diketahui. complete artinya cakupan halaman dan filter yang diminta lengkap, bukan seluruh katalog; consistency='best_effort' karena UI bisa berubah selama navigasi.
- partial result: status partial, exit4; sertakan items teramati dan warnings, pagination.complete=false. Jangan mengklaim empty ketika gagal login, timeout, parsing atau filter belum terverifikasi.
- no releases confirmed: status ok, items[], total0 hanya bila UI benar-benar membuktikannya. Halaman lewat akhir boleh kosong dengan cakupan jelas, bukan not_found release individual.
- Jangan mengembalikan title-only duplicates tanpa identity: item ID unknown dicatat null dan coverage partial. Deduplikasi hanya berdasarkan ID teramati, bukan judul/artist.

List tidak klik trash, Create Release, Save atau Publish. Query/filter read-only yang tidak tersedia menghasilkan unsupported_capability, bukan filter salah diam-diam. Paginasi/filter multi-page belum diuji live.

## Release detail — read-only

Masukan ID remote wajib. Buka jalur detail yang telah terverifikasi; jangan masuk /uploader tanpa ID karena dapat membuat draft baru. Jika membutuhkan editor untuk membaca metadata, adaptor harus membuktikan navigasi/read saja tidak menyimpan data; jangan Done/Save untuk memperoleh snapshot. Deteksi staged changes milik pengguna; bila tidak bisa membaca tanpa mengganggu, conflict.

Data snapshot:
- remote_release_id, url, observed_at, remote_status, title, release_type, artists.
- Metadata teramati: jadwal, genre/language, label/C/P, UPC jika ada; artwork descriptor (dimensi/format bila terlihat, bukan hash lokal yang dianggap remote).
- tracks ordered array: {position,remote_track_id,title,artists,language,ai_assisted,isrc,iswc,lyrics_present,writer_summary}. Unknown values null; jangan mengekspos raw lyrics secara default. remote_track_id nullable jika tidak terlihat seperti riset saat ini. Identity confidence per-track harus eksplisit.
- effective_options: stores/territories/additional deliveries beserta selected,enabled dan observation support jika tersedia. Jangan menganggap total store counter membuktikan seluruh daftar.
- issues, review_required dan coverage {complete,missing_fields,limitations}. Field yang diminta tetapi belum terbaca harus missing, bukan diisi default. Tidak perlu membangun semua field sekaligus untuk read-only awal, tetapi publish memerlukan cakupan jauh lebih kuat.
- snapshot_digest: hash dari representasi kanonis field yang benar-benar teramati; snapshot_fields dan completeness menyertai. Hash snapshot parsial bukan jaminan seluruh konten/media remote sama. Aturan canonicalization formal harus ditetapkan sebelum implementation: sorted object keys, UTF-8, urutan array bermakna, tidak include observed_at/transient IDs. Algoritma/version harus dicatat.

Status ok/exit0 hanya jika cakupan detail yang dijanjikan implementasi terpenuhi. partial/exit4 saat sebagian field tak tersedia; not_found/exit7 hanya jika akun benar dan UI eksplisit membuktikan rilis tak ada. Timeout/unauthorized tidak boleh dijadikan not_found. Semua remote_status non-draft di dokumen ini adalah desain, bukan live verification.

## Publish prepare — read-only dan non-distributing

Menghasilkan rencana review lokal, TIDAK menekan tombol Publish untuk mencari konfirmasi. Prepare boleh tersedia saat riset bila hanya membaca, tetapi tidak menjanjikan approval executable sebelum capability publish diverifikasi.

Preflight:
1. Account/profile/ID dan status Draft harus cocok. Status lain/unknown berhenti; request berulang tidak boleh mendistribusikan ulang.
2. Baca snapshot tersimpan setelah Save, bukan state staged. Pastikan metadata/media/track identity dan coverage cukup; jika media remote identity tidak dapat dibuktikan, jangan beri executable approval.
3. Tampilkan seluruh metadata, order, AI/original-cover/explicit/clean, writer/rights review, jadwal/timezone, stores/territories/additional deliveries dan issue server. Default profil juga bagian yang direview.
4. Tidak ada known blocking issue, reconciliation unknown, upload processing atau konflik. Issue UI0 saja tidak membuktikan hak/kelayakan QC.
5. Deklarasi hak dan evidence disediakan/diapprove pemilik hak, bukan dibuat CLI. AI Documentation unresolved harus blocking untuk publish jika UI mewajibkan; tidak dimatikan otomatis.
6. Eligibility atau syarat yang belum diamati berarti blocked/unsupported, bukan permit inferred.

Hasil data: {plan_id,remote_release_id,snapshot_digest,blockers,capability_verified,approval_id,approval_expires_at}. Dalam state riset saat ini capability_verified=false, blocker publish_flow_unverified, approval_id=null, status blocked (exit4). Tidak ada token approval palsu atau tombol final yang ditebak.

Setelah fase implementasi publish mendapat izin dan bukti: approval_id hanya dibuat setelah manusia/integrator berwenang mereview snapshot lengkap dan memberikan izin publish khusus. Prepare biasa bukan otorisasi. Mekanisme penerimaan approval (interaktif/out-of-band) perlu disetujui sebelum implementasi; flag boolean bukan bukti persetujuan.

## Publish execution — capability future, disabled selama riset

Approval lokal berumur pendek (usulan10menit), single-use, terikat profile+account binding, remote ID, canonical content snapshot, rencana delivery/jadwal dan scope publish. Expired/mismatch -> conflict, jangan refresh otomatis. Approval file private; ID bukan password/API key dan tidak berisi cookie. Jangan letakkan di manifest bersama metadata sebagai default persistable consent.

Sebelum aksi: exclusive profile/draft lock, baca ulang target dan snapshot; perubahan manual/opsi otomatis/metadata/track/jadwal membatalkan approval. Recheck state sedekat mungkin dengan final action; UI eksternal tetap memiliki race window, jadi tidak mengklaim transaksi atomik/remote idempotency.

Persist attempt dan tandai approval consumed sebelum pertama aksi yang mungkin memicu distribusi. Tidak dapat mengasumsikan tombol pertama hanya preview; urutan dan consent modal aktual harus diteliti pada fase terpisah yang diizinkan. Seluruh final confirmation nanti harus sesuai target/snapshot, bukan auto-accept dialog tak dikenal.

Jika capability tidak terverifikasi atau research mode: failed/unsupported_capability (exit5), tanpa klik apapun. Selama riset current implementation executor bahkan tidak memuat tindakan/selector Publish.

Setelah future submission: verifikasi receipt atau perubahan status dari server melalui read-only refresh. status submission_confirmed/exit0 hanya dengan bukti pengajuan; observed_status tetap raw+normalized. Tidak memakai status published/live karena submit/QC/delivery tidak sama dengan live.

Timeout/crash/network error setelah aksi mungkin terkirim -> submission_unknown, exit4, approval tetap consumed. Tidak automatic retry, rollback atau upload baru. Buka detail/read status untuk rekonsiliasi; bila belum pasti minta support/manusia. Kegagalan lokal sebelum klik setelah approval consumed juga tidak boleh membuat token reusable diam-diam.

State tambahan: publish_blocked → awaiting_publish_approval → publish_prepared → publish_attempted → submission_confirmed | submission_unknown | failed. Istilah bukan mapping status Too Lost yang sudah dibuktikan.

## Contoh dan acceptance

Contoh JSON di release-list.example.json, release-detail.example.json, release-publish-blocked.example.json adalah ilustrasi tanpa data akun. IDs contoh opaque, bukan hasil lookup remote. remote_verified membuktikan observasi halaman, tidak berarti coverage penuh atau siap publish.

Tes offline yang dibutuhkan:
- List pagination/filter bounded, dynamic-list duplicates, partial/empty distinction, inaccessible page bukan not_found.
- Detail ID/account mismatch, unknown fields/status, null media IDs, unsaved state dan snapshot completeness.
- Prepare blocked pada issue/identity unknown/unverified capability, tidak ada executable approval saat riset.
- Approval expiry/reuse, mismatch snapshot/account/ID/jadwal, concurrent writers dan manual edits.
- Publish attempt journal durable sebelum klik, response-lost menghasilkan unknown tanpa retry, submit confirmed bukan live.
- Konfirmasi asing, unexpected navigation/terms, AI exclusions berubah: stop.

Tidak menjalankan tes live publish pada fase riset sekarang. Perlu izin terpisah, kontrak approval direview, metadata/hak sah dan bukti UI sebelum implementasi/eksekusi final.
