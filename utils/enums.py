from enum import Enum

class CargosEnum(str, Enum):
    dono = 'dono'
    admin = 'admin'
    funcionario = 'funcionario'

class CargosFuncionarios(str, Enum):
    admin = 'admin'
    funcionario = 'funcionario'

class DataFilter(str, Enum):
    mes = "mes"
    semestre = "semestre"
    ano = "ano"
