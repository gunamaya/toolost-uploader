# Hapus satu track dari draft

Observasi 2026-10-25. Pengguna secara eksplisit mengizinkan penghapusan Sungai Teh Susu dari draft riset. Tidak hapus seluruh draft, tidak upload ulang, tidak Publish/distribusi, tidak mengubah file sumber lokal.

## Identifikasi dan konfirmasi

- ID draft URL harus cocok dengan draft pengganti yang dikenal.
- Baseline sebelum mutasi: tepat dua baris, berurutan Terangnya Belum Pulang dan Sungai Teh Susu, keduanya masih berjudul basename MP3.
- Scope `.track-item` ke judul target unik `sungai-teh-susu-6210c7bc`. Tombol hapus `.track-item__remove` berupa ikon tanpa accessible name; tidak memilih tombol anonim global.
- Klik ikon menampilkan dialog heading Remove track, teks `Remove "sungai-teh-susu-6210c7bc" from your release?`, Cancel / Remove.
- Cocokkan nama pada dialog sebelum Remove. Tidak menguji bulk removal/Select all.

## Eksekusi dan hasil

1. Klik Remove sekali. Daftar lokal menjadi tepat satu track: `terangnya-belum-pulang-9b8d6c8c`.
2. Save Changes membuka konfirmasi Save; klik Save dan tunggu Saving your release hilang.
3. Buka All Releases, cocokkan ID/status Draft, Edit draft yang sama, Manage Tracks.
4. Assert tepat satu judul baseline yang ingin dipertahankan dan tidak ada Sungai Teh Susu. Lulus.
5. Kedua path audio sumber pada manifest fixture lokal masih file yang tersedia. File sumber tidak dimodifikasi oleh script ini.

Tidak melakukan reload sebelum Save untuk menguji apakah Remove langsung persist. Karena itu hasil hanya membuktikan Remove→Save→reopen; jangan menyimpulkan Remove selalu staged atau selalu autosave.

## Batas dan konsekuensi resume

- Penghapusan dari release terbukti. Penghapusan dari library/storage remote, refund, reuse track, restorability dan undo belum diketahui. Teks dialog tidak menyatakan penghapusan file sumber lokal.
- Jangan upload ulang track yang hilang sebagai fallback resume: hilangnya track bisa perubahan manual/destruktif yang disengaja.
- Checkpoint lama dua track sekarang HISTORIS. Baseline terkini satu track. Hasil assertion resume lama tidak boleh dipakai ulang tanpa rekonsiliasi dan persetujuan desired state baru.
- Automasi penghapusan membutuhkan izin eksplisit, akun/draft/track target yang cocok serta review diff. Jangan menyamakan remove track draft dengan takedown rekaman yang sudah published.
- Nama duplikat masih ambiguous; title-only selection pada fixture unik ini bukan strategi produksi universal.

## State akhir

Draft pengganti masih Draft · Album, tepat satu MP3 Terangnya Belum Pulang berjudul basename; tanpa artwork. Metadata final/AI/lirik belum diterapkan. Tidak ada Publish dan tidak ada track baru dibuat.

Bukti privat `.local/captures/track-removal/`: before.yml, confirmation.yml, after-remove.yml, reopened.yml, result.json. Assert live read-back satu track dan keberadaan dua file sumber lokal lulus; tidak ada klaim library remote ikut terhapus.
