#!/usr/bin/env python3
"""
Audio Transcription Tool usando OpenAI Whisper API
Transcreve arquivos de áudio M4A (e outros formatos) usando a API da OpenAI
"""

import argparse
import os
import sys
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

try:
    from openai import OpenAI
    from dotenv import load_dotenv
except ImportError:
    print("❌ Erro: Dependências não instaladas!")
    print("📦 Execute: pip install -r requirements.txt")
    sys.exit(1)

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()


class AudioTranscriber:
    """Classe para transcrição de áudio usando OpenAI Whisper API"""

    SUPPORTED_FORMATS = ['.m4a', '.mp3', '.wav', '.flac', '.ogg', '.mp4', '.mpeg', '.mpga', '.webm']
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB (limite da API OpenAI/Groq)

    # Modelo padrão por provedor. Groq serve o Whisper de graça numa API
    # compatível com a da OpenAI, então o mesmo SDK atende os dois.
    DEFAULT_MODELS = {
        'groq': 'whisper-large-v3',
        'openai': 'whisper-1',
    }
    # Custo estimado por 1k tokens (apenas para o relatório). Groq é gratuito.
    COST_PER_1K = {
        'groq': 0.0,
        'openai': 0.006,
    }
    GROQ_BASE_URL = 'https://api.groq.com/openai/v1'

    def __init__(self, api_key=None, language='en', base_url=None, model=None, provider=None):
        """
        Inicializa o transcritor.

        Suporta DOIS provedores, ambos na nuvem (nenhum modelo local):
          - groq   → Whisper large-v3, GRATUITO (GROQ_API_KEY)
          - openai → whisper-1, pago (OPENAI_API_KEY)

        Seleção do provedor:
          1. explícito via `provider` / flag --provider / env TRANSCRIBE_PROVIDER
          2. auto (padrão): usa Groq se GROQ_API_KEY existir, senão OpenAI

        Args:
            api_key: Chave da API (se None, busca a do provedor escolhido)
            language: Código do idioma (en, pt, es, etc.)
            base_url: Endpoint da API (se None, deduz do provedor)
            model: Modelo a usar (se None, usa o padrão do provedor)
            provider: 'groq' | 'openai' | 'auto' (se None, usa env ou auto)
        """
        provider = (provider or os.getenv('TRANSCRIBE_PROVIDER') or 'auto').lower()
        env_base = base_url or os.getenv('TRANSCRIBE_BASE_URL') or os.getenv('OPENAI_BASE_URL')
        groq_key = os.getenv('GROQ_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')

        if provider == 'groq':
            self.provider = 'groq'
            api_key = api_key or groq_key
            base_url = env_base or self.GROQ_BASE_URL
            if not api_key:
                raise ValueError(
                    "❌ Provedor 'groq' selecionado mas GROQ_API_KEY não definida.\n"
                    "Pegue uma chave gratuita em https://console.groq.com/keys"
                )
        elif provider == 'openai':
            self.provider = 'openai'
            api_key = api_key or openai_key
            base_url = env_base
            if not api_key:
                raise ValueError(
                    "❌ Provedor 'openai' selecionado mas OPENAI_API_KEY não definida."
                )
        elif api_key:  # auto, com chave passada direto: deduz pelo endpoint/prefixo
            if (env_base and 'groq' in env_base) or api_key.startswith('gsk_'):
                self.provider = 'groq'
                base_url = env_base or self.GROQ_BASE_URL
            else:
                self.provider = 'openai'
                base_url = env_base
        elif groq_key:  # auto, sem chave: Groq (gratuito) tem prioridade
            self.provider = 'groq'
            api_key = groq_key
            base_url = env_base or self.GROQ_BASE_URL
        elif openai_key:
            self.provider = 'openai'
            api_key = openai_key
            base_url = env_base
        else:
            raise ValueError(
                "❌ Nenhuma chave de API encontrada!\n"
                "Groq (gratuito): defina GROQ_API_KEY no .env — https://console.groq.com/keys\n"
                "OpenAI (pago): defina OPENAI_API_KEY.\n"
                "Force um provedor com --provider groq|openai."
            )

        self.default_model = (
            model or os.getenv('TRANSCRIBE_MODEL')
            or self.DEFAULT_MODELS.get(self.provider, 'whisper-1')
        )
        self.cost_per_1k = self.COST_PER_1K.get(self.provider, 0.006)

        client_kwargs = {'api_key': api_key}
        if base_url:
            client_kwargs['base_url'] = base_url
        self.client = OpenAI(**client_kwargs)
        self.language = language
        print(f"✅ Cliente inicializado (provedor: {self.provider}, modelo: {self.default_model})")

    def validate_audio_file(self, audio_path, check_size=True):
        """
        Valida se o arquivo de áudio existe e tem formato suportado

        Args:
            audio_path: Caminho para o arquivo de áudio
            check_size: Se True, valida tamanho do arquivo (padrão: True)

        Returns:
            Path object se válido

        Raises:
            FileNotFoundError: Se o arquivo não existe
            ValueError: Se o formato não é suportado ou arquivo muito grande
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"❌ Arquivo não encontrado: {audio_path}")

        if audio_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"❌ Formato não suportado: {audio_path.suffix}\n"
                f"Formatos suportados: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # Só verificar tamanho se check_size=True (desabilitado quando auto_split está ativo)
        if check_size:
            file_size = audio_path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                raise ValueError(
                    f"❌ Arquivo muito grande: {file_size / (1024*1024):.2f} MB\n"
                    f"Tamanho máximo: {self.MAX_FILE_SIZE / (1024*1024):.0f} MB"
                )

        return audio_path

    def get_audio_duration(self, audio_path):
        """
        Obtém a duração do áudio em segundos usando FFprobe

        Args:
            audio_path: Caminho para o arquivo de áudio

        Returns:
            float: Duração em segundos
        """
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_path)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
            return 0

    def split_audio(self, audio_path, chunk_duration_minutes=2, overlap_seconds=5):
        """
        Divide áudio em chunks menores com overlap usando FFmpeg

        Args:
            audio_path: Caminho para o arquivo de áudio
            chunk_duration_minutes: Duração de cada chunk em minutos (padrão: 2)
            overlap_seconds: Overlap entre chunks em segundos (padrão: 5)

        Returns:
            List[Path]: Lista de caminhos dos chunks criados
        """
        audio_path = Path(audio_path)
        duration_seconds = self.get_audio_duration(audio_path)

        if duration_seconds == 0:
            raise RuntimeError("❌ Não foi possível determinar a duração do áudio")

        chunk_duration_seconds = chunk_duration_minutes * 60
        step_seconds = chunk_duration_seconds - overlap_seconds  # Passo entre chunks
        num_chunks = int((duration_seconds - overlap_seconds) / step_seconds) + 1

        print(f"\n✂️  Dividindo áudio em chunks de {chunk_duration_minutes} minutos com overlap de {overlap_seconds}s...")
        print(f"📊 Duração total: {duration_seconds / 60:.1f} minutos")
        print(f"📦 Total de chunks: {num_chunks}")
        print(f"🔗 Overlap: {overlap_seconds}s entre chunks (anti-loop)")

        chunks = []

        for i in range(num_chunks):
            start_time = i * step_seconds

            # Não ultrapassar o fim do áudio
            if start_time >= duration_seconds:
                break

            # Criar arquivo temporário para o chunk
            temp_file = tempfile.NamedTemporaryFile(suffix=f'_chunk{i+1}.mp3', delete=False)
            chunk_path = Path(temp_file.name)
            temp_file.close()

            # Extrair chunk usando FFmpeg (MONO 16kHz para melhor transcrição)
            cmd = [
                'ffmpeg',
                '-i', str(audio_path),
                '-ss', str(start_time),
                '-t', str(chunk_duration_seconds),
                '-vn',  # Sem vídeo
                '-ar', '16000',  # 16kHz (ideal para speech recognition)
                '-ac', '1',      # Mono (reduz ruído e tamanho)
                '-b:a', '64k',   # Bitrate menor (suficiente para voz)
                '-y',
                str(chunk_path)
            ]

            try:
                subprocess.run(cmd,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             check=True)
                chunks.append(chunk_path)
                print(f"  ✅ Chunk {i+1}/{num_chunks} criado")
            except subprocess.CalledProcessError as e:
                # Limpar chunks criados em caso de erro
                for chunk in chunks:
                    if chunk.exists():
                        chunk.unlink()
                if chunk_path.exists():
                    chunk_path.unlink()
                raise RuntimeError(f"❌ Erro ao criar chunk {i+1}: {e}")

        print(f"✅ {len(chunks)} chunks criados com sucesso!\n")
        return chunks

    def convert_to_mp3(self, audio_path):
        """
        Converte arquivo de áudio para MP3 usando FFmpeg

        Args:
            audio_path: Caminho para o arquivo de áudio original

        Returns:
            Path para o arquivo MP3 temporário
        """
        audio_path = Path(audio_path)

        print(f"🔄 Convertendo áudio para MP3 (formato compatível)...")

        # Verificar se ffmpeg está instalado
        try:
            subprocess.run(['ffmpeg', '-version'],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "❌ FFmpeg não encontrado!\n"
                "Instale com: brew install ffmpeg (macOS) ou apt-get install ffmpeg (Linux)"
            )

        # Criar arquivo temporário MP3
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        temp_path = Path(temp_file.name)
        temp_file.close()

        # Converter usando FFmpeg
        cmd = [
            'ffmpeg',
            '-i', str(audio_path),
            '-vn',  # Sem vídeo
            '-ar', '44100',  # Sample rate
            '-ac', '2',  # Stereo
            '-b:a', '128k',  # Bitrate
            '-y',  # Sobrescrever
            str(temp_path)
        ]

        try:
            subprocess.run(cmd,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         check=True)
            print(f"✅ Conversão concluída: {temp_path.name}")
            return temp_path
        except subprocess.CalledProcessError as e:
            # Limpar arquivo temporário em caso de erro
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"❌ Erro ao converter áudio: {e}")

    def detect_repetitions(self, text, threshold=5, window_size=20):
        """
        Detecta se há repetições suspeitas no texto (indicativo de loop)

        Args:
            text: Texto a ser analisado
            threshold: Número mínimo de repetições para considerar loop
            window_size: Tamanho da janela de palavras para detectar repetição

        Returns:
            tuple: (has_repetitions, repeated_phrase, position)
        """
        if not text or len(text.strip()) < window_size:
            return False, None, -1

        words = text.split()

        # Procurar por sequências repetidas consecutivas
        for ws in range(window_size, max(5, window_size // 2), -1):
            for i in range(len(words) - ws * threshold):
                phrase = ' '.join(words[i:i+ws])

                # Contar repetições consecutivas
                count = 1
                j = i + ws

                while j <= len(words) - ws:
                    next_phrase = ' '.join(words[j:j+ws])
                    if phrase == next_phrase:
                        count += 1
                        j += ws
                    else:
                        break

                # Se encontrou repetições suficientes
                if count >= threshold:
                    position = len(' '.join(words[:i]))
                    return True, phrase, position

        return False, None, -1

    def transcribe(self, audio_path, model=None, response_format="text", temperature=0.2, auto_convert=True, auto_split=True, chunk_minutes=2, overlap_seconds=5):
        """
        Transcreve o arquivo de áudio usando API OpenAI

        Args:
            audio_path: Caminho para o arquivo de áudio
            model: Modelo a usar (padrão: whisper-1)
            response_format: Formato da resposta (text, json, srt, verbose_json, vtt)
            temperature: Temperatura para sampling (0-1, padrão: 0.2 para evitar loops)
            auto_convert: Se True, converte automaticamente para MP3 em caso de erro
            auto_split: Se True, divide áudios longos em chunks automaticamente (padrão: True)
            chunk_minutes: Duração de cada chunk em minutos (padrão: 2)
            overlap_seconds: Overlap entre chunks em segundos (padrão: 5)

        Returns:
            Tuple: (texto transcrito, dicionário de estatísticas)
        """
        # Resolver o modelo padrão do provedor (Groq: whisper-large-v3 / OpenAI: whisper-1)
        model = model or self.default_model

        # Se auto_split está ativo, não validar tamanho (chunks serão pequenos)
        audio_path = self.validate_audio_file(audio_path, check_size=not auto_split)
        start_time = time.time()

        print(f"\n🎙️  Transcrevendo: {audio_path.name}")
        print(f"📊 Tamanho: {audio_path.stat().st_size / (1024*1024):.2f} MB")

        # Verificar duração do áudio para decidir se deve dividir
        duration_seconds = self.get_audio_duration(audio_path)
        duration_minutes = duration_seconds / 60
        threshold_minutes = chunk_minutes * 2  # Dividir se maior que 2x o tamanho do chunk (4min para chunk de 2min)

        if auto_split and duration_minutes > threshold_minutes:
            print(f"⚠️  Áudio longo detectado ({duration_minutes:.1f} minutos)")
            print(f"✂️  Dividindo em chunks de {chunk_minutes} minutos para evitar loops...")

            chunks = None
            chunk_files = []  # Lista para armazenar paths dos arquivos de chunk salvos

            try:
                # Dividir áudio em chunks com overlap
                chunks = self.split_audio(audio_path, chunk_duration_minutes=chunk_minutes, overlap_seconds=overlap_seconds)

                # Criar diretório para chunks (mesmo diretório do áudio original)
                chunks_dir = audio_path.parent / f"{audio_path.stem}_chunks"
                chunks_dir.mkdir(exist_ok=True)

                print(f"💾 Chunks serão salvos em: {chunks_dir}/")

                # Transcrever cada chunk e salvar individualmente
                transcripts = []
                chunks_info = []
                total_retries = 0
                loops_detected = 0

                for i, chunk_path in enumerate(chunks, 1):
                    print(f"\n📝 Transcrevendo chunk {i}/{len(chunks)}...")

                    # Tentar transcrever com temperature padrão
                    chunk_transcript = None
                    current_temp = temperature
                    retry_count = 0
                    max_retries = 2

                    while retry_count <= max_retries:
                        with open(chunk_path, 'rb') as audio_file:
                            chunk_transcript = self.client.audio.transcriptions.create(
                                model=model,
                                file=audio_file,
                                language=self.language if self.language else None,  # Auto-detect se None
                                response_format="text",
                                temperature=current_temp
                            )

                        transcript_text = str(chunk_transcript).strip()

                        # Detectar loop NESTE chunk
                        has_loop, loop_phrase, loop_pos = self.detect_repetitions(transcript_text, threshold=3, window_size=15)

                        if has_loop:
                            print(f"   ⚠️  Loop detectado no chunk {i}! Frase: '{loop_phrase[:50]}...'")
                            loops_detected += 1

                            if retry_count < max_retries:
                                # Retry com temperature maior
                                current_temp += 0.2
                                retry_count += 1
                                total_retries += 1
                                print(f"   🔄 Retry #{retry_count} com temperature={current_temp:.1f}...")
                                continue
                            else:
                                # Truncar loop após max retries
                                print(f"   ✂️  Max retries atingido. Truncando loop...")
                                transcript_text = transcript_text[:loop_pos].strip()
                                break
                        else:
                            # Sucesso sem loop
                            break

                    transcripts.append(transcript_text)

                    # Coletar info do chunk
                    chunks_info.append({
                        'number': i,
                        'chars': len(transcript_text),
                        'temperature': current_temp,
                        'retries': retry_count,
                        'had_loop': has_loop
                    })

                    # Salvar chunk individual imediatamente
                    chunk_file = chunks_dir / f"chunk_{i:02d}.txt"
                    with open(chunk_file, 'w', encoding='utf-8') as f:
                        f.write(transcript_text)

                    chunk_files.append(chunk_file)

                    status_emoji = "✅" if not has_loop else "⚠️"
                    temp_info = f"(temp={current_temp:.1f})" if current_temp != temperature else ""
                    print(f"{status_emoji} Chunk {i}/{len(chunks)} transcrito e salvo ({len(transcript_text)} caracteres) {temp_info}")
                    print(f"   💾 {chunk_file.name}")

                # Juntar todas as transcrições
                full_transcript = " ".join(transcripts)

                # Salvar também o arquivo combinado
                combined_file = chunks_dir / "transcript_combined.txt"
                with open(combined_file, 'w', encoding='utf-8') as f:
                    f.write(full_transcript)

                print(f"\n🎉 Todos os chunks transcritos com sucesso!")
                print(f"📝 Total combinado: {len(full_transcript)} caracteres")
                print(f"💾 Chunks salvos em: {chunks_dir}/")
                print(f"   📄 {len(chunk_files)} arquivos individuais: chunk_01.txt, chunk_02.txt, ...")
                print(f"   📄 1 arquivo combinado: transcript_combined.txt")

                # Calcular estatísticas
                processing_time = time.time() - start_time
                total_words = len(full_transcript.split())
                estimated_tokens = int(total_words * 1.3)  # Estimativa: 1 palavra ≈ 1.3 tokens
                estimated_cost = (estimated_tokens / 1000) * self.cost_per_1k

                stats = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'audio_file': audio_path.name,
                    'file_size_mb': audio_path.stat().st_size / (1024*1024),
                    'duration_minutes': duration_minutes,
                    'language': self.language or 'auto',
                    'temperature': temperature,
                    'auto_split': True,
                    'chunk_minutes': chunk_minutes,
                    'overlap_seconds': overlap_seconds,
                    'num_chunks': len(chunks),
                    'processing_time': processing_time,
                    'total_retries': total_retries,
                    'loops_detected': loops_detected,
                    'chunks_info': chunks_info,
                    'total_chars': len(full_transcript),
                    'total_words': total_words,
                    'estimated_tokens': estimated_tokens,
                    'estimated_cost': estimated_cost,
                    'output_files': [f.name for f in chunk_files] + ['transcript_combined.txt'],
                    'warnings': []
                }

                if loops_detected > 0:
                    stats['warnings'].append(f"{loops_detected} loop(s) detectado(s) e corrigido(s)")

                return full_transcript, stats, chunks_dir

            except Exception as e:
                # Se der erro, mostrar quais chunks já foram salvos
                if chunk_files:
                    print(f"\n⚠️  Erro durante transcrição!")
                    print(f"✅ Chunks já salvos ({len(chunk_files)}/{len(chunks) if chunks else '?'}):")
                    for cf in chunk_files:
                        print(f"   💾 {cf}")
                    print(f"\n💡 Você pode recuperar as transcrições parciais em: {chunks_dir}/")
                raise

            finally:
                # Manter chunks de áudio como backup/histórico
                if chunks:
                    audio_chunks_dir = chunks_dir / "audio_chunks"
                    audio_chunks_dir.mkdir(exist_ok=True)

                    for i, chunk in enumerate(chunks, 1):
                        if chunk.exists():
                            # Mover chunks de áudio para subpasta ao invés de deletar
                            new_path = audio_chunks_dir / f"chunk_{i:02d}.mp3"
                            chunk.rename(new_path)

                    print(f"💾 {len(chunks)} chunks de áudio salvos em: {audio_chunks_dir.name}/")

        # Áudio curto - transcrever normalmente
        print(f"🔄 Processando áudio completo...")

        converted_file = None
        try:
            # Tentar transcrever com OpenAI Whisper API
            with open(audio_path, 'rb') as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    language=self.language,
                    response_format=response_format,
                    temperature=temperature
                )

            # Calcular estatísticas para áudio curto
            processing_time = time.time() - start_time
            transcript_text = str(transcript).strip()
            total_words = len(transcript_text.split())
            estimated_tokens = int(total_words * 1.3)
            estimated_cost = (estimated_tokens / 1000) * self.cost_per_1k

            stats = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'audio_file': audio_path.name,
                'file_size_mb': audio_path.stat().st_size / (1024*1024),
                'duration_minutes': duration_minutes,
                'language': self.language or 'auto',
                'temperature': temperature,
                'auto_split': False,
                'num_chunks': 1,
                'processing_time': processing_time,
                'total_retries': 0,
                'loops_detected': 0,
                'total_chars': len(transcript_text),
                'total_words': total_words,
                'estimated_tokens': estimated_tokens,
                'estimated_cost': estimated_cost,
                'output_files': [],
                'warnings': []
            }

            return transcript, stats, None  # None = sem chunks_dir

        except Exception as e:
            # Se falhar e auto_convert estiver ativo, tentar converter para MP3
            if auto_convert and "Invalid file format" in str(e):
                print(f"\n⚠️  Formato não aceito pela API. Tentando conversão automática...")

                try:
                    # Converter para MP3
                    converted_file = self.convert_to_mp3(audio_path)

                    # Tentar novamente com arquivo convertido
                    print(f"🔄 Tentando transcrição com arquivo convertido...")
                    with open(converted_file, 'rb') as audio_file:
                        transcript = self.client.audio.transcriptions.create(
                            model=model,
                            file=audio_file,
                            language=self.language,
                            response_format=response_format,
                            temperature=temperature
                        )

                    # Calcular estatísticas (mesmo formato do caminho de áudio curto)
                    processing_time = time.time() - start_time
                    transcript_text = str(transcript).strip()
                    total_words = len(transcript_text.split())
                    estimated_tokens = int(total_words * 1.3)
                    estimated_cost = (estimated_tokens / 1000) * self.cost_per_1k

                    stats = {
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'audio_file': audio_path.name,
                        'file_size_mb': audio_path.stat().st_size / (1024*1024),
                        'duration_minutes': duration_minutes,
                        'language': self.language or 'auto',
                        'temperature': temperature,
                        'auto_split': False,
                        'num_chunks': 1,
                        'processing_time': processing_time,
                        'total_retries': 0,
                        'loops_detected': 0,
                        'total_chars': len(transcript_text),
                        'total_words': total_words,
                        'estimated_tokens': estimated_tokens,
                        'estimated_cost': estimated_cost,
                        'output_files': [],
                        'warnings': ['Áudio convertido para MP3 automaticamente']
                    }

                    return transcript, stats, None  # None = sem chunks_dir

                finally:
                    # Limpar arquivo temporário
                    if converted_file and converted_file.exists():
                        converted_file.unlink()
                        print(f"🗑️  Arquivo temporário removido")
            else:
                # Re-lançar exceção se não for erro de formato ou auto_convert estiver desativado
                raise

    def save_transcription(self, transcript, output_path=None, audio_path=None, validate=True):
        """
        Salva a transcrição em arquivo TXT com validação de qualidade

        Args:
            transcript: Resultado da transcrição
            output_path: Caminho para salvar (opcional)
            audio_path: Caminho do áudio original (para gerar nome automático)
            validate: Se True, valida e detecta repetições (padrão: True)

        Returns:
            Path do arquivo salvo
            Salva SEMPRE com nome transcript.md
        """
        if output_path is None:
            if audio_path is None:
                raise ValueError("❌ Forneça output_path ou audio_path")
            audio_path = Path(audio_path)
            filename = "transcript.md"
            output_path = audio_path.with_name(filename)

        output_path = Path(output_path)
        text = str(transcript).strip()
        original_length = len(text)

        # Validar transcrição se solicitado
        if validate:
            print(f"\n🔍 Validando qualidade da transcrição...")
            has_reps, repeated_phrase, position = self.detect_repetitions(text)

            if has_reps:
                print(f"\n⚠️  AVISO: Repetições detectadas (possível loop da API)!")
                print(f"📝 Frase repetida: '{repeated_phrase[:80]}...'")
                print(f"📍 Posição: caractere {position}")

                # Truncar no início da repetição
                if position > 0:
                    text = text[:position].strip()
                    print(f"✂️  Transcrição truncada automaticamente")
                    print(f"📉 Tamanho original: {original_length} caracteres")
                    print(f"📊 Tamanho após limpeza: {len(text)} caracteres")
                    print(f"🔧 Recomendação: Re-transcrever com --temperature 0.3 ou dividir áudio")
                else:
                    print(f"⚠️  Não foi possível truncar automaticamente")
            else:
                print(f"✅ Nenhuma repetição detectada - transcrição válida!")

        # Salvar transcrição
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)

        print(f"\n✅ Transcrição salva em: {output_path}")
        print(f"📝 Total de caracteres: {len(text)}")

        return output_path

    def transcribe_with_timestamps(self, audio_path):
        """
        Transcreve com timestamps detalhados (formato verbose_json)

        Args:
            audio_path: Caminho para o arquivo de áudio

        Returns:
            Objeto JSON com segmentos e timestamps
        """
        return self.transcribe(
            audio_path,
            response_format="verbose_json"
        )

    def save_detailed_transcription(self, transcript_json, output_path):
        """
        Salva transcrição detalhada com timestamps

        Args:
            transcript_json: Resultado em formato verbose_json
            output_path: Caminho para salvar
        """
        output_path = Path(output_path)

        with open(output_path, 'w', encoding='utf-8') as f:
            # Cabeçalho
            f.write("=" * 80 + "\n")
            f.write("TRANSCRIÇÃO DETALHADA\n")
            f.write("=" * 80 + "\n\n")

            # Informações gerais
            f.write(f"Idioma: {transcript_json.language}\n")
            f.write(f"Duração: {transcript_json.duration:.2f}s\n\n")

            # Transcrição completa
            f.write("TEXTO COMPLETO:\n")
            f.write("-" * 80 + "\n")
            f.write(transcript_json.text.strip() + "\n\n")

            # Segmentos com timestamps
            if hasattr(transcript_json, 'segments') and transcript_json.segments:
                f.write("=" * 80 + "\n")
                f.write("SEGMENTOS COM TIMESTAMPS:\n")
                f.write("=" * 80 + "\n\n")

                for segment in transcript_json.segments:
                    start_time = self._format_timestamp(segment['start'])
                    end_time = self._format_timestamp(segment['end'])
                    text = segment['text'].strip()

                    f.write(f"[{start_time} -> {end_time}]\n")
                    f.write(f"{text}\n\n")

        print(f"✅ Transcrição detalhada salva em: {output_path}")

    @staticmethod
    def _format_timestamp(seconds):
        """Formata segundos em HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def save_summary_report(self, output_path, stats, chunks_dir=None):
        """
        Salva relatório de resumo com estatísticas da transcrição

        Args:
            output_path: Path base para salvar o relatório
            stats: Dicionário com estatísticas da transcrição
            chunks_dir: Diretório de chunks (se houver), para salvar o summary lá
        """
        # Se tiver chunks_dir, salvar lá. Senão, salvar junto com o output
        if chunks_dir:
            summary_path = Path(chunks_dir) / "summary.txt"
        else:
            summary_path = Path(output_path).parent / "summary.txt"

        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"RELATÓRIO DE TRANSCRIÇÃO - Whisper ({self.provider})\n")
            f.write("=" * 80 + "\n\n")

            # Informações gerais
            f.write(f"📅 Data/Hora: {stats.get('timestamp', 'N/A')}\n")
            f.write(f"🎙️  Arquivo: {stats.get('audio_file', 'N/A')}\n")
            f.write(f"📊 Tamanho do áudio: {stats.get('file_size_mb', 0):.2f} MB\n")
            f.write(f"⏱️  Duração do áudio: {stats.get('duration_minutes', 0):.2f} minutos\n\n")

            # Configurações
            f.write("-" * 80 + "\n")
            f.write("CONFIGURAÇÕES\n")
            f.write("-" * 80 + "\n")
            f.write(f"🌐 Idioma: {stats.get('language', 'auto')}\n")
            f.write(f"🌡️  Temperature inicial: {stats.get('temperature', 0.2)}\n")
            f.write(f"✂️  Auto-split: {'Sim' if stats.get('auto_split', False) else 'Não'}\n")
            if stats.get('auto_split'):
                f.write(f"📦 Chunk size: {stats.get('chunk_minutes', 2)} minutos\n")
                f.write(f"🔗 Overlap: {stats.get('overlap_seconds', 5)} segundos\n\n")
            else:
                f.write("\n")

            # Processamento
            f.write("-" * 80 + "\n")
            f.write("PROCESSAMENTO\n")
            f.write("-" * 80 + "\n")
            f.write(f"📦 Chunks gerados: {stats.get('num_chunks', 1)}\n")
            f.write(f"⏱️  Tempo de processamento: {stats.get('processing_time', 0):.1f} segundos\n")
            f.write(f"🔄 Total de retries: {stats.get('total_retries', 0)}\n")
            f.write(f"⚠️  Loops detectados: {stats.get('loops_detected', 0)}\n\n")

            # Chunks individuais (se houver)
            if stats.get('chunks_info'):
                f.write("-" * 80 + "\n")
                f.write("CHUNKS INDIVIDUAIS\n")
                f.write("-" * 80 + "\n")
                for chunk_info in stats['chunks_info']:
                    f.write(f"\n  Chunk {chunk_info['number']}/{stats.get('num_chunks', 1)}:\n")
                    f.write(f"    Caracteres: {chunk_info['chars']}\n")
                    f.write(f"    Temperature usada: {chunk_info['temperature']:.1f}\n")
                    f.write(f"    Retries: {chunk_info['retries']}\n")
                    f.write(f"    Loop detectado: {'Sim' if chunk_info['had_loop'] else 'Não'}\n")
                f.write("\n")

            # Resultado
            f.write("-" * 80 + "\n")
            f.write("RESULTADO\n")
            f.write("-" * 80 + "\n")
            f.write(f"📝 Caracteres totais: {stats.get('total_chars', 0):,}\n")
            f.write(f"📝 Palavras (estimado): {stats.get('total_words', 0):,}\n")
            f.write(f"🎯 Tokens estimados: {stats.get('estimated_tokens', 0):,}\n")
            f.write(f"💰 Custo estimado: ${stats.get('estimated_cost', 0):.4f}\n\n")

            # Arquivos gerados
            f.write("-" * 80 + "\n")
            f.write("ARQUIVOS GERADOS\n")
            f.write("-" * 80 + "\n")
            for output_file in stats.get('output_files', []):
                f.write(f"  📄 {output_file}\n")
            f.write("\n")

            # Observações
            if stats.get('warnings'):
                f.write("-" * 80 + "\n")
                f.write("⚠️  AVISOS\n")
                f.write("-" * 80 + "\n")
                for warning in stats['warnings']:
                    f.write(f"  • {warning}\n")
                f.write("\n")

            f.write("=" * 80 + "\n")

        print(f"\n📊 Relatório salvo em: {summary_path}")
        return summary_path


def main():
    """Função principal do CLI"""
    parser = argparse.ArgumentParser(
        description='🎙️  Transcreve arquivos de áudio (Whisper via Groq gratuito ou OpenAI)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Transcrição básica
  python transcribe.py audio.m4a

  # Especificar idioma
  python transcribe.py audio.m4a --language en

  # Salvar em arquivo específico
  python transcribe.py audio.m4a --output transcricao.txt

  # Transcrição detalhada com timestamps
  python transcribe.py audio.m4a --detailed

  # Usar chave de API específica
  python transcribe.py audio.m4a --api-key sk-...

Configuração da API (escolha um provedor):
  Groq (gratuito):  export GROQ_API_KEY='gsk_...'   # https://console.groq.com/keys
  OpenAI (pago):    export OPENAI_API_KEY='sk-...'
  Forçar provedor:  --provider groq|openai   (ou env TRANSCRIBE_PROVIDER)

Formatos suportados:
  .m4a, .mp3, .wav, .flac, .ogg, .mp4, .mpeg, .mpga, .webm

Limite de tamanho:
  Máximo 25 MB por arquivo
        """
    )

    parser.add_argument(
        'audio_file',
        type=str,
        help='Caminho para o arquivo de áudio'
    )

    parser.add_argument(
        '-k', '--api-key',
        type=str,
        help='Chave da API (ou use GROQ_API_KEY / OPENAI_API_KEY no ambiente)'
    )

    parser.add_argument(
        '-p', '--provider',
        type=str,
        choices=['auto', 'groq', 'openai'],
        default=None,
        help='Provedor: groq (gratuito) | openai (pago) | auto (padrão: detecta pela chave). Também via TRANSCRIBE_PROVIDER.'
    )

    parser.add_argument(
        '-l', '--language',
        type=str,
        default='en',
        help='Código do idioma (padrão: en para inglês)'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Arquivo de saída (padrão: mesmo nome do áudio com .txt)'
    )

    parser.add_argument(
        '-d', '--detailed',
        action='store_true',
        help='Salvar transcrição detalhada com timestamps'
    )

    parser.add_argument(
        '-t', '--temperature',
        type=float,
        default=0.2,
        help='Temperatura para sampling (0-1, padrão: 0.2 para evitar loops)'
    )

    parser.add_argument(
        '--no-validate',
        action='store_true',
        help='Desabilitar validação automática de repetições'
    )

    parser.add_argument(
        '--no-split',
        action='store_true',
        help='Desabilitar divisão automática de áudios longos em chunks'
    )

    parser.add_argument(
        '--chunk-minutes',
        type=int,
        default=2,
        help='Duração de cada chunk em minutos (padrão: 2, recomendado para evitar loops)'
    )

    parser.add_argument(
        '--overlap-seconds',
        type=int,
        default=5,
        help='Overlap entre chunks em segundos (padrão: 5, anti-loop)'
    )

    args = parser.parse_args()

    try:
        # Criar transcritor
        transcriber = AudioTranscriber(
            api_key=args.api_key,
            language=args.language,
            provider=args.provider
        )

        # Transcrever
        if args.detailed:
            # Transcrição com timestamps (ainda não retorna stats)
            transcript = transcriber.transcribe_with_timestamps(args.audio_file)

            # Salvar transcrição simples com validação
            simple_text = transcript.text
            output_path = transcriber.save_transcription(
                simple_text,
                output_path=args.output,
                audio_path=args.audio_file,
                validate=not args.no_validate
            )

            # Salvar transcrição detalhada
            detailed_path = output_path.with_stem(output_path.stem + '_detailed')
            transcriber.save_detailed_transcription(transcript, detailed_path)
        else:
            # Transcrição simples
            transcript, stats, chunks_dir = transcriber.transcribe(
                args.audio_file,
                temperature=args.temperature,
                auto_split=not args.no_split,
                chunk_minutes=args.chunk_minutes,
                overlap_seconds=args.overlap_seconds
            )

            # Salvar transcrição com validação
            output_path = transcriber.save_transcription(
                transcript,
                output_path=args.output,
                audio_path=args.audio_file,
                validate=not args.no_validate
            )

            # Salvar relatório de estatísticas (na pasta de chunks se existir)
            transcriber.save_summary_report(output_path, stats, chunks_dir=chunks_dir)

        print("\n🎉 Transcrição concluída com sucesso!")

    except ValueError as e:
        print(f"\n❌ Erro: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n❌ Erro: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Transcrição cancelada pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
