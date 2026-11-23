from getpass import getpass
from werkzeug.security import generate_password_hash

password = getpass("Buat password admin: ")
if len(password) < 12:
    raise SystemExit("Gunakan minimal 12 karakter.")
print("\nSimpan nilai berikut sebagai ADMIN_PASSWORD_HASH di pengaturan Environment hosting:\n")
print(generate_password_hash(password))
