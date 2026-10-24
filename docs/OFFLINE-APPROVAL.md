# Gate binding/approval sintetis offline

Pengguna menyetujui gate offline: binding pertama direview manusia; identitas unavailable/berubah memblokir; approval terikat profile, account/draft, manifest/checkpoint dan rencana. Implementasi `approval.py` hanya menerima identitas literal `synthetic-account`/`synthetic-draft`. **Ini tidak memverifikasi identitas Too Lost**, tidak membuka browser dan tidak memberi izin executor nyata. Sumber fingerprint UI stabil tetap blocker.

## Perilaku yang tersedia

- `bind`: reviewed harus boolean True, satu binding immutable per profile dalam `_offline-binding.json` privat ber-lock. Unknown identity ditolak. Tidak ada rebind/reset/deletion; tidak menulis account_fingerprint pada profile.json/checkpoint, keduanya tetap null.
- `approve`: exact run/checkpoint revision validated, binding cocok, approved=True. Plan hanya operations unik dari fake.upload/fake.edit/fake.save dan desired_sha256 lowercase; publish/delete/unknown fields ditolak. Tidak mengarang consent rights/credits/delivery.
- Record `<release_id>.approval.json`: authority synthetic-offline, alias, target, run, hash checkpoint, hash plan, UUID approval, approved/consumed dan canonical record hash. Exact hash checkpoint mengikat snapshot manifest dan revisi. Satu approval per checkpoint; existing/corrupt file tidak ditimpa.
- `consume`: periksa binding/identity/run/token/plan/checkpoint terbaru, lalu simpan consumed atomik sebelum return. Mismatch tidak memperbarui approval lama dan tidak melakukan mutasi; consume dengan plan lama tetap hanya sah bila input exact cocok. Perubahan target/plan/checkpoint harus menghasilkan approval baru melalui flow review masa depan, bukan mengubah token lama.
- Write outcome unknown sesudah rename membuat caller berhenti; record yang sudah consumed tidak boleh dipakai ulang. Tidak ada executor yang dipanggil dari gate; fake journal/UI/upload yang ada belum diwajibkan memanggil gate ini.

Ini aturan local safety untuk caller kooperatif, bukan security boundary: boolean review dari caller bukan bukti manusia sungguhan, hash bukan MAC, token disimpan private tetapi bukan secret/password atau bearer authorization layanan. Tidak ada log raw identity/path. Profile lock/permissions/symlink/atomic-write mengikuti LOCAL-STATE.md. Binding disimpan di directory checkpoint profile untuk tahap kecil ini, bukan browser identity manager.

## Batas dan keputusan berikutnya

Belum ada TTL, approval renewal, multi-attempt, invalidation history, command binding/approve, UI account identity extraction, account/draft mapping, approval interactive/noninteractive CLI, atau wiring ke executor. Tidak ada create di plan karena target draft baru belum punya identitas terverifikasi; create approval flow tetap perlu review terpisah. Publikasi musik/PyPI, live smoke dan perubahan akun tidak diizinkan oleh gate offline.

Tes sintetis: manual review required, immutable binding, missing approval/binding, account/draft unavailable/mismatch, stale checkpoint/plan, token satu-pakai, corruption, unsupported publish/delete, dan fsync-after-rename unknown yang tetap consumed. Fixtures temporary directory, bukan profil riset.

Verifikasi sesi ini pada macOS/Python 3.14.7: build wheel melalui sdist berhasil; suite lengkap dengan schema dan instalasi wheel bersih **86/86 lulus tanpa skip**. `git diff --check` bersih. Tidak ada browser atau tindakan akun.
