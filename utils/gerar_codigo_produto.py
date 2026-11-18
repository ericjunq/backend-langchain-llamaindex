from uuid import uuid4

def gerar_codigo_produto() -> str:
    # Unicidade garantida pela constraint (empresa_id, codigo_produto) no banco.
    return "PROD-" + uuid4().hex[:8].upper()
