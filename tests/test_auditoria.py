"""Trilha de auditoria: o que é registrado, como (LGPD) e quem consulta."""
from datetime import datetime, timedelta, timezone
from langchain_core.messages import AIMessage
from tests.fabrica import SENHA, criar_venda, gerar_convite, login, nova_conta, vincular
from tests.modelo_falso import chamar


def _eventos(client, conta, **filtros):
    r = client.get('/auditoria', headers=conta.headers, params=filtros)
    assert r.status_code == 200, r.text
    return r.json()


def _acoes(client, conta, **filtros):
    return [e['acao'] for e in _eventos(client, conta, **filtros)]


def test_ciclo_de_um_produto(client, loja):
    pid = loja.produto['id']
    h = loja.dono.headers
    client.patch(f'/produtos/{pid}', headers=h, json={'preco_venda': '30.00'})
    client.post(f'/produtos/{pid}/reposicao', headers=h, json={'quantidade': 5})
    client.delete(f'/produtos/{pid}', headers=h)

    eventos = _eventos(client, loja.dono, entidade='produto', entidade_id=pid)
    assert [e['acao'] for e in eventos] == ['produto.excluido', 'estoque.reposto', 'produto.editado', 'produto.criado']
    editado = eventos[2]
    assert editado['detalhes'] == {'campos': {'preco_venda': '30.00'}}
    assert editado['usuario_id'] == loja.dono.id and editado['origem'] == 'api' and editado['categoria'] == 'operacao'
    assert eventos[1]['detalhes'] == {'quantidade': 5, 'estoque_final': 15}


def test_vendas_e_cancelamento_com_motivo(client, loja):
    vid = criar_venda(client, loja.func.headers, [(loja.produto['id'], 2)]).json()['id']
    client.post(f'/vendas/{vid}/cancelar', headers=loja.func.headers, json={'motivo_cancelamento': 'Cliente desistiu'})
    cancelada, criada = _eventos(client, loja.dono, entidade='venda', entidade_id=vid)
    assert criada['acao'] == 'venda.criada' and criada['categoria'] == 'venda'
    assert criada['detalhes'] == {'valor_final': '51.00', 'itens': 1, 'forma_pagamento': 'pix'}
    assert cancelada['detalhes']['motivo'] == 'Cliente desistiu' and cancelada['usuario_id'] == loja.func.id


def test_lgpd_campos_pessoais_mascarados(client, loja):
    client.patch(f"/clientes/{loja.cliente['id']}", headers=loja.dono.headers,
                 json={'nome': 'Maria Nova', 'email': 'maria.nova@teste.com'})
    client.patch('/usuarios/me', headers=loja.dono.headers, json={'senha': 'outrasenha1', 'senha_atual': SENHA})

    cliente = _eventos(client, loja.dono, acao='cliente.editado')[0]
    usuario = _eventos(client, loja.dono, acao='usuario.editado')[0]
    assert cliente['detalhes'] == {'campos': {'nome': 'alterado', 'email': 'alterado'}}
    assert usuario['detalhes'] == {'campos': {'senha_hash': 'alterado'}}
    texto = str(_eventos(client, loja.dono))
    assert 'Maria Nova' not in texto and 'maria.nova' not in texto and 'outrasenha1' not in texto


def test_logins_e_exportacoes(client, loja, db):
    from models.auditoria_model import Auditoria
    login(client, loja.dono.email, 'errada')
    login(client, 'ninguem@teste.com', 'x')  # email inexistente: registra sem usuário
    client.get('/relatorios/vendas/exportar', headers=loja.dono.headers)
    client.get('/usuarios/me/dados', headers=loja.dono.headers)

    assert _acoes(client, loja.dono, categoria='acesso')[:3] == ['dados_pessoais.exportados', 'relatorio.exportado',
                                                                  'login.falhou']
    sem_usuario = db.query(Auditoria).filter(Auditoria.acao == 'login.falhou', Auditoria.usuario_id.is_(None)).one()
    assert sem_usuario.ip == 'testclient' and sem_usuario.detalhes is None  # o email digitado não é guardado
    assert all('ip' not in e for e in _eventos(client, loja.dono))  # IP não sai na API (mínima exposição)


def test_leituras_nao_geram_registro(client, loja, db):
    from models.auditoria_model import Auditoria
    antes = db.query(Auditoria).count()
    for url in ('/produtos', '/clientes', '/vendas', f"/produtos/{loja.produto['id']}", '/relatorios/vendas'):
        client.get(url, headers=loja.dono.headers)
    assert db.query(Auditoria).count() == antes


def test_operacao_que_falha_nao_deixa_registro(client, loja, db):
    from models.auditoria_model import Auditoria
    antes = db.query(Auditoria).count()
    assert criar_venda(client, loja.func.headers, [(loja.produto['id'], 999)]).status_code == 409
    assert db.query(Auditoria).count() == antes  # mesma transação: rollback leva o log junto


def test_acao_confirmada_pelo_chat_tem_origem_chat(client, loja, modelo):
    modelo(chamar('repor_estoque', produto=loja.produto['nome'], quantidade=3), AIMessage('ok'))
    acao_id = client.post('/chat', headers=loja.dono.headers, json={'mensagem': 'chegaram 3'}).json()['acoes_pendentes'][0]['id']
    client.post(f'/chat/acoes/{acao_id}/confirmar', headers=loja.dono.headers)
    [evento] = _eventos(client, loja.dono, acao='estoque.reposto')
    assert evento['origem'] == 'chat'
    assert _eventos(client, loja.dono, origem='chat') == [evento]


def test_equipe_e_convites(client, loja):
    colega = nova_conta(client)
    vincular(client, colega.headers, gerar_convite(client, loja.dono.headers))
    client.patch(f'/empresa/funcionarios/{colega.id}', headers=loja.dono.headers, json={'cargo': 'admin'})
    client.delete(f'/empresa/funcionarios/{colega.id}', headers=loja.dono.headers)
    acoes = _acoes(client, loja.dono, entidade='usuario', entidade_id=colega.id)
    assert acoes == ['funcionario.removido', 'funcionario.cargo_alterado']
    cargo = _eventos(client, loja.dono, acao='funcionario.cargo_alterado')[0]
    assert cargo['detalhes'] == {'de': 'funcionario', 'para': 'admin'}
    assert _acoes(client, loja.dono, acao='convite.aceito')  # o aceite também aparece para a empresa


def test_so_o_dono_consulta_e_so_a_propria_empresa(client, loja, outra_loja):
    assert client.get('/auditoria', headers=loja.func.headers).status_code == 403
    admin = nova_conta(client)
    vincular(client, admin.headers, gerar_convite(client, loja.dono.headers))
    client.patch(f'/empresa/funcionarios/{admin.id}', headers=loja.dono.headers, json={'cargo': 'admin'})
    assert client.get('/auditoria', headers=admin.headers).status_code == 403

    ids_loja = {e['id'] for e in _eventos(client, loja.dono)}
    ids_outra = {e['id'] for e in _eventos(client, outra_loja.dono)}
    assert ids_loja and ids_outra and not ids_loja & ids_outra


def test_retencao_da_auditoria(client, loja, db):
    from main import limpar_dados_expirados
    from models.auditoria_model import Auditoria
    agora = datetime.now(timezone.utc)
    criar_venda(client, loja.func.headers, [(loja.produto['id'], 1)])

    def envelhecer(acao, dias):
        db.query(Auditoria).filter(Auditoria.acao == acao).update(
            {'created_at': agora - timedelta(days=dias)}, synchronize_session=False)

    envelhecer('login', 400)           # acesso com mais de 1 ano → sai
    envelhecer('venda.criada', 400)    # venda com 400 dias → fica (5 anos)
    envelhecer('produto.criado', 1900) # operação com mais de 5 anos → sai
    db.commit()

    limpar_dados_expirados()

    db.expire_all()
    restantes = {a for (a,) in db.query(Auditoria.acao)}
    assert 'login' not in restantes and 'produto.criado' not in restantes
    assert 'venda.criada' in restantes and 'cliente.criado' in restantes
