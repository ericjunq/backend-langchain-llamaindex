import re
from pydantic import AfterValidator, EmailStr
from typing import Annotated

# Os validadores aceitam o valor com ou sem máscara ("123.456.789-09")
# e devolvem só os dígitos, que é o formato salvo no banco (colunas de 11/14 chars).

def _digitos(valor: str) -> str:
    return re.sub(r'\D', '', valor)

def validar_telefone(telefone: str) -> bool:
    # DDD + 8 dígitos (fixo) ou DDD + 9 dígitos (celular)
    return len(_digitos(telefone)) in (10, 11)

def validar_cpf(cpf: str) -> bool:
    cpf = _digitos(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    total = sum(int(cpf[i]) * (10 - i) for i in range(9))
    remainder = (total * 10) % 11
    if remainder == 10:
        remainder = 0
    if remainder != int(cpf[9]):
        return False
    total = sum(int(cpf[i]) * (11 - i) for i in range(10))
    remainder = (total * 10) % 11
    if remainder == 10:
        remainder = 0
    if remainder != int(cpf[10]):
        return False
    return True

def validar_cnpj(cnpj: str) -> bool:
    cnpj = _digitos(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(cnpj[i]) * pesos[i] for i in range(12))
    remainder = total % 11
    primeiro = 0 if remainder < 2 else 11 - remainder
    if primeiro != int(cnpj[12]):
        return False
    pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(cnpj[i]) * pesos[i] for i in range(13))
    remainder = total % 11
    segundo = 0 if remainder < 2 else 11 - remainder
    if segundo != int(cnpj[13]):
        return False
    return True

# --- Checadores (levantam erro se inválido e normalizam) ---

def checar_cpf(v: str) -> str:
    if not validar_cpf(v):
        raise ValueError('CPF inválido')
    return _digitos(v)

def checar_cnpj(v: str) -> str:
    if not validar_cnpj(v):
        raise ValueError('CNPJ inválido')
    return _digitos(v)

def checar_telefone(v: str) -> str:
    if not validar_telefone(v):
        raise ValueError('Telefone inválido')
    return _digitos(v)

def checar_email(v: str) -> str:
    v = v.strip().lower()
    if len(v) > 60:
        raise ValueError('Email muito longo (máx. 60 caracteres)')
    return v

# --- Tipos reutilizáveis ---

CPF = Annotated[str, AfterValidator(checar_cpf)]
CNPJ = Annotated[str, AfterValidator(checar_cnpj)]
Telefone = Annotated[str, AfterValidator(checar_telefone)]
Email = Annotated[EmailStr, AfterValidator(checar_email)]
