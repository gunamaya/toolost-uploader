# Kontrak CLI release v1 — untuk review

Status: PROPOSAL, belum diimplementasikan/disetujui final. Versi kontrak `1` belum dirilis. Basis: bukti riset yang diindeks RESEARCH.md. Operasi draft serta release list/detail diusulkan; kontrak publish juga disertakan sebagai capability future yang disabled selama riset. Scope release/draft, bukan pengelolaan library Too Lost. Lihat [RELEASE-CONTRACT.md](RELEASE-CONTRACT.md) untuk kontrak list/detail/publish dan batas bukti.

Update review offline 25 Oktober 2026: pengguna menyetujui scope schema manifest/result validate + validator offline, nama distribusi/modul/executable, field minimal dan AI boolean wajib pada manifest upload normal. Implementasi script dan batas subset ada di [OFFLINE-VALIDATION.md](OFFLINE-VALIDATION.md). Ini tidak menyetujui seluruh proposal operasi akun/publish; v1 belum dirilis.

## Command

Nama executable `toolost`, distribusi `toolost-uploader`, modul `toolost_uploader` disetujui; ketersediaan nama PyPI belum diperiksa. Packaging lokal dan command `toolost validate` tersedia; command lain di bawah tetap proposal. Lihat README untuk instalasi lokal.

```sh
toolost login --profile <alias>
toolost validate <manifest.json> --json
toolost upload <manifest.json> --profile <alias> --json
toolost resume <run-id> --profile <alias> --json
toolost status <run-id> --profile <alias> --json
toolost release list --profile <alias> --page 1 --page-size 20 --json
toolost release detail <remote-release-id> --profile <alias> --json
toolost release publish <remote-release-id> --profile <alias> --prepare --json
toolost release publish <remote-release-id> --profile <alias> --approval <approval-id> --json
```

- login membuka Chrome khusus tanpa automation untuk login manual. Menolak --json; instruksi ke terminal. Tidak meminta password/OTP di CLI atau membaca cookie.
- validate offline, tidak membuka browser/network, tidak mengklaim kelayakan QC/DSP.
- upload memulai rencana dari manifest setelah preflight lengkap. ID lokal yang sudah punya checkpoint tidak boleh membuat draft baru diam-diam; arahkan ke resume.
- resume memakai snapshot manifest + hash pada run lokal dan mencocokkan profile/account/draft sebelum mutasi. Tidak membaca ulang file manifest berubah tanpa review.
- status membaca checkpoint dan, bila sesi dapat diverifikasi, membaca state draft melalui UI tanpa mutasi. Jika remote belum diperiksa, nyatakan remote_verified=false. release detail berbeda: menargetkan ID remote tanpa perlu run lokal.
- release list/detail read-only; publish prepare hanya review tanpa klik Publish. Eksekusi publish tidak diimplementasikan/diizinkan selama riset; approval draft tidak berlaku untuk publish. Detail gate dan hasil unknown ada di RELEASE-CONTRACT.md.
- --profile wajib pada command yang memakai akun. Nama profile alias lokal, bukan path atau artist. Aturan alias: ASCII huruf/angka, underscore, hyphen, panjang1–64; bukan . atau .. . Storage harus terisolasi per OS user, private permissions, bukan cwd atau Chrome harian. Lokasi final ditetapkan implementasi.
- Tidak ada delete CLI v1. Riset hapus membuktikan operasi tetapi bukan alasan menambah fitur destruktif. Track remote yang tidak ada di manifest tidak otomatis dihapus.

## Manifest

JSON UTF-8, satu rilis per manifest. Tolak duplicate JSON keys, unknown fields, schema_version lain, ID track duplikat, ordinal implisit, serta key kredensial. Batas ukuran/track diputuskan implementasi dengan pesan jelas, bukan disamakan dengan batas Too Lost yang belum diketahui.

Wajib:
- schema_version: integer1.
- release_id: ID stabil buatan integrator, ASCII safe1–128 karakter. Bukan judul, timestamp retry, atau remote draft ID.
- release_type: album | ep | single | compilation.
- title: string nonblank.
- release_date: tanggal ISO YYYY-MM-DD eksplisit, tidak mengambil default otomatis kalender UI.
- artwork: file reference wajib untuk operasi upload normal. Resume riset/manual draft parsial bukan otomatis menjadi manifest produksi valid.
- tracks: array nonempty; posisi array adalah urutan yang diinginkan, setiap elemen memiliki track_id stabil, title, audio dan ai_assisted boolean eksplisit.

File reference: {path: string, sha256: 64 lowercase hex}. Path relatif terhadap direktori manifest, bukan cwd; absolute path diperbolehkan untuk integrasi lokal. Resolve dan verifikasi regular readable file, hash dan ukuran sebelum browser dimutasi. Tidak memodifikasi sumber. Referensi symlink escape/TOCTOU perlu snapshot atau verifikasi ulang sebelum filechooser; kebijakan final harus dites, bukan sekadar Path.resolve. Lyrics opsional berupa file reference UTF-8, tidak otomatis menghapus section/instruksi atau mengaku cocok dengan audio. Integrator bertanggung jawab memasangkan take dan lirik yang disetujui.

Track optional fields yang telah diobservasi: version_line, language, instrumental, explicit, clean_version, isrc, iswc. Bila omitted, baca baseline UI dan laporkan inherited; jangan default boolean negatif. ai_assisted berbeda: wajib keputusan eksplisit untuk upload normal, missing menghasilkan invalid_input. Raw unknown state tetap dapat dilaporkan status saat inspect/resume, bukan dikonversi false.

ISRC/ISWC hanya boleh diberikan jika sudah diketahui; omission tidak mengirim kode palsu. Mapping switch code otomatis vs own code harus difinalkan sebelum implementasi penerapan override kode. Provenance_known_ai_generated optional boolean dapat memberi conflict warning ketika ai_assisted=false; bukan verifikasi hak legal.

Release optional fields awal: language, primary_genre, secondary_genre, label, copyright (c_year,c_owner,p_year,p_owner), upc. Omission mempertahankan baseline; jangan mengirim null/empty sebagai clear. Explicit clear belum didukung v1. Artist level rilis wajib dibaca dari baseline dan ditampilkan; pemilihan artist alternatif/multi-artist serta track writers/credits memerlukan mapping identity UI yang belum lengkap, sehingga belum menerima free-form pembuatan participant v1.

Tanggal original/preorder, timezone/time, stores/territories/additional delivery dan cover licensing dicatat sebagai capability pending; jangan menerima field tersebut lalu silently mengabaikannya. Baseline efektifnya dibaca dan dilaporkan untuk review. Dukungan eksplisit nanti ditambahkan dengan schema version/capability yang ditinjau. Banyak menu teramati bukan berarti semua kombinasi sudah didukung.

## Defaults dan consent

- Baca release/track default setelah form visible/stabil; native checked bisa berbeda dari aria-checked.
- Catat source inherited | explicit | ui_adjusted untuk nilai efektif. Jangan menyamakan profile alias browser dengan artist Too Lost.
- AI switch dapat mengubah stores/additional delivery. Read-back sesudah perubahan, laporkan delta dan unresolved documentation.
- Baseline layanan hak/monetisasi/AI training bukan izin baru mengaktifkannya; uploader tidak toggle service otomatis. Bila efek otomatis UI mengubah pilihan, report untuk review. V1 draft-only tidak menjamin kelayakan delivery final.
- Claim original/cover, writer legal dan hak yang belum diverifikasi adalah review_required, bukan nilai rekaan untuk menghilangkan issue.
- validate dapat memeriksa format dasar tetapi tidak menetapkan batas jumlah Album/EP dari label yang beririsan atau mengklaim validasi server/DSP selesai.

## Preflight dan approval draft

Sebelum Create Release/upload/Save: validasi semua file/hash/schema, profile lock, identitas akun terikat alias (fingerprint UI non-secret, jangan raw email di log), baseline dan rencana mutasi.

Mode interaktif menampilkan ringkasan dan meminta konfirmasi sebelum mutasi draft. Untuk integrator noninteractive, `--approve-draft` menegaskan izin create/upload/edit/save draft dari manifest itu, bukan publish, rights consent atau delete. Tanpa flag dan tanpa TTY, berhenti confirmation_required. Flag tidak membypass mismatch akun, ambiguous target, perubahan hash atau kebutuhan keputusan legal.

Akun pertama kali perlu manual binding/review; nama alias bukan bukti identitas. Jika fingerprint UI stabil tidak tersedia, berhenti untuk review, jangan memakai heuristic diam-diam. Mekanisme account binding masih blocker implementasi operasi akun unattended.

## Checkpoint dan state

Update simulasi offline: journal.py mendukung satu intent fake.save + reconcile read-only terhadap FakeAdapter memori. Bukan capability akun; tidak mengubah kontrak result CLI atau mengimplementasikan state remote. Lihat OFFLINE-JOURNAL.md untuk batasnya.

Subset offline internal kini tersedia: profil privat POSIX, lock, create/read snapshot manifest dan transisi lokal validated→cancelled dengan run/revision guard. Lihat LOCAL-STATE.md. Belum ada binding akun, remote state/mapping, attempt journal atau command status/resume; daftar field/state berikut tetap target proposal, bukan implementasi lengkap.

run_id adalah ID lokal unik; satu active writer per alias. Checkpoint berisi schema version, release_id, manifest canonical hash, source hashes, profile binding, remote draft ID bila diketahui, track mappings, rencana/attempts, observed order, last verified state. Simpan atomik, permission privat; tidak kredensial/raw lyric/network bodies.

State utama:
validated → confirmation_required/ready → draft_created → media_processing → metadata_staged → save_pending → draft_saved.

Jalur penghentian: login_required, conflict, reconciliation_required, cancelled, failed. Bukan semua langkah linear: staged bisa hilang pada reload; file ingest dapat bertahan terpisah.

- Catat attempt sebelum mutasi dan observed result sesudahnya. Timeout setelah attempt bukan bukti rollback.
- draft_saved hanya setelah read-back draft dan field/media/order yang diklaim. issues boleh nonempty; release_ready tidak digunakan v1.
- Done tidak sama dengan persisted. Save bisa dialog Save atau navigasi daftar; tunggu outcome aktual, bukan selector satu jalur.
- Hash lokal bukan hash audio remote. Jika remote track identity tidak dapat dibuktikan (duplicate names/normalisasi/partial ingest), reconciliation_required, bukan upload ulang.
- Missing track yang dulu ada mungkin dihapus pengguna. Conflict, jangan restore otomatis.
- Jika crash setelah create sebelum ID tersimpan, jangan membuat draft lagi; minta rekonsiliasi target yang ambigu. Jangan dedupe hanya judul.
- Retry metadata/Save hanya sesudah desired vs actual diperiksa dan tidak konflik. Tidak ada blind retry Create Release, Upload atau deletion.
- Cancel menghentikan tindakan lokal/worker dan melaporkan remote outcome known/unknown; tidak menjanjikan proses server ikut berhenti. Jangan logout/kill Chrome harian.

## Hasil JSON

Dengan --json: stdout tepat satu objek JSON final, tanpa banner/progress. stderr progres yang disensor. --json tidak mengandung cookie/password/raw lyrics atau path private yang tidak dibutuhkan. Contoh docs/contract-result.example.json; belum output aktual CLI.

Field wajib: schema_version, command, run_id (nullable sebelum run dibuat), status, profile (alias nullable untuk validate), release_id, draft_id, remote_verified, issues, warnings, error. error nullable atau {code,message,retryable}; retryable berarti dapat dicoba setelah rekonsiliasi/aksi manusia yang dijelaskan, bukan otomatis aman. issues berupa {code,scope,message}; scope release atau track_id. Nama issue lokal stabil terpisah dari label UI yang dapat berubah.

status: valid, invalid_input, confirmation_required, draft_saved, login_required, conflict, reconciliation_required, cancelled, failed. Ekstensi operasi release: ok, partial, not_found, blocked, publish_prepared, submission_confirmed, submission_unknown. Status tersebut bukan status DSP live. Untuk status command gunakan observed_state terpisah (nullable); jangan menciptakan draft_saved dari checkpoint yang belum remote_verified. Hasil tambahan track_results: {track_id,remote_identity,identity_verified,state}; remote_identity nullable dan bukan label filename yang dianggap ID. Operasi release memiliki data object dan remote_release_id; run_id/release_id/draft_id nullable sesuai konteks. Lihat RELEASE-CONTRACT.md.

Exit code proposal:
- 0: validate valid, upload/resume draft_saved terverifikasi (meski issues), status berhasil dibaca sesuai remote_verified yang dilaporkan; release list/detail ok atau future publish_prepared/submission_confirmed dengan bukti yang memadai.
- 2: invalid_input, schema/CLI/file validation.
- 3: login_required.
- 4: conflict, reconciliation_required, partial, blocked atau submission_unknown; hentikan mutasi/retry sampai direview.
- 5: failed (UI/network/unsupported capability).
- 6: confirmation_required.
- 7: not_found release hanya setelah ketidakhadiran terverifikasi pada akun benar; bukan timeout/auth error.
- 130: cancelled oleh pengguna/SIGINT, final JSON best effort jika channel tersedia.

Konsumen wajib membaca status+issues+remote_verified, bukan exit0 saja. Kegagalan menulis JSON/checkpoint sendiri harus nonzero, bukan sukses palsu.

## Tes penerimaan sebelum implementasi live

1. Parser manifest: unknown/duplicate keys, code types, hash mismatch, relative paths, missing AI state, duplicate track_id, no profile injection.
2. Offline fake pages/fixtures untuk overlay, delayed panels, aria/native checked mismatch, filechooser multi-stage, reversed ingest, Save dialog/navigation/error.
3. Checkpoint atomicity dan crash-attempt unknown; rerun tidak membuat release/upload duplikat; missing remote track tidak direstore.
4. stdout JSON/stderr separation, exit mapping, lock conflict, interrupt cleanup, credential redaction.
5. Live draft-only smoke setelah persetujuan: profile binding, create → upload → apply explicit metadata → reorder → Save → reopen.
6. Tidak memasukkan selectors/tindakan Publish di v1 executor. Publish phase berikutnya terpisah, approval terikat akun+draft+snapshot konten, belum boleh diuji sekarang.

## Review yang masih diperlukan

- Setujui field minimal, default semantics dan CLI names sebelum membuat schema formal/validator.
- Pastikan bagaimana integrator memberi approval take final dan fingerprint akun UI yang stabil.
- Tentukan scope writer/artist overrides, original/cover dan rights review; belum cukup bukti untuk unattended release final.
- Failure upload partial/server-saved-response-lost/expired session belum diuji. Kontrak fail-closed dapat ditulis sekarang, tetapi kemampuan recovery otomatis tidak boleh diklaim.
