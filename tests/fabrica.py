"""Fábrica de dados fictícios para os testes (nada de dado pessoal real)."""
import itertools
from dataclasses import dataclass, field
from types import SimpleNamespace

SENHA = 'senha1234'
_seq = itertools.count(1)


def gerar_cpf() -> str:
    digitos = [int(c) for c in f'{100000000 + next(_seq):09d}']
    for peso_inicial in (10, 11):
        soma = sum(d * (peso_inicial - i) for i, d in enumerate(digitos))
        resto = (soma * 10) % 11
        digitos.append(0 if resto == 10 else resto)
    return ''.join(map(str, digitos))


def gerar_cnpj() -> str:
    digitos = [int(c) for c in f'{10000000 + next(_seq):08d}0001']
    for pesos in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
        resto = sum(d * p for d, p in zip(digitos, pesos)) % 11
        digitos.append(0 if resto < 2 else 11 - resto)
    return ''.join(map(str, digitos))


def gerar_telefone() -> str:
    return f'119{next(_seq):08d}'


@dataclass
class Conta:
    id: int
    email: str
    tokens: dict
    headers: dict = field(init=False)

    def __post_init__(self):
        self.headers = {'Authorization': f"Bearer {self.tokens['access_token']}"}


def dados_usuario(**extra) -> dict:
    n = next(_seq)
    return {
        'nome': f'Usuario{n}', 'sobrenome': 'Teste', 'email': f'usuario{n}@teste.com',
        'senha': SENHA, 'cpf': gerar_cpf(), 'telefone': gerar_telefone(), **extra,
    }


def login(client, email: str, senha: str = SENHA):
    return client.post('/auth/login', data={'username': email, 'password': senha})


def nova_conta(client, **extra) -> Conta:
    dados = dados_usuario(**extra)
    r = client.post('/usuarios', json=dados)
    assert r.status_code == 201, r.text
    r_login = login(client, dados['email'])
    assert r_login.status_code == 200, r_login.text
    return Conta(id=r.json()['id'], email=dados['email'], tokens=r_login.json())


def nova_empresa(client, headers) -> dict:
    r = client.post('/empresa', headers=headers, json={
        'nome': 'Loja Teste', 'cnpj': gerar_cnpj(),
        'email': f'loja{next(_seq)}@teste.com', 'telefone': gerar_telefone(),
    })
    assert r.status_code == 201, r.text
    return r.json()


def gerar_convite(client, headers) -> str:
    r = client.post('/empresa/convites', headers=headers)
    assert r.status_code == 201, r.text
    return r.json()['token']


def vincular(client, headers, token: str):
    return client.post('/convites/aceitar', headers=headers, json={'token': token})


def novo_produto(client, headers, **campos) -> dict:
    dados = {
        'nome': f'Produto {next(_seq)}', 'descricao': 'Descrição', 'quantidade': 10,
        'preco_compra': '10.00', 'preco_venda': '25.50', 'estoque_min': 2, **campos,
    }
    r = client.post('/produtos', headers=headers, json=dados)
    assert r.status_code == 201, r.text
    return r.json()


def novo_cliente(client, headers, **campos) -> dict:
    n = next(_seq)
    dados = {'nome': f'Cliente {n}', 'email': f'cliente{n}@teste.com',
             'cpf': gerar_cpf(), 'telefone': gerar_telefone(), **campos}
    r = client.post('/clientes', headers=headers, json=dados)
    assert r.status_code == 201, r.text
    return r.json()


def criar_venda(client, headers, itens, **campos):
    """itens: lista de (produto_id, quantidade). Devolve a resposta (não valida status)."""
    corpo = {
        'descricao': 'Venda teste', 'forma_pagamento': 'pix',
        'itens': [{'produto_id': p, 'quantidade': q} for p, q in itens], **campos,
    }
    return client.post('/vendas', headers=headers, json=corpo)


def estoque(client, headers, produto_id: int) -> int:
    return client.get(f'/produtos/{produto_id}', headers=headers).json()['quantidade']


def criar_loja(client) -> SimpleNamespace:
    """Cenário padrão: dono com empresa, um funcionário vinculado, um produto (10 un. a 25,50) e um cliente."""
    dono = nova_conta(client)
    empresa = nova_empresa(client, dono.headers)
    func = nova_conta(client)
    r = vincular(client, func.headers, gerar_convite(client, dono.headers))
    assert r.status_code == 200, r.text
    produto = novo_produto(client, dono.headers)
    cliente = novo_cliente(client, func.headers)
    return SimpleNamespace(dono=dono, func=func, empresa=empresa, produto=produto, cliente=cliente)
