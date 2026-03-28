from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGGa31S2"
plain = "automata2026"

print(f"VERIFICACIÓN: {pwd_context.verify(plain, hashed)}")
