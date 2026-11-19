import os
import httpx
import pytest
from langchain_core.messages import AIMessage
from services.chat_service import MENSAGEM_LIMITE_PASSOS
from tests.fabrica import criar_venda, nova_conta
from tests.modelo_falso import chamar


def _chat(client, conta, mensagem='oi', **extra):
    return client.post('/chat', headers=conta.headers, json={'mensagem': mensagem, **extra})


def test_resposta_direta_com_historico(client, loja, modelo):
    m = modelo(AIMessage('<think>pensando…</think>Olá! Como posso ajudar?'))
    r = _chat(client, loja.dono, historico=[{'papel': 'usuario', 'conteudo': 'bom dia'},
                                           {'papel': 'assistente', 'conteudo': 'bom dia!'}])
    assert r.status_code == 200
    assert r.json() == {'resposta': 'Olá! Como posso ajudar?', 'ferramentas_usadas': [], 'acoes_pendentes': []}
    sistema, *resto = m.chamadas[0]
    assert loja.empresa['nome'] in sistema.content and 'dono' in sistema.content
    assert [x.content for x in resto] == ['bom dia', 'bom dia!', 'oi']


def test_historico_limitado_a_10(client, loja, modelo):
    modelo(AIMessage('ok'))
    historico = [{'papel': 'usuario', 'conteudo': 'x'}] * 11
    assert _chat(client, loja.dono, historico=historico).status_code == 422


def test_buscar_produtos_devolve_json_compacto(client, loja, modelo):
    m = modelo(chamar('buscar_produtos', nome=loja.produto['nome']), AIMessage('Tem 10 em estoque.'))
    r = _chat(client, loja.func, 'quanto tem do produto?')
    assert r.json()['ferramentas_usadas'] == ['buscar_produtos']
    [saida] = m.saidas_ferramentas()
    assert saida == [{'produto': loja.produto['nome'], 'codigo': loja.produto['codigo_produto'],
                      'estoque': 10, 'estoque_min': 2, 'preco_venda': 25.5}]


def test_reposicao_por_necessidade_e_gasto_estimado(client, loja, modelo):
    m = modelo(chamar('sugerir_reposicao'), AIMessage('ok'))
    _chat(client, loja.dono, 'o que preciso comprar?')
    [saida] = m.saidas_ferramentas()
    assert set(saida['por_necessidade']) == {'comprar_agora', 'em_breve', 'ok'}
    assert 'gasto_estimado_reposicao' in saida and 'ESTIMADO' in saida['obs']


def test_lgpd_ferramentas_nao_expoem_dados_pessoais(client, loja, modelo, db):
    from models.cliente_model import Clientes
    cliente = db.get(Clientes, loja.cliente['id'])
    cliente.nome = 'Maria Souza Lima'
    db.commit()
    criar_venda(client, loja.func.headers, [(loja.produto['id'], 1)], cliente_id=cliente.id)

    m = modelo(chamar('ultimas_vendas'), chamar('buscar_clientes', nome='maria'), AIMessage('ok'))
    _chat(client, loja.dono, 'últimas vendas')

    texto = str(m.saidas_ferramentas())
    for dado in (cliente.cpf, cliente.email, cliente.telefone, 'Souza Lima'):
        assert dado not in texto
    assert 'Maria S.' in texto


def test_permissoes_valem_no_chat(client, loja, modelo):
    m = modelo(chamar('sugerir_reposicao'), chamar('resumo_vendas', periodo='mes'), AIMessage('Sem permissão.'))
    r = _chat(client, loja.func, 'o que comprar e quanto vendemos?')
    assert r.status_code == 200
    assert all('erro' in s for s in m.saidas_ferramentas())


def test_isolamento_entre_empresas_no_chat(client, loja, outra_loja, modelo):
    m = modelo(chamar('prever_demanda', produto=loja.produto['nome']), AIMessage('Não encontrei.'))
    _chat(client, outra_loja.dono, 'previsão do produto')
    assert m.saidas_ferramentas() == [{'erro': f'Produto "{loja.produto["nome"]}" não encontrado'}]


def test_argumentos_invalidos_e_ferramenta_inexistente(client, loja, modelo):
    m = modelo(chamar('prever_demanda'), chamar('apagar_tudo'), AIMessage('ok'))
    r = _chat(client, loja.dono)
    assert r.status_code == 200
    saidas = m.saidas_ferramentas()
    assert 'erro' in saidas[0] and saidas[1] == {'erro': 'ferramenta inexistente'}


def test_limite_de_passos(client, loja, modelo):
    modelo(*[chamar('buscar_produtos') for _ in range(20)])
    r = _chat(client, loja.dono)
    assert r.json()['resposta'] == MENSAGEM_LIMITE_PASSOS
    assert len(r.json()['ferramentas_usadas']) == 5


def test_ollama_fora_do_ar(client, loja, modelo):
    modelo(httpx.ConnectError('recusado'))
    r = _chat(client, loja.dono)
    assert r.status_code == 503 and r.json()['detail'] == 'Assistente indisponível no momento'


def test_usuario_sem_empresa(client, modelo):
    modelo(AIMessage('ok'))
    assert _chat(client, nova_conta(client)).status_code == 403


@pytest.mark.skipif(os.environ.get('OLLAMA_TESTE') != '1', reason='defina OLLAMA_TESTE=1 para usar o Ollama real')
def test_integracao_ollama_real(client, loja):
    import time
    from tests.fabrica import novo_produto
    novo_produto(client, loja.dono.headers, nome='Filtro de papel', quantidade=1, estoque_min=5)

    def perguntar(conta, pergunta):
        inicio = time.perf_counter()
        r = _chat(client, conta, pergunta)
        assert r.status_code == 200, r.text
        corpo = r.json()
        print(f'\n[{time.perf_counter() - inicio:.1f}s] {pergunta}\n  ferramentas: {corpo["ferramentas_usadas"]}'
              f'\n  resposta: {corpo["resposta"]}\n  ações: {[a["resumo"] for a in corpo["acoes_pendentes"]]}')
        return corpo

    corpo = perguntar(loja.dono, 'Quais produtos estão abaixo do estoque mínimo?')
    assert corpo['ferramentas_usadas'] and 'Filtro' in corpo['resposta']

    corpo = perguntar(loja.dono, 'O que eu preciso comprar?')
    assert corpo['ferramentas_usadas'] and 'Filtro' in corpo['resposta']
    assert '4 unidades' in corpo['resposta'] or 'comprar 4' in corpo['resposta'].lower()  # leu o campo certo
    assert 'Confirmar' not in corpo['resposta'] and corpo['acoes_pendentes'] == []  # consulta não gera ação

    # Escrita: o modelo deve só PREPARAR a venda (nada muda até o usuário confirmar).
    from tests.fabrica import estoque
    corpo = perguntar(loja.func, f"Registra uma venda de 2 {loja.produto['nome']} no pix, sem cliente.")
    [acao] = corpo['acoes_pendentes']
    assert acao['resumo'].startswith(f"Venda: 2× {loja.produto['nome']}")
    assert estoque(client, loja.dono.headers, loja.produto['id']) == 10

    # Cancelamento sem motivo: o modelo deve PERGUNTAR o motivo, sem preparar nada.
    from tests.fabrica import criar_venda
    vid = criar_venda(client, loja.func.headers, [(loja.produto['id'], 1)]).json()['id']
    corpo = perguntar(loja.func, f'Cancela a venda {vid}.')
    assert corpo['acoes_pendentes'] == [] and 'motivo' in corpo['resposta'].lower()
    corpo = perguntar(loja.func, f'Cancela a venda {vid}, o cliente desistiu da compra.')
    [acao] = corpo['acoes_pendentes']
    assert acao['resumo'].startswith(f'Cancelar venda #{vid}')
