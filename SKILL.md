---
name: transcribe-audio
description: Transcreve arquivos de áudio para texto usando o app de transcrição OpenAI (Whisper API). Use SEMPRE que o usuário pedir para transcrever, ouvir, ler ou "passar para texto" um áudio — notas de voz do WhatsApp (.ogg), gravações, ou anexos de voz em .m4a, .mp3, .wav, .flac. Dispare mesmo que o usuário só anexe/mencione um arquivo de áudio e peça "o que ele diz", "resume esse áudio" ou "transcreve aí", sem dizer a palavra "transcrever". Roda nesta máquina (macOS) via o app `transcribe.py` (API OpenAI).
---

# Transcrever áudio para texto

Receita VALIDADA nesta máquina (macOS/darwin) para transcrever áudio usando o **app de
transcrição** que chama a **API da OpenAI (Whisper)**. Idioma de comunicação: Português.

A ideia central: **use o app `transcribe.py`**, não o whisper local. O app é rápido,
preciso, converte formatos automaticamente e divide áudios longos em chunks sozinho —
você passa o áudio original direto (`.m4a`/`.ogg`/etc.) e ele cuida do resto.

> **Por que não o whisper local:** roda em CPU, é lento (minutos por áudio) e os
> processos morrem entre turnos. O app via API termina em segundos/poucos minutos e é
> mais confiável.

## Pré-requisitos

O app vive em (path com espaços — **sempre entre aspas**):

```
./app
```

- **`transcribe.py`** — o CLI que faz a transcrição via API OpenAI.
- **`.venv/bin/python`** — venv próprio do app (use ESTE python, não o do sistema).
- **`.env`** — contém `OPENAI_API_KEY` (já configurado). O app o carrega sozinho.
- **`ffmpeg`** (`/opt/homebrew/bin`) — usado pelo app para conversão automática.

Cheque rapidamente antes de começar:

```bash
APP="./app"
ls "$APP/.venv/bin/python" "$APP/transcribe.py"
```

## Procedimento

Use caminhos absolutos e **cite sempre os paths entre aspas** — tanto o áudio (notas de
voz têm espaços no nome) quanto o diretório do app (tem espaços). Para escolher um
output sem espaços, salve em `/tmp` (ex.: `/tmp/t0.txt`).

### Interface do CLI

```bash
.venv/bin/python transcribe.py "<audio>" -l pt -o "<saida.txt>"
```

- **`<audio>`** (posicional) — caminho do áudio original. **Aceita `.m4a`, `.mp3`,
  `.wav`, `.flac`, `.ogg`, `.mp4`, `.webm`** — não precisa converter antes.
- **`-l pt`** — idioma. **Sempre explícito** (`pt` para português, `en` inglês, `es`
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
cd "./app"
.venv/bin/python transcribe.py "<caminho-do-audio>" -l pt -o /tmp/transcricao.txt
```

Para vários áudios, encadeie sequencialmente num único background e marque o fim:

```bash
cd "./app"
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

- **Use o app, não o whisper local.** O whisper local em CPU é lento e os processos
  morrem entre turnos — vários retries falharam por isso. O app via API é a forma certa.
- **`cd` no diretório do app antes de rodar.** Ele carrega o `OPENAI_API_KEY` do `.env`
  no diretório de trabalho. Use o `.venv/bin/python` do app, não o python do sistema.
- **Não converta o áudio antes.** O app aceita `.m4a`/`.ogg`/etc. e converte sozinho
  (a API recusa `.m4a` direto, mas o app tem fallback automático para MP3).
- **Cite TODOS os paths.** O diretório do app E os áudios têm espaços; sem aspas o
  comando quebra.
- **`-l pt` sempre explícito.** O padrão do app é `en`; áudio em português sem `-l pt`
  transcreve pior.
- **Áudio longo → background.** O app divide em chunks e demora; rode com
  `run_in_background` e faça poll do `.txt`. Nunca `sleep` em foreground.
- **Bug corrigido (2026-06-17):** o caminho de fallback de conversão retornava 1 valor
  em vez da tripla `(transcript, stats, chunks_dir)` → `too many values to unpack
  (expected 3)`. Já corrigido no `transcribe.py`. Se reaparecer, é regressão nesse
  retorno.

## Exemplo completo

Transcrever uma nota de voz `.m4a` em português:

```bash
# 1. ir para o diretório do app (carrega o .env)
cd "./app"

# 2. transcrever (áudio original citado, idioma pt, saída sem espaços)
#    áudio longo → run_in_background: true
.venv/bin/python transcribe.py "/Users/me/Downloads/nota de voz.m4a" -l pt -o /tmp/t0.txt

# 3. quando terminar, ler /tmp/t0.txt
```
