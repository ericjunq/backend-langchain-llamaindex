"""python -m migracoes  → aplica as pendentes e mostra o estado de cada migração."""
from database import engine
from migracoes import aplicar, estado

aplicadas = aplicar(engine)
print('Aplicadas agora:', ', '.join(aplicadas) if aplicadas else 'nenhuma (banco em dia)')
for nome, ok in estado(engine):
    print(f"  [{'x' if ok else ' '}] {nome}")
