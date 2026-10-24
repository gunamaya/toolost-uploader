# Uji resume setelah restart browser

Observasi 2026-10-25. Scope disetujui: uji resume pada draft riset dan dua audio yang sudah diupload. Tidak Create Release, upload tambahan, reorder baru, Save tambahan, penghapusan, Publish/distribusi atau perubahan kredensial pada uji ini.

## Skenario yang benar-benar diuji

**Draft sudah tersimpan → browser ditutup terkontrol → browser proses baru dengan profil sama → rekonsiliasi melalui daftar rilis → buka Edit → read-back dua track.**

Ini bukan crash saat upload/Save, bukan session expired, dan bukan implementasi command resume produk.

## Langkah dan hasil

1. Cocokkan ID URL draft dengan hasil uji MULTI-TRACK.md. Buka Manage Tracks dan assert count2 serta urutan sama dengan hasil save sebelumnya. Simpan baseline privat.
2. Buat `.local/stop.request`; script gather keluar dari observasi dan menghentikan Chrome miliknya sendiri. Tidak mematikan Chrome harian.
3. Periksa profile_in_use=false dan port9437 tertutup. Tidak memulai dua proses browser pada profil sama.
4. Mulai proses `scripts/gather.py observe` baru pada profil sama. Login manual tidak perlu diulang pada sesi ini; bukan jaminan sesi tidak akan kedaluwarsa.
5. Buka All Releases, bukan /uploader atau Create New Release. Cari link Edit berdasarkan ID draft yang sudah diketahui; cocokkan kartu judul riset dan status Draft sebelum membuka.
6. Daftar memiliki tepat satu kartu rilis. Draft lama yang sudah dihapus tidak dibuat ulang.
7. Edit draft target, Manage Tracks: count2 dan urutan Terangnya Belum Pulang → Sungai Teh Susu (nama file awal) sama dengan baseline. Assert keduanya lolos. Tidak upload ulang.

State akhir browser: draft pengganti yang sama, Manage Tracks. Metadata final belum dilengkapi: filename title, lyrics kosong, AI-assisted defaultfalse dari uji baseline, belum artwork. Jangan menyimpulkan siap distribusi.

## Kekuatan dan batas pencocokan

- ID draft dicocokkan dari URL/tautan, status dan judul kartu juga diverifikasi.
- Track diperiksa berdasarkan jumlah dan dua judul basename unik dari fixture yang hash lokalnya telah dicatat. Ini cukup untuk read-back fixture ini, bukan bukti hash remote atau isi audio identik.
- Inspeksi `.track-item` pada UI ini hanya mengungkap class dan tidak ada link/ID track pada atribut yang diamati. Tidak membaca internal framework state, cookie atau response body jaringan untuk mencari ID.
- Nama duplikat/filename ternormalisasi serta track remote diganti pengguna belum ditangani. Jangan mengklaim resume upload partial aman hanya dari judul/count.
- UI tidak memperlihatkan autentikasi akun unik yang dibandingkan dengan binding profil formal pada uji ini; profil khusus dan draft ID yang diketahui digunakan. Verifikasi account binding produksi masih perlu desain/uji.

## Dampak kontrak

- Resume harus menerima referensi draft/profil yang tersimpan, memeriksa state remote terlebih dahulu, lalu skip tindakan yang sudah terverifikasi.
- Jangan memulai Create Release/Upload sebagai fallback otomatis ketika hasil sebelumnya belum diketahui atau target tidak ditemukan.
- Bila target/account tidak cocok, session expired, track ambiguous atau reconciliation tidak lengkap: berhenti dengan status perlu review/login, bukan menebak.
- Simpan checkpoint hanya setelah read-back yang mendukung klaimnya; log percobaan mutasi terpisah dari hasil terverifikasi.
- Satu writer per profil tetap diperlukan. Tidak ada race/concurrency test pada uji ini.

## Riset berikutnya yang terpisah

1. Resume proses CLI tanpa menutup browser dan idempotent rerun pada no-op fixture; belum ada CLI produk untuk diuji.
2. Gangguan saat transfer/encoding/Save: gunakan mocks offline dahulu; uji live harus dibatasi dan dikomunikasikan. Outcome unknown harus direkonsiliasi sebelum retry, tanpa upload duplikat untuk menutupi ketidakpastian.
3. Session expired/account mismatch: jangan logout atau menghapus sesi pengguna untuk tes tanpa izin terpisah.
4. Multi-file partial success, duplicate basename, dan ketahanan identifier per track.
5. Unsaved edits/Done/autosave vs Save serta deteksi konflik perubahan manual.

Bukti privat `.local/captures/resume/`: baseline.json/yml, after-restart-list.yml, after-restart-tracks.yml, result.json. Tes live read-back di atas lulus; tidak ada pytest atau klaim keseluruhan failure recovery lulus.
