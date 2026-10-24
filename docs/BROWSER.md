# Browser riset

Python + Playwright, Chrome lokal, profil terpisah di `.local/chrome-profile`.

## Login manual

```sh
.venv/bin/python scripts/gather.py login
```

Chrome dibuka sebagai proses biasa, tanpa Playwright atau remote debugging. Login dilakukan pengguna, termasuk CAPTCHA/2FA. Jangan mengambil capture login, membaca password/cookie, menyalin profil harian, atau mengakali penolakan Google. Cara ini tidak menjamin Google mengizinkan login.

Setelah login berhasil, tutup seluruh jendela Chrome dengan profil project ini dan tunggu proses login selesai. Jangan hapus profile lock secara manual.

## Observasi setelah login

```sh
.venv/bin/python scripts/gather.py observe
```

Chrome dibuka ulang pada profil yang sama dengan port debugging loopback 9437, kemudian Playwright attach via CDP. Port ini memberi kendali browser kepada proses lokal; jangan expose/tunnel ke jaringan. Tidak ada stealth flag, patch navigator.webdriver, maupun capture otomatis.

Capture hanya setelah pengguna mengonfirmasi halaman non-login siap:

```sh
touch .local/capture.request
```

Capture manual berupa teks halaman, deskripsi kontrol tanpa membaca nilai input, dan screenshot viewport. Semua hasil privat di `.local/captures/`; screenshot/teks tetap dapat memuat data akun. Guard URL/password bukan detektor login lengkap: operator wajib memastikan bukan halaman autentikasi, termasuk modal/iframe.

Berhenti dan tutup browser milik script:

```sh
touch .local/stop.request
```

Jangan beralih mode saat Chrome project masih berjalan. Script menolak lock aktif/tidak dikenal; lock hostname lokal dengan PID mati diserahkan ke Chrome untuk ditangani tanpa penghapusan manual. Tes ini bukan jaminan bebas race/PID reuse; lock native Chrome tetap otoritas akhir.

Script ini khusus observasi; tidak mengisi form, membuat draft, upload, autosave atau publish. Tindakan riset terpisah tetap mengikuti izin pengguna. Rancangan multi-profile produksi ada di CONTRACT-PLAN.md; script saat ini hanya mendukung satu profil riset. Tes default offline: `.venv/bin/python -m unittest discover -s tests -v`.
