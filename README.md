# QualiQuanti Bot

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.x-000000?style=flat&logo=flask&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?style=flat&logo=javascript&logoColor=black)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat&logo=css3&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?style=flat&logo=pandas&logoColor=white)
![Claude](https://img.shields.io/badge/Claude_Code-Anthropic-D97757?style=flat)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)
![Version](https://img.shields.io/badge/version-v1.0.2-blue?style=flat)

> **Versão Beta** — Converse com seus dados em português, sem escrever uma linha de código.
>
> Desenvolvido com [Claude Code](https://claude.ai/code) e o padrão **Skills CLI** da Anthropic.

---

## O que é?

O **QualiQuanti Bot** é uma solução open source que permite a qualquer pessoa — analista, gestor, pesquisador ou estudante — fazer perguntas em linguagem natural sobre suas planilhas e receber respostas com análises, gráficos e previsões geradas por inteligência artificial.

Você carrega um arquivo `.xlsx`, faz sua pergunta e o bot cuida do resto.

---

## Como funciona

```
Usuário (navegador)
       │
       ▼
  Flask (app.py)          ← backend Python
       │  monta prompt com dados + histórico
       ▼
  Claude Code CLI          ← IA da Anthropic
       │  executa análise via Skills
       ▼
  Resposta (markdown)     → renderizada no browser
```

1. Você faz upload de uma planilha
2. O backend converte para CSV e extrai os metadados (colunas, tipos, nulos, min/max)
3. A cada pergunta, o servidor monta um prompt com: metadados + dados + histórico + sua pergunta
4. O **Claude Code CLI** recebe esse prompt, decide qual *skill* ativar e executa a análise
5. A resposta chega em tempo real no browser via streaming

---

## Skills disponíveis

O bot conta com três módulos de análise especializados, ativados automaticamente:

### Análise Exploratória de Dados
- Qualidade dos dados (nulos, duplicatas, inconsistências)
- Estatísticas descritivas (média, mediana, desvio padrão, percentis)
- Rankings e agrupamentos por qualquer variável
- Correlações e padrões entre variáveis
- Detecção de outliers e anomalias
- Insights e recomendações acionáveis

### Visualização de Dados
- Geração automática de gráficos (barras, linhas, dispersão, histograma, boxplot)
- Seleção inteligente do tipo de gráfico conforme o dado
- Gráficos prontos para apresentação, com título e rótulos

### Séries Temporais (ARIMA / SARIMA)
- Decomposição de tendência e sazonalidade
- Testes de estacionariedade (ADF e KPSS)
- Diagnóstico de autocorrelação (ACF / PACF)
- Ajuste automático de modelo com `auto_arima`
- Previsão com intervalo de confiança de 95%
- Aviso de limitações e caveats estatísticos

---

## Pré-requisitos

Antes de instalar o projeto, você precisa ter instalado na sua máquina:

| Ferramenta | Versão mínima | Para que serve |
|---|---|---|
| Python | 3.10+ | Rodar o backend Flask |
| Node.js | 18+ | Necessário para o Claude Code CLI |
| npm | 9+ | Instalado junto com o Node.js |
| Git | qualquer | Clonar o repositório |

> Apenas arquivos `.xlsx` são aceitos para upload.

Você também precisa de uma conta na Anthropic com acesso ao Claude Code CLI (veja o Passo 3 abaixo).

---

## Instalação passo a passo

### Passo 1 — Instalar Python 3.10+

**Windows:**
- Baixe em [python.org/downloads](https://www.python.org/downloads/)
- Durante a instalação, **marque a opção "Add Python to PATH"**
- Verifique: `python --version`

**macOS:**
```bash
brew install python@3.12
python3 --version
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install python3 python3-pip python3-venv
python3 --version
```

---

### Passo 2 — Instalar Node.js 18+

O Claude Code CLI é instalado via npm e requer o Node.js.

**Windows / macOS:**
- Baixe o instalador LTS em [nodejs.org](https://nodejs.org/)
- Verifique: `node --version` e `npm --version`

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
node --version
```

---

### Passo 3 — Instalar e autenticar o Claude Code CLI

O Claude Code CLI é a ferramenta da Anthropic que executa toda a inteligência do bot.

**Instale globalmente via npm:**
```bash
npm install -g @anthropic-ai/claude-code
```

**Verifique a instalação:**
```bash
claude --version
```

**Autentique com sua conta Anthropic:**
```bash
claude
```

Na primeira execução, o CLI abre o fluxo de autenticação no navegador. Você pode autenticar de duas formas:

- **Claude.ai Pro/Max** — faça login com sua conta Claude.ai (recomendado para uso pessoal)
- **Chave de API Anthropic** — se preferir usar a API diretamente, obtenha sua chave em [console.anthropic.com](https://console.anthropic.com/) e configure:
  ```bash
  export ANTHROPIC_API_KEY="sua-chave-aqui"
  ```

> Sem autenticação válida, o bot não consegue processar nenhuma pergunta.

---

### Passo 4 — Clonar o repositório

```bash
git clone https://github.com/SEU_USUARIO/qualiquanti-bot.git
cd qualiquanti-bot
```

Ou baixe o ZIP pelo GitHub e extraia em uma pasta de sua escolha.

---

### Passo 5 — Criar ambiente virtual Python

Um ambiente virtual isola as dependências do projeto para não conflitar com outros projetos Python.

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

Após ativar, o prompt do terminal deve exibir `(venv)` no início.

---

### Passo 6 — Instalar as dependências Python

Com o ambiente virtual ativo:
```bash
pip install -r requirements.txt
```

Isso instala:
- `flask` — servidor web
- `pandas` — manipulação de dados
- `openpyxl` — leitura de arquivos `.xlsx`
- `xlrd` — leitura de arquivos `.xls` legados
- `matplotlib` e `seaborn` — geração de gráficos
- `statsmodels` — análise de séries temporais
- `pmdarima` — seleção automática de modelo ARIMA
- `scipy` — testes estatísticos

> A instalação do `pmdarima` pode demorar alguns minutos pois compila extensões nativas.

---

### Passo 7 — Iniciar o servidor

```bash
python app.py
```

Você verá uma saída parecida com:
```
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

---

### Passo 8 — Acessar o aplicativo

Abra o navegador e acesse:
```
http://127.0.0.1:5000
```

Pronto! O bot está funcionando.

---

## Como usar

1. **Criar uma nova conversa** — clique em "Nova conversa" na barra lateral
2. **Carregar um arquivo** — arraste e solte ou clique na área de upload; formato aceito: `.xlsx`
3. **Fazer perguntas** — escreva sua pergunta em português no campo de texto e pressione Enter ou clique em Enviar
4. **Navegar no histórico** — conversas anteriores ficam salvas na barra lateral e podem ser retomadas a qualquer momento

**Exemplos de perguntas:**
- "Quais são os 10 produtos mais vendidos?"
- "Existe correlação entre preço e quantidade vendida?"
- "Faça um gráfico de barras com as vendas por região"
- "Preveja as vendas dos próximos 6 meses"
- "Quantos registros têm valores nulos na coluna cliente?"

---

## Formato dos dados

Para melhores resultados, os dados devem estar organizados como uma tabela simples:

- ✅ Arquivo no formato `.xlsx` (Excel)
- ✅ Uma linha = um registro
- ✅ Uma coluna = uma variável
- ✅ Cabeçalho na primeira linha, sem células mescladas
- ✅ Datas em formato consistente (ex: `2024-01`, `01/2024`, `2024`)
- ❌ Evite subtotais, células coloridas com significado ou tabelas dinâmicas exportadas sem limpeza

> Esta versão beta não realiza limpeza automática. Quanto mais limpo o arquivo, melhor a análise.

---

## Estrutura do projeto

```
qualiquanti-bot/
├── app.py                            ← Backend Flask (servidor e integração com Claude)
├── requirements.txt                  ← Dependências Python
├── CLAUDE.md                         ← Persona e protocolo do bot (lido pelo Claude)
├── templates/
│   └── index.html                    ← Interface web (HTML + CSS + JS)
├── static/
│   └── charts/                       ← Gráficos gerados (criado automaticamente)
├── uploads/                          ← Arquivos enviados convertidos em CSV (criado automaticamente)
├── history/                          ← Histórico de conversas em JSON (criado automaticamente)
└── .claude/
    └── skills/
        ├── analista-dados/SKILL.md   ← Instruções para análise exploratória
        ├── visualizacao/SKILL.md     ← Instruções para geração de gráficos
        └── series-temporais/SKILL.md ← Instruções para previsão ARIMA/SARIMA
```

> As pastas `uploads/`, `history/` e `static/charts/` são criadas automaticamente ao iniciar o servidor.

---

## Variáveis de ambiente (opcionais)

Você pode personalizar o comportamento do servidor criando um arquivo `.env` ou exportando variáveis antes de iniciar:

| Variável | Padrão | Descrição |
|---|---|---|
| `FLASK_HOST` | `127.0.0.1` | Host do servidor (use `0.0.0.0` para acesso na rede local) |
| `FLASK_PORT` | `5000` | Porta do servidor |
| `FLASK_DEBUG` | `false` | Modo debug do Flask (não use em produção) |
| `CLAUDE_CMD` | `claude` | Comando para invocar o Claude Code CLI |
| `CLAUDE_TIMEOUT` | `600` | Tempo limite em segundos por análise |
| `MAX_FULL_CSV_BYTES` | `400000` | Tamanho máximo para enviar o CSV completo ao modelo (~400KB) |

**Exemplo de uso:**
```bash
# Windows (PowerShell)
$env:FLASK_PORT = "8080"
python app.py

# macOS / Linux
FLASK_PORT=8080 python app.py
```

---

## Solução de problemas

### `claude: command not found`
O Claude Code CLI não está no PATH. Verifique se o npm instalou corretamente:
```bash
npm list -g @anthropic-ai/claude-code
```
Se instalado mas não encontrado, adicione o diretório global do npm ao seu PATH.

### `claude --version` funciona mas o bot retorna erro de autenticação
Execute `claude` no terminal e siga o fluxo de login novamente. O token pode ter expirado.

### Erro ao instalar `pmdarima` no Windows
Instale primeiro as ferramentas de build do C++:
```bash
pip install wheel
pip install pmdarima --no-binary pmdarima
```
Se persistir, instale o [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).

### Erro ao instalar `pmdarima` no macOS
```bash
brew install gcc
pip install pmdarima
```

### Gráficos não aparecem após a resposta
Verifique se a pasta `static/charts/` existe e tem permissão de escrita. O Flask deve ser reiniciado a partir da raiz do projeto.

### O servidor inicia mas o browser exibe "Connection refused"
Certifique-se de acessar exatamente `http://127.0.0.1:5000` (não `https`). Verifique se nenhum outro processo usa a porta 5000 (`lsof -i :5000` no Mac/Linux ou `netstat -ano | findstr :5000` no Windows).

### Análise demora mais de 10 minutos e trava
O timeout padrão é 600 segundos. Para arquivos muito grandes, aumente:
```bash
CLAUDE_TIMEOUT=1200 python app.py
```

---

## Tecnologias utilizadas

- **Backend:** Python 3.10+ + Flask
- **IA:** Claude (Anthropic) via Claude Code CLI
- **Análise de dados:** pandas, numpy, scipy
- **Visualização:** matplotlib, seaborn
- **Séries temporais:** statsmodels, pmdarima
- **Frontend:** HTML5 + CSS3 + JavaScript puro (sem frameworks)
- **Comunicação em tempo real:** Server-Sent Events (SSE)

---

## Limitações da versão beta

- Dados precisam estar tabulados e limpos antes do upload
- Análises de séries temporais exigem no mínimo 24 períodos
- Arquivos maiores que ~400KB são enviados apenas com amostra (500 linhas) + estatísticas
- Uma sessão por vez por instância do servidor
- Gráficos ficam salvos localmente e não são excluídos automaticamente

---

## Contribuições

Contribuições são bem-vindas! Abra uma *issue* ou envie um *pull request*.

---

## Contato

Dúvidas, sugestões ou parcerias:

**contato@profclaudiobonel.com.br**

---

## Licença

MIT License — livre para usar, modificar e distribuir.
