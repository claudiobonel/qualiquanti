# QualiQuanti Bot 🤖📊

> **Versão Beta** — Converse com seus dados em português, sem escrever uma linha de código.
>
> Desenvolvido com [Claude Code](https://claude.ai/code) e o padrão **Skills CLI** da Anthropic.

---

## O que é?

O **QualiQuanti Bot** é uma solução **open source** que permite a qualquer pessoa — analista, gestor, pesquisador ou estudante — fazer perguntas em linguagem natural sobre suas planilhas e receber respostas com análises, gráficos e previsões geradas por inteligência artificial.

Você carrega um arquivo `.xlsx`, `.xls` ou `.csv`, faz sua pergunta e o bot cuida do resto.

---

## Skills disponíveis

O bot conta com três módulos de análise especializados, ativados automaticamente conforme a sua solicitação:

### 📋 Análise Exploratória de Dados
- Qualidade dos dados (nulos, duplicatas, inconsistências)
- Estatísticas descritivas (média, mediana, desvio padrão, percentis)
- Rankings e agrupamentos por qualquer variável
- Correlações e padrões entre variáveis
- Detecção de outliers e anomalias
- Insights e recomendações acionáveis

### 📈 Visualização de Dados
- Geração automática de gráficos (barras, linhas, dispersão, histograma, boxplot)
- Seleção inteligente do tipo de gráfico conforme o dado
- Gráficos prontos para apresentação, com título e rótulos

### 🔮 Séries Temporais (ARIMA / SARIMA)
- Decomposição de tendência e sazonalidade
- Testes de estacionariedade (ADF e KPSS)
- Diagnóstico de autocorrelação (ACF / PACF)
- Ajuste automático de modelo com `auto_arima`
- Previsão com intervalo de confiança de 95%
- Aviso de limitações e caveats estatísticos

---

## ⚠️ Atenção: Formato dos Dados

Para obter os melhores resultados, **os dados devem estar tabulados e organizados**:

- ✅ Uma linha = um registro
- ✅ Uma coluna = uma variável
- ✅ Cabeçalho na primeira linha, sem células mescladas
- ✅ Datas em formato consistente (ex: `2024-01`, `01/2024`, `2024`)
- ❌ Evite subtotais, células coloridas com significado, ou tabelas dinâmicas exportadas sem limpeza

> Esta versão beta não realiza limpeza automática de dados mal formatados. Quanto mais limpo o arquivo, melhor a análise.

---

## Executando localmente

### Pré-requisitos

- Python 3.10 ou superior
- [Claude Code CLI](https://docs.anthropic.com/claude-code) instalado e autenticado
- Git (opcional, para clonar o repositório)

### Passo a passo

**1. Clone o repositório**
```bash
git clone https://github.com/SEU_USUARIO/qualiquanti-bot.git
cd qualiquanti-bot
```

**2. Crie e ative um ambiente virtual**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

**3. Instale as dependências**
```bash
pip install -r requirements.txt
```

**4. Verifique se o Claude Code CLI está funcionando**
```bash
claude --version
```
> Caso não tenha o Claude Code instalado, siga as instruções em: https://docs.anthropic.com/claude-code

**5. Inicie o servidor**
```bash
python app.py
```

**6. Acesse no navegador**
```
http://127.0.0.1:5000
```

---

## Estrutura do projeto

```
qualiquanti-bot/
├── app.py                          ← Backend Flask
├── requirements.txt                ← Dependências Python
├── CLAUDE.md                       ← Persona e protocolo de análise
├── templates/
│   └── index.html                  ← Interface web
├── static/
│   └── charts/                     ← Gráficos gerados (auto)
├── uploads/                        ← Arquivos enviados (auto, não versionado)
├── history/                        ← Histórico de conversas (auto, não versionado)
└── .claude/
    └── skills/
        ├── analista-dados/SKILL.md ← Skill de análise exploratória
        ├── visualizacao/SKILL.md   ← Skill de gráficos
        └── series-temporais/SKILL.md ← Skill de ARIMA/SARIMA
```

---

## Variáveis de ambiente (opcionais)

| Variável | Padrão | Descrição |
|---|---|---|
| `FLASK_HOST` | `127.0.0.1` | Host do servidor |
| `FLASK_PORT` | `5000` | Porta do servidor |
| `FLASK_DEBUG` | `false` | Modo debug do Flask |
| `CLAUDE_CMD` | `claude` | Comando do Claude Code CLI |
| `CLAUDE_TIMEOUT` | `600` | Timeout em segundos por requisição |
| `MAX_FULL_CSV_BYTES` | `400000` | Limite para enviar CSV completo ao modelo |

---

## Tecnologias utilizadas

- **Backend:** Python + Flask
- **IA:** Claude (Anthropic) via Claude Code CLI
- **Análise de dados:** pandas, numpy, scipy
- **Visualização:** matplotlib, seaborn
- **Séries temporais:** statsmodels, pmdarima
- **Frontend:** HTML + CSS + JavaScript puro

---

## Limitações da versão beta

- Dados precisam estar tabulados e limpos antes do upload
- Análises de séries temporais exigem no mínimo 24 períodos
- Arquivos muito grandes (>10MB) podem aumentar o tempo de resposta
- Uma sessão por vez por instância do servidor

---

## Contribuições

Contribuições são bem-vindas! Abra uma *issue* ou envie um *pull request*.

---

## Contato

Dúvidas, sugestões ou parcerias:

📧 **contato@profclaudiobonel.com.br**

---

## Licença

MIT License — livre para usar, modificar e distribuir.
