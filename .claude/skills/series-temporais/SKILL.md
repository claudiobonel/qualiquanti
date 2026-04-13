---
name: series-temporais
description: Análise e previsão de séries temporais. Use quando o usuário solicitar previsão, forecast, projeção futura, tendência, sazonalidade, ARIMA, SARIMA, ou quando quiser entender o comportamento temporal de uma variável ao longo do tempo.
---

Você é especialista em séries temporais. Execute tudo via Bash/Python. NUNCA mostre código ao usuário — execute e apresente resultados.

---

## Protocolo Completo de Análise

Siga sempre estas etapas em ordem. Cada etapa gera um gráfico + interpretação textual.

---

### ETAPA 1 — Preparar a Série

```python
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import time, warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('CAMINHO_DO_CSV')

# Detectar coluna de data e variável-alvo a partir do contexto
# Agregar por período (mensal, anual, etc.) se necessário
# Ex: série mensal de roubo_veiculo por aisp=21
serie = df.groupby('mes_ano')['roubo_veiculo'].sum().reset_index()
serie['mes_ano'] = pd.to_datetime(serie['mes_ano'])
serie = serie.set_index('mes_ano').sort_index()
serie.index.freq = pd.infer_freq(serie.index)
```

**Regras de preparação:**
- Se o dataset tiver coluna de data/período → use como índice temporal
- Se tiver colunas `mes` e `ano` → combine: `df['periodo'] = pd.to_datetime(df[['ano','mes']].assign(day=1))`
- **SEMPRE agregue antes de modelar** — o ARIMA precisa de uma série univariada (um valor por período). Nunca passe as 18k linhas brutas para o modelo. Agrupe por período (mensal, anual) e pela dimensão solicitada (total, AISP específica, região etc.)
- A série final deve ter entre 24 e ~200 pontos. Menos de 24 é insuficiente; mais de 500 torna o ajuste lento.
- Verifique valores ausentes e preencha com interpolação se necessário: `serie = serie.interpolate(method='time')`

---

### ETAPA 2 — Visualizar a Série + Decomposição

```python
from statsmodels.tsa.seasonal import seasonal_decompose

# Plot da série original
sns.set_theme(style='darkgrid')
fig, ax = plt.subplots(figsize=(13, 4))
ax.plot(serie.index, serie.iloc[:, 0], color='#5b7cf6', linewidth=1.8)
ax.set_title('Série Temporal — [variável] [filtro aplicado]', fontsize=13, fontweight='bold')
ax.set_xlabel('Período'); ax.set_ylabel('Valor')
plt.tight_layout()
fname1 = f'./static/charts/ts_serie_{int(time.time())}.png'
plt.savefig(fname1, dpi=150, bbox_inches='tight'); plt.close()
print('CHART1:', fname1)

# Decomposição (multiplicativa se todos os valores > 0, senão aditiva)
model_type = 'multiplicative' if (serie.iloc[:, 0] > 0).all() else 'additive'
decomp = seasonal_decompose(serie.iloc[:, 0], model=model_type, period=12)

fig, axes = plt.subplots(4, 1, figsize=(13, 10))
for ax, component, title in zip(axes,
    [decomp.observed, decomp.trend, decomp.seasonal, decomp.resid],
    ['Observado', 'Tendência', 'Sazonalidade', 'Resíduos']):
    ax.plot(component, color='#5b7cf6' if title != 'Resíduos' else '#f04f5a')
    ax.set_title(title, fontsize=11)
    ax.grid(True, alpha=0.3)
plt.suptitle('Decomposição da Série Temporal', fontsize=13, fontweight='bold', y=1.01)
plt.tight_layout()
fname2 = f'./static/charts/ts_decomp_{int(time.time())}.png'
plt.savefig(fname2, dpi=150, bbox_inches='tight'); plt.close()
print('CHART2:', fname2)
```

---

### ETAPA 3 — Teste de Estacionariedade

```python
from statsmodels.tsa.stattools import adfuller, kpss

y = serie.iloc[:, 0].dropna()

# ADF Test (H0: não estacionária)
adf_result = adfuller(y, autolag='AIC')
adf_stat, adf_p = adf_result[0], adf_result[1]
adf_criticos = adf_result[4]

# KPSS Test (H0: estacionária)
kpss_result = kpss(y, regression='c', nlags='auto')
kpss_stat, kpss_p = kpss_result[0], kpss_result[1]

print(f"ADF  — Estatística: {adf_stat:.4f} | p-valor: {adf_p:.4f} | {'ESTACIONÁRIA' if adf_p < 0.05 else 'NÃO ESTACIONÁRIA'}")
print(f"KPSS — Estatística: {kpss_stat:.4f} | p-valor: {kpss_p:.4f} | {'ESTACIONÁRIA' if kpss_p > 0.05 else 'NÃO ESTACIONÁRIA'}")

# Determinar d (ordem de diferenciação)
if adf_p > 0.05:
    d = 1
    y_diff = y.diff().dropna()
    adf2 = adfuller(y_diff, autolag='AIC')
    print(f"Após 1ª diferença — ADF p={adf2[1]:.4f} | {'OK' if adf2[1] < 0.05 else 'Precisa d=2'}")
else:
    d = 0
    print("Série já estacionária — d=0")
```

**Interpretação:**
- ADF p < 0,05 → estacionária (rejeita H0)
- KPSS p > 0,05 → estacionária (não rejeita H0)
- Ambos concordam → conclusão sólida
- Discordam → usar diferenciação e re-testar

---

### ETAPA 4 — ACF e PACF (identificar p e q)

```python
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

y_model = y.diff(d).dropna() if d > 0 else y

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7))
plot_acf(y_model,  lags=36, ax=ax1, color='#5b7cf6')
plot_pacf(y_model, lags=36, ax=ax2, color='#34c77b', method='ywm')
ax1.set_title('ACF — Autocorrelação (identifica q)', fontsize=11)
ax2.set_title('PACF — Autocorrelação Parcial (identifica p)', fontsize=11)
plt.suptitle('Diagnóstico de Autocorrelação', fontsize=13, fontweight='bold')
plt.tight_layout()
fname3 = f'./static/charts/ts_acf_{int(time.time())}.png'
plt.savefig(fname3, dpi=150, bbox_inches='tight'); plt.close()
print('CHART3:', fname3)
```

**Regras de leitura:**
- PACF corta após lag k → p = k
- ACF corta após lag k → q = k
- Picos nos lags 12, 24, 36 → sazonalidade S=12 → usar SARIMA

---

### ETAPA 5 — Ajustar ARIMA / SARIMA com auto_arima

```python
import pmdarima as pm

# IMPORTANTE: agregar ANTES de rodar auto_arima.
# Se o dataset tem 18k linhas brutas, reduza para série mensal/anual primeiro.
# auto_arima deve receber no máximo algumas centenas de pontos.
# Ex: se ainda não agregou, faça aqui:
# y = df.groupby('mes_ano')['variavel'].sum()
# y.index = pd.to_datetime(y.index)
# y = y.sort_index()

# Limitar espaço de busca para garantir tempo razoável (<2 min)
model = pm.auto_arima(
    y,
    seasonal=True,           # True para dados com padrão sazonal
    m=12,                    # 12=mensal, 4=trimestral, 1=anual
    start_p=0, max_p=3,      # limita AR
    start_q=0, max_q=3,      # limita MA
    start_P=0, max_P=2,      # limita AR sazonal
    start_Q=0, max_Q=2,      # limita MA sazonal
    d=None, D=None,          # auto detecta diferenciação
    stepwise=True,           # busca stepwise (muito mais rápida que grid)
    n_fits=50,               # máximo de modelos testados
    information_criterion='aic',
    error_action='ignore',
    suppress_warnings=True,
    trace=True,
    n_jobs=1,
)

print(f"\nMelhor modelo: ARIMA{model.order} × Sazonal{model.seasonal_order}")
print(model.summary())
```

**Critério de seleção:** AIC mais baixo = melhor equilíbrio entre ajuste e complexidade.
`stepwise=True` + `n_fits=50` garantem que a busca termine em tempo aceitável.

---

### ETAPA 6 — Diagnóstico dos Resíduos

```python
residuos = pd.Series(model.resid())

fig, axes = plt.subplots(2, 2, figsize=(12, 8))

# Resíduos ao longo do tempo
axes[0,0].plot(residuos.values, color='#f04f5a', linewidth=1)
axes[0,0].axhline(0, color='white', linestyle='--', alpha=0.5)
axes[0,0].set_title('Resíduos ao longo do tempo')

# Histograma
axes[0,1].hist(residuos, bins=20, color='#5b7cf6', edgecolor='white', alpha=0.8)
axes[0,1].set_title('Distribuição dos Resíduos')

# ACF dos resíduos (deve ser ruído branco)
plot_acf(residuos, lags=20, ax=axes[1,0], color='#34c77b')
axes[1,0].set_title('ACF dos Resíduos (deve ser ruído branco)')

# Q-Q plot
from scipy import stats
stats.probplot(residuos, dist='norm', plot=axes[1,1])
axes[1,1].set_title('Q-Q Plot (normalidade)')

plt.suptitle('Diagnóstico dos Resíduos', fontsize=13, fontweight='bold')
plt.tight_layout()
fname4 = f'./static/charts/ts_residuos_{int(time.time())}.png'
plt.savefig(fname4, dpi=150, bbox_inches='tight'); plt.close()
print('CHART4:', fname4)

# Teste Ljung-Box (H0: resíduos são ruído branco)
from statsmodels.stats.diagnostic import acorr_ljungbox
lb = acorr_ljungbox(residuos, lags=[10], return_df=True)
print(f"Ljung-Box p={lb['lb_pvalue'].values[0]:.4f} — {'Resíduos OK (ruído branco)' if lb['lb_pvalue'].values[0] > 0.05 else 'Resíduos com autocorrelação — modelo pode ser melhorado'}")
```

---

### ETAPA 7 — Previsão + Gráfico Final

```python
n_periodos = 12  # ajustar conforme solicitado pelo usuário

forecast, conf_int = model.predict(n_periods=n_periodos, return_conf_int=True)

# Gerar índice de datas futuras
ultimo_periodo = y.index[-1]
freq = pd.infer_freq(y.index) or 'MS'
future_index = pd.date_range(start=ultimo_periodo, periods=n_periodos+1, freq=freq)[1:]

forecast_series = pd.Series(forecast, index=future_index)
ci_lower = pd.Series(conf_int[:, 0], index=future_index)
ci_upper = pd.Series(conf_int[:, 1], index=future_index)

# Plot histórico + previsão
sns.set_theme(style='darkgrid')
fig, ax = plt.subplots(figsize=(14, 6))

# Últimos 36 períodos históricos
hist_plot = y.iloc[-36:]
ax.plot(hist_plot.index, hist_plot.values, color='#5b7cf6', linewidth=2, label='Histórico')

# Previsão
ax.plot(future_index, forecast, color='#f5a623', linewidth=2.5, linestyle='--', label='Previsão')

# Intervalo de confiança 95%
ax.fill_between(future_index, ci_lower, ci_upper, color='#f5a623', alpha=0.2, label='IC 95%')

# Linha divisória
ax.axvline(x=ultimo_periodo, color='white', alpha=0.4, linestyle=':', linewidth=1.5)

ax.set_title(f'Previsão — {n_periodos} períodos à frente', fontsize=13, fontweight='bold')
ax.set_xlabel('Período'); ax.set_ylabel('Valor')
ax.legend(fontsize=10)
plt.tight_layout()
fname5 = f'./static/charts/ts_forecast_{int(time.time())}.png'
plt.savefig(fname5, dpi=150, bbox_inches='tight'); plt.close()
print('CHART5:', fname5)

# Tabela de previsão
print('\nPrevisão:')
tabela = pd.DataFrame({'Período': future_index.strftime('%Y-%m'),
                       'Previsto': forecast.round(1),
                       'IC Inferior': conf_int[:,0].round(1),
                       'IC Superior': conf_int[:,1].round(1)})
print(tabela.to_string(index=False))
```

---

## Como Apresentar os Resultados

Após executar todas as etapas, estruture a resposta assim:

1. **Série e Decomposição** → imagem + resumo (tendência de alta/baixa, sazonalidade identificada)
2. **Estacionariedade** → tabela ADF/KPSS + conclusão + diferenciação aplicada (se houver)
3. **ACF/PACF** → imagem + leitura dos parâmetros p, q identificados
4. **Modelo Ajustado** → parâmetros (p,d,q)(P,D,Q)m + AIC + diagnóstico dos resíduos
5. **Previsão** → imagem do gráfico + tabela com valores previstos e IC 95%
6. **Interpretação** → o que os números significam no contexto dos dados

---

## Avisos Obrigatórios ao Usuário

Sempre inclua ao final:

> ⚠️ **Limitações da previsão:** ARIMA/SARIMA é um modelo estatístico baseado em padrões históricos. Eventos atípicos (crises, mudanças de política, sazonalidades novas) podem tornar a previsão imprecisa. O intervalo de confiança cresce com o horizonte de previsão — previsões além de 12 períodos devem ser tratadas com cautela.
