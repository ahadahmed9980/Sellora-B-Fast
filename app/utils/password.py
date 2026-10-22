from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def confirm_Password(plain_password, hash_password) -> bool:
    return password_hash.verify(plain_password, hash_password)
