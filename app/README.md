# 🎙️ Audio Transcriber - OpenAI Whisper

Ferramenta de transcrição de áudio usando a API Whisper da OpenAI. Suporta diversos formatos de áudio incluindo M4A, MP3, WAV, FLAC e outros.

## 📋 Características

- ✅ Transcrição de áudio usando API OpenAI Whisper
- 🎯 Suporte a múltiplos idiomas
- 📝 Opção de transcrição com timestamps detalhados
- 🔄 Processamento rápido e preciso
- 💾 Salvamento automático em arquivos TXT
- 🌐 Suporte para diversos formatos de áudio
- 🔧 **Conversão automática para MP3** quando o formato não é aceito pela API
- 🧹 Limpeza automática de arquivos temporários
- 🛡️ **Detecção e correção automática de loops infinitos** (NOVO!)
- ✂️ **Divisão automática de áudios longos em chunks** com overlap anti-loop
- 💾 **Salvamento incremental** de chunks para evitar perda de progresso
- 🔄 **Retry automático** com temperatura adaptativa
- 📊 **Relatório estatístico completo** ao final da transcrição
- 🔍 **Validação de qualidade** pós-transcrição

## 🎵 Formatos Suportados

- `.m4a` - Apple Lossless Audio
- `.mp3` - MPEG Audio Layer 3
- `.wav` - Waveform Audio File Format
- `.flac` - Free Lossless Audio Codec
- `.ogg` - Ogg Vorbis
- `.mp4` - MPEG-4 Video (áudio)
- `.mpeg` - MPEG Audio
- `.mpga` - MPEG Audio
- `.webm` - WebM Audio

**Limite:**
- ✅ **Com auto-split (padrão):** SEM LIMITE! Áudios de qualquer tamanho são divididos automaticamente
- ⚠️ **Sem auto-split:** Máximo 25 MB (limite da API OpenAI)

## 🚀 Instalação

### 1. Instalar FFmpeg (necessário para conversão de áudio)

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows (via Chocolatey)
choco install ffmpeg
```

### 2. Instalar Dependências Python

```bash
cd transcribe_audio
pip install -r requirements.txt
```

### 3. Configurar API Key da OpenAI

Você precisa de uma chave de API da OpenAI. Obtenha em: https://platform.openai.com/api-keys

#### Opção 1: Variável de ambiente (recomendado)

```bash
export OPENAI_API_KEY='sua-chave-aqui'
```

Para tornar permanente, adicione ao seu `~/.bashrc` ou `~/.zshrc`:

```bash
echo 'export OPENAI_API_KEY="sua-chave-aqui"' >> ~/.zshrc
source ~/.zshrc
```

#### Opção 2: Passar via parâmetro

```bash
python transcribe.py audio.m4a --api-key sk-...
```

## 📖 Uso

### Transcrição Básica

```bash
python transcribe.py audio.m4a
```

Isso irá:
- Transcrever o arquivo `audio.m4a`
- Salvar a transcrição em `audio.txt` (mesmo diretório)

### Especificar Arquivo de Saída

```bash
python transcribe.py audio.m4a --output minha_transcricao.txt
```

### Transcrição com Timestamps Detalhados

```bash
python transcribe.py audio.m4a --detailed
```

Isso irá gerar dois arquivos:
- `audio.txt` - Transcrição simples
- `audio_detailed.txt` - Transcrição com timestamps e segmentos

### Especificar Idioma

```bash
# Português (padrão)
python transcribe.py audio.m4a --language pt

# Inglês
python transcribe.py audio.m4a --language en

# Espanhol
python transcribe.py audio.m4a --language es
```

### Usar Chave de API Específica

```bash
python transcribe.py audio.m4a --api-key sk-sua-chave-aqui
```

### Ajustar Temperatura

A temperatura controla a aleatoriedade da transcrição (0-1):
- 0 = mais determinístico e preciso (pode causar loops)
- 0.2 = balanceado - evita loops mantendo precisão (**padrão recomendado**)
- 1 = mais criativo e variável

```bash
# Usar temperatura padrão (0.2) - recomendado
python transcribe.py audio.m4a

# Aumentar temperatura se houver loops
python transcribe.py audio.m4a --temperature 0.3
```

### Divisão Automática de Áudios Longos (Anti-Loop)

Por padrão, áudios longos (>4 minutos) são automaticamente divididos em chunks de 2 minutos com overlap de 5 segundos para prevenir loops:

```bash
# Usar divisão automática padrão (2 min chunks, 5s overlap)
python transcribe.py audio_longo.mp3

# Personalizar tamanho dos chunks
python transcribe.py audio_longo.mp3 --chunk-minutes 3

# Personalizar overlap entre chunks
python transcribe.py audio_longo.mp3 --overlap-seconds 10

# Desabilitar divisão automática (não recomendado para áudios longos)
python transcribe.py audio_longo.mp3 --no-split
```

**Benefícios da divisão:**
- ✅ Previne loops infinitos da API
- ✅ Salvamento incremental (não perde progresso se der erro)
- ✅ Chunks preservados como backup
- ✅ Retry automático por chunk com temperatura adaptativa

### Desabilitar Validação Automática

Por padrão, o script valida a transcrição e detecta/corrige loops automaticamente. Para desabilitar:

```bash
python transcribe.py audio.m4a --no-validate
```

## 🎯 Exemplos Práticos

### Transcrever uma reunião em português

```bash
python transcribe.py reuniao.m4a --detailed --output transcricao_reuniao.txt
```

### Transcrever podcast em inglês

```bash
python transcribe.py podcast.mp3 --language en --output podcast_transcript.txt
```

### Transcrever com API key específica

```bash
python transcribe.py audio.m4a --api-key sk-... --detailed
```

## 📊 Formato da Transcrição Detalhada

Quando você usa a flag `--detailed`, o arquivo gerado terá o seguinte formato:

```
================================================================================
TRANSCRIÇÃO DETALHADA
================================================================================

Idioma: pt
Duração: 125.50s

TEXTO COMPLETO:
--------------------------------------------------------------------------------
[Texto completo da transcrição aqui...]

================================================================================
SEGMENTOS COM TIMESTAMPS:
================================================================================

[00:00:00 -> 00:00:05]
Primeiro segmento de texto transcrito.

[00:00:05 -> 00:00:12]
Segundo segmento de texto transcrito.

...
```

## 📊 Relatório de Estatísticas (NOVO!)

Ao final de cada transcrição, o script gera automaticamente um arquivo `summary.txt` com estatísticas completas:

**Localização do arquivo:**
- 📁 Com chunks: `audio_chunks/summary.txt` (dentro da pasta de chunks)
- 📁 Sem chunks: `summary.txt` (no mesmo diretório do áudio)

**Estrutura de pastas gerada (com chunks):**
```
pasta_do_audio/
├── audio_aula02.mp3                    # Áudio original
├── transcript.md                       # Transcrição completa
└── audio_aula02_chunks/                # Pasta de chunks
    ├── chunk_01.txt                    # Chunk 1 transcrito
    ├── chunk_02.txt                    # Chunk 2 transcrito
    ├── ...
    ├── transcript_combined.txt         # Todos os chunks juntos
    ├── summary.txt                     # ⭐ RELATÓRIO AQUI!
    └── audio_chunks/                   # Chunks de áudio preservados
        ├── chunk_01.mp3
        ├── chunk_02.mp3
        └── ...
```

```
================================================================================
RELATÓRIO DE TRANSCRIÇÃO - OpenAI Whisper API
================================================================================

📅 Data/Hora: 2025-01-23 14:35:20
🎙️  Arquivo: audio_aula02.mp3
📊 Tamanho do áudio: 28.45 MB
⏱️  Duração do áudio: 31.2 minutos

--------------------------------------------------------------------------------
CONFIGURAÇÕES
--------------------------------------------------------------------------------
🌐 Idioma: en
🌡️  Temperature inicial: 0.2
✂️  Auto-split: Sim
📦 Chunk size: 2 minutos
🔗 Overlap: 5 segundos

--------------------------------------------------------------------------------
PROCESSAMENTO
--------------------------------------------------------------------------------
📦 Chunks gerados: 16
⏱️  Tempo de processamento: 245.3 segundos
🔄 Total de retries: 2
⚠️  Loops detectados: 1

--------------------------------------------------------------------------------
CHUNKS INDIVIDUAIS
--------------------------------------------------------------------------------

  Chunk 1/16:
    Caracteres: 2453
    Temperature usada: 0.2
    Retries: 0
    Loop detectado: Não

  Chunk 5/16:
    Caracteres: 1834
    Temperature usada: 0.4
    Retries: 1
    Loop detectado: Sim

  [...]

--------------------------------------------------------------------------------
RESULTADO
--------------------------------------------------------------------------------
📝 Caracteres totais: 38,452
📝 Palavras (estimado): 6,742
🎯 Tokens estimados: 8,765
💰 Custo estimado: $0.0526

--------------------------------------------------------------------------------
ARQUIVOS GERADOS
--------------------------------------------------------------------------------
  📄 chunk_01.txt
  📄 chunk_02.txt
  [...]
  📄 transcript_combined.txt

--------------------------------------------------------------------------------
⚠️  AVISOS
--------------------------------------------------------------------------------
  • 1 loop(s) detectado(s) e corrigido(s)

================================================================================
```

**Informações incluídas:**
- ✅ Data/hora da transcrição
- ✅ Detalhes do arquivo de áudio
- ✅ Configurações usadas (temperatura, chunks, overlap)
- ✅ Estatísticas de processamento
- ✅ Detalhes de cada chunk individual
- ✅ Tokens estimados e custo aproximado
- ✅ Lista de arquivos gerados
- ✅ Avisos sobre loops detectados

## ⚙️ Opções do CLI

```
usage: transcribe.py [-h] [-k API_KEY] [-l LANGUAGE] [-o OUTPUT] [-d] [-t TEMPERATURE]
                     [--no-validate] [--no-split] [--chunk-minutes MINUTES]
                     [--overlap-seconds SECONDS] audio_file

Argumentos posicionais:
  audio_file                Caminho para o arquivo de áudio

Opções:
  -h, --help                Mostrar ajuda
  -k, --api-key             Chave da API OpenAI
  -l, --language            Código do idioma (padrão: en)
  -o, --output              Arquivo de saída
  -d, --detailed            Transcrição detalhada com timestamps
  -t, --temperature         Temperatura para sampling (0-1, padrão: 0.2)
  --no-validate             Desabilitar validação automática de repetições
  --no-split                Desabilitar divisão automática em chunks
  --chunk-minutes MINUTES   Duração dos chunks em minutos (padrão: 2)
  --overlap-seconds SECONDS Overlap entre chunks em segundos (padrão: 5)
```

## 🛡️ Proteção Contra Loops Infinitos (NOVO!)

O script agora detecta e corrige automaticamente loops infinitos causados pela API Whisper!

### Como Funciona

1. **Detecção Automática**: Após a transcrição, o script analisa o texto procurando por repetições suspeitas
2. **Truncamento Inteligente**: Se detectar loop, trunca o texto automaticamente no início da repetição
3. **Relatório Detalhado**: Mostra exatamente onde o loop começou e quanto foi removido

### Exemplo de Saída

```
🔍 Validando qualidade da transcrição...

⚠️  AVISO: Repetições detectadas (possível loop da API)!
📝 Frase repetida: 'So if you want to run a long-running bash command and feed the output...'
📍 Posição: caractere 15234
✂️  Transcrição truncada automaticamente
📉 Tamanho original: 125000 caracteres
📊 Tamanho após limpeza: 15234 caracteres
🔧 Recomendação: Re-transcrever com --temperature 0.3 ou dividir áudio

✅ Transcrição salva em: transcript.md
📝 Total de caracteres: 15234
```

### Quando Loops Acontecem?

- ✅ **Áudios muito longos** (>30 minutos)
- ✅ **Temperature muito baixa** (0.0)
- ✅ **Silêncios prolongados** no áudio
- ✅ **Ruído ou eco** persistente
- ✅ **Qualidade de áudio ruim**

### Como Prevenir Loops?

1. **Use temperature 0.2 ou maior** (padrão do script)
2. **Divida áudios longos** em chunks de 10-15 minutos
3. **Melhore a qualidade do áudio** antes de transcrever
4. **Use `--detailed`** para ter timestamps e identificar problemas

## 💡 Dicas

1. **Qualidade do áudio**: Áudio de melhor qualidade gera transcrições mais precisas
2. **Idioma correto**: Sempre especifique o idioma correto com `--language`
3. **Timestamps**: Use `--detailed` quando precisar saber em que momento algo foi dito
4. **Limite de tamanho**: Arquivos maiores que 25 MB precisam ser divididos
5. **Temperature 0.2+**: Use temperature >= 0.2 para evitar loops (padrão do script)
6. **Áudios longos**: Para áudios >30min, considere dividir em partes menores

## 🔧 Como Usar Programaticamente

Você também pode usar a classe `AudioTranscriber` em seus próprios scripts Python:

```python
from transcribe import AudioTranscriber

# Criar transcritor
transcriber = AudioTranscriber(
    api_key='sua-chave-aqui',  # ou None para usar OPENAI_API_KEY
    language='pt'
)

# Transcrição simples
transcript = transcriber.transcribe('audio.m4a')
transcriber.save_transcription(transcript, audio_path='audio.m4a')

# Transcrição com timestamps
transcript_json = transcriber.transcribe_with_timestamps('audio.m4a')
transcriber.save_detailed_transcription(transcript_json, 'audio_detailed.txt')
```

## 🔧 Conversão Automática de Áudio

O script detecta automaticamente quando um arquivo de áudio não é aceito pela API OpenAI e faz a conversão para MP3 automaticamente!

**Como funciona:**
1. Script tenta transcrever o arquivo original
2. Se a API rejeitar o formato, converte para MP3 automaticamente
3. Transcreve o arquivo convertido
4. Remove o arquivo temporário após conclusão

**Requisitos:**
- FFmpeg instalado no sistema (obrigatório para conversão automática)

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows (via Chocolatey)
choco install ffmpeg
```

**Nota:** O script usa FFmpeg diretamente via subprocess, sem dependências Python problemáticas.

**Exemplo de uso:**
```bash
# Arquivo 3GPP será convertido automaticamente para MP3
python transcribe.py audio_problematico.m4a
```

Saída:
```
⚠️  Formato não aceito pela API. Tentando conversão automática...
🔄 Convertendo áudio para MP3 (formato compatível)...
✅ Conversão concluída: tmpxyz123.mp3
🔄 Tentando transcrição com arquivo convertido...
✅ Transcrição salva em: audio_problematico.txt
🗑️  Arquivo temporário removido
```

## 🐛 Solução de Problemas

### Erro: OPENAI_API_KEY não encontrada

```bash
export OPENAI_API_KEY='sua-chave-aqui'
```

### Erro: Arquivo muito grande

**Solução:** O script agora divide automaticamente áudios grandes! Se você receber esse erro, significa que:

1. Você usou a flag `--no-split` (que desabilita divisão automática)
2. **Solução:** Remova a flag `--no-split` e deixe o script dividir automaticamente

```bash
# ❌ VAI FALHAR para arquivos >25MB
python transcribe.py audio_grande.mp3 --no-split

# ✅ FUNCIONA para qualquer tamanho
python transcribe.py audio_grande.mp3
```

Se você realmente não quer usar auto-split, pode:
1. Comprimir o áudio manualmente
2. Dividir em partes menores
3. Usar um formato mais eficiente (ex: MP3 em vez de WAV)

### Erro: Dependências não instaladas

```bash
pip install -r requirements.txt
```

### Erro: FFmpeg não encontrado

Se você receber erro de conversão de áudio, instale o FFmpeg:

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# Baixe de: https://ffmpeg.org/download.html
```

## 📝 Custos da API

A API Whisper da OpenAI cobra por minuto de áudio transcrito. Consulte os preços atuais em: https://openai.com/pricing

Preço aproximado (verificar site oficial):
- ~$0.006 por minuto de áudio

## 🔗 Links Úteis

- [OpenAI API Documentation](https://platform.openai.com/docs/guides/speech-to-text)
- [OpenAI Pricing](https://openai.com/pricing)
- [Get API Key](https://platform.openai.com/api-keys)

## 🌐 Tradução de Chunks Transcritos

Após transcrever áudio em chunks, você pode traduzir todos os chunks usando o script `translate_chunks.py`.

### Uso Básico

```bash
# Traduzir chunks para português brasileiro (padrão)
python translate_chunks.py "pasta/chunks"

# Traduzir para português brasileiro (explícito)
python translate_chunks.py "pasta/chunks" --target pt_br

# Traduzir para espanhol
python translate_chunks.py "pasta/chunks" --target es

# Traduzir para inglês americano
python translate_chunks.py "pasta/chunks" --target en_us

# Especificar idioma origem e destino
python translate_chunks.py "pasta/chunks" --source en --target pt_br
```

### Opções Disponíveis

- `--source`: Idioma de origem (padrão: `en`)
- `--target`: Idioma de destino (padrão: `pt`)
- `--output`: Arquivo de saída para tradução combinada
- `--no-individual`: Não salvar chunks traduzidos individualmente
- `-k, --api-key`: Chave da API OpenAI (ou use variável de ambiente)

### Formato Esperado

O script espera encontrar arquivos no formato:
```
pasta/chunks/
├── chunk_01.txt
├── chunk_02.txt
├── chunk_03.txt
└── ...
```

### Saída Gerada

O script gera:
- `translated_combined_[idioma].txt`: Arquivo com todos os chunks traduzidos combinados
- `translated_chunks/`: Pasta com cada chunk traduzido individualmente (se não usar `--no-individual`)
- `translation_summary.txt`: Relatório com estatísticas da tradução

### Exemplo Completo

```bash
# 1. Transcrever áudio (gera chunks)
python transcribe.py audio.mp3

# 2. Traduzir os chunks gerados
python translate_chunks.py "audio_chunks" --source en --target pt

# Resultado:
# - audio_chunks/translated_combined_pt.txt (tradução completa)
# - audio_chunks/translated_chunks/ (chunks individuais traduzidos)
# - audio_chunks/translation_summary.txt (relatório)
```

### Idiomas Suportados

O script suporta qualquer idioma que o GPT-4o-mini suporta. Alguns exemplos:

**Códigos básicos:**
- `pt` ou `pt_br` - Português brasileiro (padrão)
- `pt_pt` - Português de Portugal
- `en` ou `en_us` - Inglês americano
- `en_gb` ou `en_uk` - Inglês britânico
- `es` ou `es_es` - Espanhol da Espanha
- `es_mx` ou `es_ar` - Espanhol latino-americano
- `fr` - Francês
- `de` - Alemão
- `it` - Italiano
- `ja` - Japonês
- `zh` ou `zh_cn` - Chinês simplificado
- `zh_tw` - Chinês tradicional
- `ru` - Russo
- `ko` - Coreano
- `ar` - Árabe
- `hi` - Hindi

**Nota:** Você pode usar códigos com underscore (`pt_br`) ou hífen (`pt-br`). O script normaliza automaticamente.

## 📄 Licença

Este projeto é de código aberto e está disponível sob a licença MIT.

## 👨‍💻 Autor

Desenvolvido para uso no vault "davidsongomes" - Sistema de PKM (Personal Knowledge Management)

---

**Última atualização:** 02/02/2026
