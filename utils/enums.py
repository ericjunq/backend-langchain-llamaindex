from enum import Enum

class CargosEnum(str, Enum):
    dono = 'dono'
    admin = 'admin'
    funcionario = 'funcionario'

class CargosFuncionarios(str, Enum):
    admin = 'admin'
    funcionario = 'funcionario'

class PeriodoEnum(str, Enum):
    mes = "mes"
    semestre = "semestre"
    ano = "ano"

class StatusVenda(str, Enum):
    concluida = 'concluida'
    cancelada = 'cancelada'

class FormaPagamento(str, Enum):
    pix = 'pix'
    cartao_credito = 'cartao_credito'
    cartao_debito = 'cartao_debito'
    boleto = 'boleto'
    dinheiro = 'dinheiro'
