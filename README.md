# Tunas Daud Lost & Found

Website informasi barang temuan dan laporan kehilangan untuk lingkungan sekolah.

## Fitur
- Halaman publik untuk melihat dan mencari barang temuan.
- Formulir laporan kehilangan.
- Login admin menggunakan username dan password hash.
- Dashboard untuk menambah, menghapus, dan mengubah status barang.
- Pengelolaan status laporan kehilangan.
- Mendukung SQLite untuk uji lokal dan PostgreSQL untuk hosting.

## Jalankan secara lokal
1. Instal Python 3.
2. Buka terminal pada folder proyek.
3. Buat virtual environment (opsional tetapi disarankan):
   - Windows: `python -m venv .venv`
   - Windows PowerShell: `.venv\\Scripts\\Activate.ps1`
4. Instal paket: `python -m pip install -r requirements.txt`
5. Jalankan: `python app.py`
6. Buka `http://127.0.0.1:5000`.

Untuk uji lokal, halaman publik dan formulir laporan dapat digunakan. Login admin memerlukan pengaturan variabel lingkungan `ADMIN_USERNAME` dan `ADMIN_PASSWORD_HASH`.

## Membuat hash password admin
Jalankan:
`python create_password_hash.py`
Masukkan password minimal 12 karakter. Salin hash yang dihasilkan. Jangan bagikan hash atau password.

Atur environment:
- `SECRET_KEY`: string acak panjang dan rahasia.
- `ADMIN_USERNAME`: username admin yang disetujui sekolah.
- `ADMIN_PASSWORD_HASH`: hash dari script di atas.
- `DATABASE_URL`: URL PostgreSQL (di hosting).
- `COOKIE_SECURE=1` untuk HTTPS.

## Deploy ke Render
1. Buat repository GitHub dan unggah seluruh isi folder ini.
2. Di Render, pilih New > Blueprint dan hubungkan repository.
3. Render membaca `render.yaml` untuk membuat web service dan database.
4. Isi `ADMIN_USERNAME` dan `ADMIN_PASSWORD_HASH` pada Environment service.
5. Pastikan `SECRET_KEY` dibuat secara acak dan rahasia.
6. Deploy, lalu buka URL `.onrender.com` yang diberikan.

Catatan:
- `render.yaml` meminta paket database Free sebagai contoh. Ketersediaan dan kebijakan paket gratis dapat berubah; pilih paket yang sesuai kebutuhan.
- Jangan gunakan data pribadi siswa yang sensitif. Kontak pelapor hanya untuk admin, tetapi pada versi demo ini kontak laporan hanya ditampilkan di dashboard admin.
- Sebelum dipakai resmi, minta persetujuan sekolah, gunakan akun admin yang dikelola sekolah, tetapkan prosedur penyerahan barang, backup database, dan uji keamanan.
- Ini adalah starter project siap dikembangkan, bukan layanan yang sudah diterbitkan ke internet.
