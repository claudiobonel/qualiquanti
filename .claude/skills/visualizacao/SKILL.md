---
name: visualizacao
description: Gera gráficos e visualizações de dados. Use quando o usuário solicitar gráfico, chart, plot, figura ou visualização — ou quando dados comparativos, rankings, tendências temporais, distribuições ou correlações forem melhor comunicados visualmente do que em texto/tabela.
---

Quando gerar um gráfico, siga este protocolo exato:

1. **Execute Python** com matplotlib/seaborn via ferramenta Bash
2. **Salve** em `./static/charts/` com nome único baseado em timestamp
3. **Exiba no chat** com markdown: `![descrição](/static/charts/nome.png)`

NUNCA mostre o código Python ao usuário. NUNCA peça aprovação. Execute e exiba o resultado.

---

## Escolha do Tipo de Gráfico

| Situação | Tipo |
|---|---|
| Ranking / comparar categorias | Barras horizontais (`barh`) |
| Evolução ao longo do tempo | Linha (`plot`) |
| Distribuição de uma variável numérica | Histograma ou Boxplot |
| Correlação entre duas variáveis | Scatter plot |
| Composição / proporção (≤5 categorias) | Barras empilhadas |
| Múltiplas métricas por grupo | Barras agrupadas |

Evite gráfico de pizza para mais de 5 categorias. Prefira barras horizontais quando os rótulos são longos.

---

## Template de Código

```python
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # OBRIGATÓRIO: sem display
import matplotlib.pyplot as plt
import seaborn as sns
import time

# ── Carregar e processar dados ──────────────────
df = pd.read_csv('CAMINHO_DO_CSV')
# ... agrupamentos, filtros, ordenações ...

# ── Estilo ──────────────────────────────────────
sns.set_theme(style='darkgrid')
fig, ax = plt.subplots(figsize=(12, 7))

# ── Plot ────────────────────────────────────────
# ... código do gráfico ...

# ── Rótulos e título ────────────────────────────
ax.set_title('Título do Gráfico', fontsize=14, fontweight='bold', pad=16)
ax.set_xlabel('Eixo X', fontsize=11)
ax.set_ylabel('Eixo Y', fontsize=11)
plt.tight_layout()

# ── Salvar ──────────────────────────────────────
fname = f'./static/charts/chart_{int(time.time())}.png'
plt.savefig(fname, dpi=150, bbox_inches='tight')
plt.close()
print(fname)
```

---

## Boas Práticas

- **Dados grandes**: agrupe antes de plotar (máx. ~30 barras legíveis)
- **Valores nas barras**: use `ax.bar_label()` para exibir valores diretamente
- **Cores**: use a paleta `"deep"` do seaborn por padrão; destaque o maior valor com cor diferente se for ranking
- **Tamanho**: `figsize=(12, 7)` para gráficos de barra; `(10, 6)` para linha/scatter
- **Legibilidade**: rotacione labels do eixo X com `plt.xticks(rotation=45, ha='right')` se necessário
- **Filtros**: aplique qualquer filtro temporal ou categórico solicitado ANTES de plotar

---

## Após Salvar

Inclua na resposta o caminho retornado pelo print como imagem markdown:

```
![Título descritivo](/static/charts/chart_1234567890.png)
```

Seguido de uma breve interpretação do que o gráfico mostra.
