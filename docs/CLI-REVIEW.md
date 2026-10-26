# Review subset CLI draft dan kontrak integrator

Dokumen ini adalah hasil review bounded dari task **CLI-01** (25 Oktober 2026).
Tujuan: memetakan realitas implementasi saat ini terhadap proposal [CONTRACT-V1](CONTRACT-V1.md), mengidentifikasi gap integrator `yt-to-flowmusic`, dan menyajikan rekomendasi slice produk terkecil untuk keputusan pengguna. Task ini bersifat **review/proposal saja**, bukan izin implementasi atau mutasi akun live.

---

## 1. Status Command: Implemented vs Proposed vs Unsupported

| Command / Entry point | Status | Lokasi kode | Keterangan & Batas |
|---|---|---|---|
| `toolost validate <manifest> [--json]` | **Implemented** | `toolost_uploader/cli.py`, `toolost_uploader/validation.py` | Offline penuh, stdlib, memeriksa schema v1, hash artwork/audio lokal, exit 0/2/5. Tidak menyentuh network/browser. |
| `toolost login --profile <alias>` | **Proposed** | Proposal di `docs/CONTRACT-V1.md` | Belum ada di CLI. Bantuan pembuka browser manual ada di `scripts/gather.py`, tetapi belum menjadi command terpasang. |
| `toolost upload <manifest> --profile <alias> [--json]` | **Proposed / Parsial di script** | `scripts/upload_draft.py`, `toolost_uploader/live_draft.py` | **Belum tersedia di CLI terpasang `toolost`**. Hanya tersedia sebagai script Playwright mandiri `scripts/upload_draft.py` dengan pembatasan ketat: hanya Single 1 track, stop di Save (draft-only), butuh CDP loopback operator. |
| `toolost resume <run-id> --profile <alias> [--json]` | **Proposed / Bounded di script** | `toolost_uploader/live_draft.py` (`--reconcile-readback-only`) | Belum ada di CLI terpasang. Recovery debugging lama dimatikan. Hanya readback rekonsiliasi pasca-Save yang didukung di script; resume produksi ([RES-01](ANTRIAN-PEKERJAAN-UTAMA.md)) berstatus **deferred**. |
| `toolost status <run-id> --profile <alias> [--json]` | **Proposed** | Proposal di `docs/CONTRACT-V1.md` | Belum diimplementasikan. Belum ada command inspect draft status tanpa menjalankan alur draft. |
| `toolost release list / detail` | **Proposed / Parsial parser** | `toolost_uploader/read_only.py` | Parser snapshot UI tersedia di `read_only.py` (offline), tetapi belum ada subcommand CLI atau alur Playwright live untuk navigasi katalog. |
| `toolost release publish` | **Unsupported / Deferred** | `docs/RELEASE-CONTRACT.md` | **Dilarang keras selama riset**; [PUB-01](ANTRIAN-PEKERJAAN-UTAMA.md) deferred; tidak ada eksekusi publish. |

---

## 2. Perbandingan Dukungan Manifest: Validator vs Live Draft

| Bagian Manifest | Dukungan di `validation.py` (Validator) | Dukungan di `live_draft.py` (Live Executor) | Gap & Dampak |
|---|---|---|---|
| **Release Type** | `album`, `ep`, `single`, `compilation` | **Hanya `single`** | Jika manifest bertipe `album` atau `ep`, validator meloloskan tetapi live draft melempar `unsupported_live_manifest`. |
| **Jumlah Track** | Array nonempty (1 sampai N track) | **Tepat 1 track** (`len(tracks) == 1`) | Multi-track belum didukung di live draft. |
| **Track Fields** | `track_id`, `title`, `audio`, `ai_assisted`, + optional fields (`version_line`, `language`, `instrumental`, `explicit`, `clean_version`, `isrc`, `iswc`, `lyrics`, `provenance_known_ai_generated`) | **Hanya 4 field wajib**: `{'track_id', 'title', 'audio', 'ai_assisted'}` | Field opsional apa pun pada track akan memicu `unsupported_live_track_fields`. |
| **Release Fields** | `schema_version`, `release_id`, `release_type`, `title`, `release_date`, `artwork`, `tracks`, + optional (`language`, `primary_genre`, `secondary_genre`, `label`, `copyright`, `upc`) | **Hanya 7 field dasar** | Field opsional release memicu `unsupported_live_manifest`. |
| **Release Date** | Format `YYYY-MM-DD` wajib valid | **Belum diterapkan ke UI form** | Nilai `release_date` dari manifest belum diisikan ke picker tanggal Too Lost; UI mewarisi default tanggal kalender Too Lost dengan flag eksplisit `--accept-ui-date-for-smoke`. |
| **Judul Track Single** | Diperbolehkan berbeda dari judul release | **Terkunci di UI Too Lost** | UI Too Lost mengunci judul track Single sama dengan judul release; live draft memerlukan judul sama persis atau flag `--approve-release-title-equals-track`. |

---

## 3. Format Output & Exit Codes

### CLI Terpasang (`toolost validate`)
- **Stdout (`--json`)**: Objek JSON validasi manifest tunggal:
  ```json
  {"status": "valid", "warnings": [], "error": null, "manifest": {...}}
  ```
- **Exit codes**:
  - `0`: Manifest valid.
  - `2`: Manifest tidak valid atau argumen CLI salah.
  - `5`: Kesalahan I/O fatal (misal file tidak ditemukan).

### Script Draft (`scripts/upload_draft.py`)
- **Stdout**:
  - Sukses subset:
    ```json
    {
      "status": "draft_saved_subset",
      "run_id": "...",
      "draft_id": "12345",
      "warnings": [
        "Tanggal UI diwarisi; bukan release_date manifest terverifikasi.",
        "Remote track identity dan rights/services belum diverifikasi; bukan siap distribusi."
      ]
    }
    ```
  - Reconcile readback:
    ```json
    {
      "status": "draft_readback_subset",
      "run_id": "...",
      "draft_id": "12345",
      "warnings": [...]
    }
    ```
  - Gagal / Stop guard:
    ```json
    {
      "status": "reconciliation_required",
      "code": "<DraftError_code>",
      "error": "Operasi dihentikan; periksa checkpoint privat sebelum tindakan berikutnya. Jangan retry create/upload/Save."
    }
    ```
- **Exit codes**:
  - `0`: Sukses draft tersimpan atau readback terverifikasi.
  - `2`: Argumen CLI tidak valid.
  - `4`: `reconciliation_required` (kesalahan proses Playwright, target berubah, timeout, atau identity guard).

---

## 4. Gap Integrasi dengan `yt-to-flowmusic`

Berdasarkan telaah arsitektur `ProcessRunner` / `FlowClient` di `yt-to-flowmusic`:
1. **Invokasi Subprocess**:
   - Integrator memanggil executable terpasang via command line (misal `toolost <subcommand> --json`).
   - Saat ini integrator **tidak dapat** memanggil fitur draft karena fungsionalitas tersebut baru ada di `scripts/upload_draft.py`, bukan di executable `toolost`.
2. **Ketergantungan Parameter Browser**:
   - `upload_draft.py` memerlukan argumen operator tingkat rendah: `--cdp http://127.0.0.1:9437`, `--expected-account <ID>`, `--approve-draft`, dan `--accept-ui-date-for-smoke`.
   - Pada kontrak integrator, konfigurasi browser dan akun seharusnya diabstraksikan melalui parameter `--profile <alias>`, di mana profile menyimpan metadata sesi terisolasi (sesuai modul `storage.py`), tanpa membocorkan detail port/ID mentah pada tiap panggilan tingkat aplikasi.
3. **Ekspektasi Jenis Rilis**:
   - `yt-to-flowmusic` memiliki modul produksi album (`production/album_designer.py`). Jika integrator mencoba mengirim album multi-track, live uploader saat ini akan langsung menolak. Integrator harus dibatasi secara eksplisit hanya memproduksi Single 1-track jika ingin berintegrasi dengan uploader saat ini.
4. **Pemisahan Log Progres vs JSON Result**:
   - Integrator mem-parse `stdout` sebagai JSON murni (`json.loads(text)`). Output teks manusia, banner progres, atau log peringatan harus disalurkan ke `stderr` agar tidak merusak deserialisasi JSON di integrator.

---

## 5. Rekomendasi: Slice Implementasi Terkecil (Smallest Viable Slice)

Untuk menjembatani gap di atas tanpa overengineering atau membuka risiko di luar batas yang disetujui, direkomendasikan slice implementasi produk berikut:

### Usulan Task: `CLI-02` — CLI Subcommand `upload-draft` Terintegrasi
Mempromosikan kemampuan `scripts/upload_draft.py` ke dalam entry point resmi `toolost` sebagai subcommand:
```sh
toolost upload-draft <manifest.json> --profile <alias> --expected-account <account-id> [options] --json
```

#### Spesifikasi Slice:
1. **Scope Masuk**:
   - Menambahkan parser subcommand `upload-draft` di `toolost_uploader/cli.py`.
   - Menghubungkan parser ke fungsi `execute()` di `toolost_uploader/live_draft.py`.
   - Standarisasi flag: `--profile`, `--expected-account`, `--cdp` (default 127.0.0.1:9437), `--approve-draft`, `--accept-ui-date`, `--json`.
   - Menjamin `stdout` hanya berisi satu baris JSON hasil, sementara pesan info/warning ke `stderr`.
   - Exit code konsisten: `0` (sukses draft subset), `2` (invalid input/argumen/manifest), `4` (reconciliation required / draft error), `5` (OS error).
   - Tes unit offline menggunakan mock Playwright (memperluas `tests/test_cli.py`).
2. **Scope Keluar**:
   - Tidak mencakup multi-track atau album (tetap Single 1-track).
   - Tidak mencakup pengisian `release_date` ke UI form (tetap mengandalkan inherit UI date).
   - Tidak mencakup resume mutasi otomatis (tetap fail-stop ke status reconciliation required).
   - Tidak mencakup publish atau distribusi.
   - Tidak melakukan pengujian live baru (menggunakan tes mock offline).

---

## 6. Keputusan yang Diperlukan dari Pengguna

Sebelum melanjutkan ke implementasi berikutnya, mohon konfirmasi keputusan atas opsi berikut:
1. **Pilihan Penamaan Subcommand**:
   - **Opsi A (Rekomendasi)**: `toolost upload-draft` — nama eksplisit yang menegaskan bahwa command ini hanya menyimpan draft di Too Lost (tidak melakukan publish).
   - **Opsi B**: `toolost upload --draft-only` — menggunakan kata `upload` dengan flag wajib `--draft-only`.
2. **Kesiapan Scope Integrator**:
   - Apakah integrasi tahap pertama dengan `yt-to-flowmusic` difokuskan khusus untuk rilis bertipe **Single (1 track)** terlebih dahulu, sesuai kesiapan live executor saat ini?
