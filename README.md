# 🛒 Worten Outlet Scraper

Monitoriza automaticamente a página de portáteis outlet da Worten e envia alertas via Telegram quando aparecem novos produtos.

Corre na cloud (GitHub Actions) de graça, 24/7.

## Setup (10 minutos)

### 1. Criar bot Telegram

1. Abre o Telegram e procura **@BotFather**
2. Envia `/newbot`
3. Dá um nome (ex: "Worten Alertas") e um username (ex: "worten_outlet_bot")
4. Guarda o **token** que recebes (parece: `7123456789:AAH...`)
5. Procura **@userinfobot** e envia `/start` → guarda o teu **chat_id**

### 2. Criar repositório no GitHub

1. Vai a [github.com/new](https://github.com/new)
2. Nome: `worten-scraper` (pode ser privado)
3. Cria o repositório

### 3. Adicionar os secrets

1. No repositório, vai a **Settings → Secrets and variables → Actions**
2. Clica **New repository secret** e adiciona:
   - Nome: `TELEGRAM_TOKEN` → Valor: o token do passo 1
   - Nome: `TELEGRAM_CHAT_ID` → Valor: o chat_id do passo 1

### 4. Upload dos ficheiros

Faz upload destes ficheiros para o repositório:

```
worten-scraper/
├── .github/
│   └── workflows/
│       └── scrape.yml        ← GitHub Actions workflow
├── scraper.py                ← Script principal
├── seen_products.json        ← Histórico (começa vazio)
└── README.md
```

**Via terminal (se tiveres Git):**
```bash
git clone https://github.com/TEU_USERNAME/worten-scraper.git
cd worten-scraper
# copia os ficheiros para cá
git add .
git commit -m "Initial setup"
git push
```

**Ou via browser:**
Upload direto no GitHub (Add file → Upload files)

### 5. Ativar o workflow

1. Vai ao separador **Actions** no repositório
2. Se aparecer "I understand my workflows, go ahead and enable them", clica
3. Clica em "Worten Outlet Scraper" → "Run workflow" para testar

## ✅ Pronto!

O scraper corre automaticamente a cada 10 minutos. Recebes uma mensagem no Telegram sempre que aparecer um novo portátil com ≥24GB de RAM.

## Configuração extra

### Alterar filtros

No ficheiro `.github/workflows/scrape.yml`, ajusta:

```yaml
env:
  MIN_RAM_GB: '24'    # RAM mínima (0 = sem filtro)
  MAX_PRICE: '800'    # Preço máximo em € (0 = sem filtro)
```

### Alterar frequência

No mesmo ficheiro, ajusta o cron:

```yaml
schedule:
  - cron: '*/10 * * * *'   # Cada 10 min
  - cron: '*/5 * * * *'    # Cada 5 min (usa mais minutos do plano)
  - cron: '*/30 * * * *'   # Cada 30 min (mais conservador)
```

### Limites GitHub Actions (plano gratuito)

- **Repos públicos:** minutos ilimitados
- **Repos privados:** 2000 min/mês
- A cada 10 min ≈ ~4320 runs/mês × ~2 min cada ≈ 8640 min → precisa de repo **público**
- A cada 30 min num repo privado: ~1440 runs × 2 min = 2880 min → justo

**Recomendação:** usa repo público (o código não tem dados sensíveis, os tokens estão nos Secrets).

## Troubleshooting

- **Não recebo mensagens:** verifica os secrets no GitHub e testa o bot mandando uma mensagem
- **"Nenhum produto encontrado":** a Worten pode ter mudado o HTML. Verifica o `debug_screenshot.png` no repositório
- **Workflow não corre:** verifica em Actions se está ativado
