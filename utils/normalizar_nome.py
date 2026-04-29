import re
import unicodedata

def normalizar_nome(nome: str) -> str:
    nome = nome.strip().lower()

    # remove acentos
    nome = unicodedata.normalize("NFD", nome)
    nome = nome.encode("ascii", "ignore").decode("utf-8")

    # remove tudo que não for letra ou número
    nome = re.sub(r'[^a-z0-9]', '', nome)

    return nome