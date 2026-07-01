---
name: transcribe-audio
description: Transcreve arquivos de áudio para texto usando o app `transcribe.py` (Whisper na nuvem via Groq gratuito ou OpenAI). Use SEMPRE que o usuário pedir para transcrever, ouvir, ler ou "passar para texto" um áudio — notas de voz do WhatsApp (.ogg), gravações, ou anexos de voz em .m4a, .mp3, .wav, .flac. Dispare mesmo que o usuário só anexe/mencione um arquivo de áudio e peça "o que ele diz", "resume esse áudio" ou "transcreve aí", sem dizer a palavra "transcrever". Roda nesta máquina (Linux/WSL2) via o app `transcribe.py` — Whisper na nuvem (Groq gratuito por padrão, ou OpenAI), sem modelo local.
---

# Transcrever áudio para texto

Receita para transcrever áudio usando o **app `transcribe.py`**, que chama o **Whisper
`large-v3`** na nuvem via **Groq** (gratuito, padrão) ou **OpenAI** — API compatível com
o SDK da OpenAI nos dois casos. Idioma de comunicação: Português.

A ideia central: **use o app `transcribe.py`**, não o whisper local. O app é rápido,
preciso, converte formatos automaticamente e divide áudios longos em chunks sozinho —
você passa o áudio original direto (`.m4a`/`.ogg`/etc.) e ele cuida do resto.

> **Por que não o whisper local:** roda em CPU, é lento (minutos por áudio), ocupa GBs em
> disco e os processos morrem entre turnos. O app via API (Groq) termina em
> segundos/poucos minutos, não ocupa disco e é mais confiável.

## Pré-requisitos

O app vive em (caminho absoluto — funciona de **qualquer** sessão/cwd):

```
$HOME/.claude/skills/transcribe-audio/app
```

- **`transcribe.py`** — o CLI que faz a transcrição via API (Groq por padrão).
- **`.venv/bin/python`** — venv próprio do app (use ESTE python, não o do sistema; o
  Ubuntu bloqueia `pip install` global por PEP 668).
- **`.env`** — contém `GROQ_API_KEY` (gratuito, padrão) ou `OPENAI_API_KEY`. O app o
  carrega sozinho (do diretório de trabalho). Force o provedor com `--provider groq|openai`.
- **`ffmpeg`/`ffprobe`** — já instalados no sistema; usados para chunking e conversão.

Cheque rapidamente antes de começar:

```bash
APP="$HOME/.claude/skills/transcribe-audio/app"
ls "$APP/.venv/bin/python" "$APP/transcribe.py"
grep -qE '^(GROQ|OPENAI)_API_KEY=.+' "$APP/.env" || echo "⚠️  Falta preencher GROQ_API_KEY (gratuito) ou OPENAI_API_KEY no $APP/.env — Groq: https://console.groq.com/keys"
```

Se a chave não estiver preenchida, avise o usuário para colocá-la em `$APP/.env`
(chave começa com `gsk_`, gratuita em https://console.groq.com/keys). Não invente chave.

## Procedimento

Use caminhos absolutos e **cite o path do áudio entre aspas** (notas de voz têm espaços
no nome). Para escolher um output sem espaços, salve em `/tmp` (ex.: `/tmp/t0.txt`).

### Interface do CLI

```bash
"$APP/.venv/bin/python" "$APP/transcribe.py" "<audio>" -l pt -o "<saida.txt>"
```

- **`<audio>`** (posicional) — caminho do áudio original. **Aceita `.m4a`, `.mp3`,
  `.wav`, `.flac`, `.ogg`, `.mp4`, `.webm`** — não precisa converter antes.
- **`-l pt`** — idioma. **Sempre explícito** (`pt` português, `en` inglês, `es`
  espanhol). O padrão do app é `en`; passe `pt` para áudio em português.
- **`-o <saida.txt>`** — arquivo de saída. Se omitir, ele escolhe um nome ao lado do
  áudio. Prefira `/tmp/algo.txt` (sem espaços).
- Áudios longos: o app divide em chunks de 2min automaticamente (anti-loop). Não precisa
  fazer nada — só esperar. Flags opcionais: `--chunk-minutes N`, `--no-split`,
  `-t/--temperature`, `--detailed` (com timestamps).

### Rodar (em BACKGROUND para áudios longos)

Áudio curto (poucos segundos) roda em foreground tranquilo. Áudios longos (minutos) o app
divide em chunks e demora mais — rode em **background** (`run_in_background: true`) e
faça poll do `.txt`, em vez de bloquear. Sempre faça `cd` no diretório do app primeiro
(ele carrega o `.env` do diretório de trabalho).

```bash
cd "$HOME/.claude/skills/transcribe-audio/app"
.venv/bin/python transcribe.py "<caminho-do-audio>" -l pt -o /tmp/transcricao.txt
```

Para vários áudios, encadeie sequencialmente num único background e marque o fim:

```bash
cd "$HOME/.claude/skills/transcribe-audio/app"
.venv/bin/python transcribe.py "<audio1>" -l pt -o /tmp/t1.txt > /tmp/run1.log 2>&1; echo "A1 EXIT=$?"
.venv/bin/python transcribe.py "<audio2>" -l pt -o /tmp/t2.txt > /tmp/run2.log 2>&1; echo "A2 EXIT=$?"
echo "ALL_DONE"
```

Faça poll do marcador `ALL_DONE` (ou dos `.txt`) com o Monitor, sem `sleep` em foreground.

### Ler o resultado

O app escreve o `.txt` no `-o` que você passou. Faça poll até existir, leia com a Read e
entregue ao usuário. Se o usuário pediu resumo ou resposta sobre o conteúdo, use o texto
transcrito como base. Para áudios longos o app também salva os chunks individuais e um
`transcript_combined.txt` numa pasta `<audio>_chunks/` ao lado do áudio.

## Armadilhas (aprendidas na prática)

- **Use o app, não o whisper local.** O whisper local em CPU é lento, come disco e os
  processos morrem entre turnos. O app via API (Groq) é a forma certa.
- **`cd` no diretório do app antes de rodar.** Ele carrega a `GROQ_API_KEY` do `.env` no
  diretório de trabalho. Use o `.venv/bin/python` do app, não o python do sistema.
- **Provedor:** por padrão usa Groq (grátis). Se `GROQ_API_KEY` estiver vazia e só houver
  `OPENAI_API_KEY`, o app cai pra OpenAI (paga) automaticamente. Para forçar modelo, use
  `TRANSCRIBE_MODEL` no `.env` (ex.: `whisper-large-v3-turbo`).
- **Não converta o áudio antes.** O app aceita `.m4a`/`.ogg`/etc. e converte sozinho para
  MP3 se a API recusar o formato (fallback automático via ffmpeg).
- **Cite o path do áudio.** Notas de voz têm espaços no nome; sem aspas o comando quebra.
- **`-l pt` sempre explícito.** O padrão do app é `en`; áudio em português sem `-l pt`
  transcreve pior.
- **Áudio longo → background.** O app divide em chunks e demora; rode com
  `run_in_background` e faça poll do `.txt`. Nunca `sleep` em foreground.
- **Limites do free tier do Groq:** há limite de requisições/minuto e de tamanho por
  arquivo (~25 MB). O auto-split resolve o tamanho (chunks são pequenos). Se bater rate
  limit, espere alguns segundos e siga.

## Exemplo completo

Transcrever uma nota de voz `.m4a` em português:

```bash
# 1. ir para o diretório do app (carrega o .env)
cd "$HOME/.claude/skills/transcribe-audio/app"

# 2. transcrever (áudio original citado, idioma pt, saída sem espaços)
#    áudio longo → run_in_background: true
.venv/bin/python transcribe.py "/home/guilherme/Downloads/nota de voz.m4a" -l pt -o /tmp/t0.txt

# 3. quando terminar, ler /tmp/t0.txt
```
