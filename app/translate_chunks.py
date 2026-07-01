#!/usr/bin/env python3
"""
Translate Audio Chunks Script

Reads transcribed text chunks from a folder, translates each chunk using OpenAI,
and combines everything into a final translated file.
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from openai import OpenAI
    from dotenv import load_dotenv
except ImportError:
    print("❌ Erro: Dependências não instaladas!")
    print("📦 Execute: pip install openai python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv()


class ChunkTranslator:
    """Class to translate text chunks using OpenAI"""

    def __init__(self, api_key=None, target_language="pt", source_language="en"):
        """
        Initialize translator

        Args:
            api_key: OpenAI API key (if None, searches for OPENAI_API_KEY)
            target_language: Target language code (default: "pt" for Portuguese)
            source_language: Source language code (default: "en" for English)
        """
        if api_key is None:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError(
                    "❌ OPENAI_API_KEY não encontrada!\n"
                    "Configure com: export OPENAI_API_KEY='sua-chave-aqui'"
                )

        self.client = OpenAI(api_key=api_key)
        self.target_language = target_language
        self.source_language = source_language
        print(f"✅ Cliente OpenAI inicializado!")
        print(f"🌐 Traduzindo de {self._get_language_name(source_language)} para {self._get_language_name(target_language)}")

    def get_chunk_files(self, chunks_dir: Path):
        """
        Get all chunk text files from directory, sorted by number

        Args:
            chunks_dir: Directory containing chunk files

        Returns:
            List of Path objects sorted by chunk number
        """
        chunks_dir = Path(chunks_dir)

        if not chunks_dir.exists():
            raise FileNotFoundError(f"❌ Diretório não encontrado: {chunks_dir}")

        # Find all .txt files that match chunk pattern
        chunk_files = []
        for file_path in chunks_dir.glob("chunk_*.txt"):
            try:
                # Extract chunk number from filename (chunk_01.txt -> 1)
                chunk_num = int(file_path.stem.split('_')[1])
                chunk_files.append((chunk_num, file_path))
            except (ValueError, IndexError):
                # If filename doesn't match pattern, skip it
                continue

        # Sort by chunk number
        chunk_files.sort(key=lambda x: x[0])

        if not chunk_files:
            raise ValueError(
                f"❌ Nenhum arquivo de chunk encontrado em: {chunks_dir}\n"
                f"Esperado formato: chunk_01.txt, chunk_02.txt, etc."
            )

        print(f"📦 Encontrados {len(chunk_files)} chunks para traduzir")
        return [path for _, path in chunk_files]

    def _get_language_name(self, lang_code: str) -> str:
        """
        Get human-readable language name from language code
        
        Args:
            lang_code: Language code (e.g., 'pt', 'pt_br', 'en', 'en_us')
            
        Returns:
            Human-readable language name
        """
        # Normalize language code (extract base code)
        base_code = lang_code.lower().split('_')[0]
        
        language_names = {
            "pt": "português brasileiro",
            "en": "inglês",
            "es": "espanhol",
            "fr": "francês",
            "de": "alemão",
            "it": "italiano",
            "ja": "japonês",
            "zh": "chinês",
            "ru": "russo",
            "ko": "coreano",
            "ar": "árabe",
            "hi": "hindi",
            "nl": "holandês",
            "pl": "polonês",
            "tr": "turco",
            "sv": "sueco",
            "da": "dinamarquês",
            "no": "norueguês",
            "fi": "finlandês",
        }
        
        # Handle specific regional variants
        if lang_code.lower() in ["pt_br", "pt-br"]:
            return "português brasileiro"
        elif lang_code.lower() in ["pt_pt", "pt-pt"]:
            return "português de Portugal"
        elif lang_code.lower() in ["en_us", "en-us"]:
            return "inglês americano"
        elif lang_code.lower() in ["en_gb", "en-gb", "en_uk", "en-uk"]:
            return "inglês britânico"
        elif lang_code.lower() in ["es_es", "es-es"]:
            return "espanhol da Espanha"
        elif lang_code.lower() in ["es_mx", "es-mx", "es_ar", "es-ar"]:
            return "espanhol latino-americano"
        elif lang_code.lower() in ["zh_cn", "zh-cn"]:
            return "chinês simplificado"
        elif lang_code.lower() in ["zh_tw", "zh-tw"]:
            return "chinês tradicional"
        
        # Return mapped name or original code if not found
        return language_names.get(base_code, lang_code)

    def translate_chunk(self, text: str, chunk_num: int, total_chunks: int) -> str:
        """
        Translate a single chunk of text using OpenAI

        Args:
            text: Text to translate
            chunk_num: Current chunk number (for progress display)
            total_chunks: Total number of chunks (for progress display)

        Returns:
            Translated text
        """
        if not text.strip():
            return ""

        print(f"🔄 Traduzindo chunk {chunk_num}/{total_chunks}... ({len(text)} caracteres)")

        # Get human-readable language names
        target_lang_name = self._get_language_name(self.target_language)
        source_lang_name = self._get_language_name(self.source_language)

        prompt = f"""Traduza o seguinte texto de {source_lang_name} para {target_lang_name}.
Mantenha o tom e estilo do texto original.
Traduza de forma natural e fluida.
Retorne APENAS o texto traduzido, sem comentários ou explicações.

Texto a traduzir:
{text}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using cheaper model for translation
                messages=[
                    {
                        "role": "system",
                        "content": f"Você é um tradutor profissional especializado em traduzir de {source_lang_name} para {target_lang_name}."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent translation
            )

            translated_text = response.choices[0].message.content.strip()
            print(f"✅ Chunk {chunk_num}/{total_chunks} traduzido ({len(translated_text)} caracteres)")

            return translated_text

        except Exception as e:
            print(f"❌ Erro ao traduzir chunk {chunk_num}: {e}")
            raise

    def translate_chunks_folder(
        self,
        chunks_dir: Path,
        output_file: Path = None,
        save_individual: bool = True
    ):
        """
        Translate all chunks in a folder and combine into final file

        Args:
            chunks_dir: Directory containing chunk text files
            output_file: Path to save final translated file (optional)
            save_individual: If True, save each translated chunk individually

        Returns:
            Tuple: (combined_translated_text, stats_dict)
        """
        chunks_dir = Path(chunks_dir)
        start_time = time.time()

        print(f"\n📂 Processando chunks de: {chunks_dir}")
        print(f"🌐 Idioma origem: {self.source_language}")
        print(f"🌐 Idioma destino: {self.target_language}\n")

        # Get all chunk files
        chunk_files = self.get_chunk_files(chunks_dir)

        # Create output directory for translated chunks
        if save_individual:
            translated_chunks_dir = chunks_dir / "translated_chunks"
            translated_chunks_dir.mkdir(exist_ok=True)
            print(f"💾 Chunks traduzidos serão salvos em: {translated_chunks_dir}/\n")

        # Translate each chunk
        translated_chunks = []
        translated_files = []
        total_chars_translated = 0
        total_tokens_used = 0
        errors = []

        for i, chunk_file in enumerate(chunk_files, 1):
            try:
                # Read chunk text
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunk_text = f.read().strip()

                if not chunk_text:
                    print(f"⚠️  Chunk {i} está vazio, pulando...")
                    translated_chunks.append("")
                    continue

                # Translate chunk
                translated_text = self.translate_chunk(chunk_text, i, len(chunk_files))

                translated_chunks.append(translated_text)
                total_chars_translated += len(translated_text)

                # Save individual translated chunk if requested
                if save_individual:
                    translated_file = translated_chunks_dir / f"chunk_{i:02d}_translated.txt"
                    with open(translated_file, 'w', encoding='utf-8') as f:
                        f.write(translated_text)
                    translated_files.append(translated_file)
                    print(f"   💾 {translated_file.name}")

                # Small delay to avoid rate limits
                time.sleep(0.5)

            except Exception as e:
                error_msg = f"Erro no chunk {i}: {e}"
                errors.append(error_msg)
                print(f"❌ {error_msg}")
                # Add placeholder for failed chunk
                translated_chunks.append(f"[ERRO NA TRADUÇÃO DO CHUNK {i}]")

        # Combine all translated chunks
        combined_text = "\n\n".join(translated_chunks)

        # Determine output file path
        if output_file is None:
            # Normalize language code for filename (remove underscores)
            lang_code_normalized = self.target_language.lower().replace('_', '-')
            output_file = chunks_dir / f"translated_combined_{lang_code_normalized}.txt"
        else:
            output_file = Path(output_file)

        # Save combined translated file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(combined_text)

        # Calculate statistics
        processing_time = time.time() - start_time
        total_words = len(combined_text.split())
        estimated_tokens = int(total_words * 1.3)  # Rough estimate
        estimated_cost = (estimated_tokens / 1000) * 0.15  # gpt-4o-mini pricing

        stats = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'chunks_dir': str(chunks_dir),
            'source_language': self.source_language,
            'target_language': self.target_language,
            'num_chunks': len(chunk_files),
            'chunks_translated': len([c for c in translated_chunks if c]),
            'chunks_failed': len(errors),
            'processing_time': processing_time,
            'total_chars_translated': total_chars_translated,
            'total_words': total_words,
            'estimated_tokens': estimated_tokens,
            'estimated_cost': estimated_cost,
            'output_file': str(output_file),
            'translated_files': [str(f) for f in translated_files] if save_individual else [],
            'errors': errors
        }

        # Print summary
        print(f"\n{'='*80}")
        print(f"✅ Tradução concluída!")
        print(f"{'='*80}")
        print(f"📝 Chunks processados: {stats['chunks_translated']}/{stats['num_chunks']}")
        if errors:
            print(f"⚠️  Erros: {len(errors)}")
        print(f"📊 Caracteres traduzidos: {total_chars_translated:,}")
        print(f"📊 Palavras: {total_words:,}")
        print(f"⏱️  Tempo de processamento: {processing_time:.1f} segundos")
        print(f"💰 Custo estimado: ${estimated_cost:.4f}")
        print(f"💾 Arquivo final: {output_file}")
        if save_individual:
            print(f"💾 Chunks individuais: {translated_chunks_dir}/")
        print(f"{'='*80}\n")

        return combined_text, stats

    def save_summary_report(self, output_path: Path, stats: dict):
        """
        Save summary report with translation statistics

        Args:
            output_path: Base path to save report
            stats: Dictionary with translation statistics
        """
        summary_path = Path(output_path).parent / "translation_summary.txt"

        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("RELATÓRIO DE TRADUÇÃO - OpenAI GPT\n")
            f.write("=" * 80 + "\n\n")

            # General information
            f.write(f"📅 Data/Hora: {stats.get('timestamp', 'N/A')}\n")
            f.write(f"📂 Diretório de chunks: {stats.get('chunks_dir', 'N/A')}\n")
            f.write(f"🌐 Idioma origem: {stats.get('source_language', 'N/A')}\n")
            f.write(f"🌐 Idioma destino: {stats.get('target_language', 'N/A')}\n\n")

            # Processing
            f.write("-" * 80 + "\n")
            f.write("PROCESSAMENTO\n")
            f.write("-" * 80 + "\n")
            f.write(f"📦 Total de chunks: {stats.get('num_chunks', 0)}\n")
            f.write(f"✅ Chunks traduzidos: {stats.get('chunks_translated', 0)}\n")
            f.write(f"❌ Chunks com erro: {stats.get('chunks_failed', 0)}\n")
            f.write(f"⏱️  Tempo de processamento: {stats.get('processing_time', 0):.1f} segundos\n\n")

            # Results
            f.write("-" * 80 + "\n")
            f.write("RESULTADO\n")
            f.write("-" * 80 + "\n")
            f.write(f"📝 Caracteres traduzidos: {stats.get('total_chars_translated', 0):,}\n")
            f.write(f"📝 Palavras: {stats.get('total_words', 0):,}\n")
            f.write(f"🎯 Tokens estimados: {stats.get('estimated_tokens', 0):,}\n")
            f.write(f"💰 Custo estimado: ${stats.get('estimated_cost', 0):.4f}\n\n")

            # Output files
            f.write("-" * 80 + "\n")
            f.write("ARQUIVOS GERADOS\n")
            f.write("-" * 80 + "\n")
            f.write(f"📄 Arquivo combinado: {stats.get('output_file', 'N/A')}\n")
            if stats.get('translated_files'):
                f.write(f"\n📄 Chunks individuais traduzidos:\n")
                for tf in stats['translated_files']:
                    f.write(f"  • {Path(tf).name}\n")
            f.write("\n")

            # Errors
            if stats.get('errors'):
                f.write("-" * 80 + "\n")
                f.write("⚠️  ERROS\n")
                f.write("-" * 80 + "\n")
                for error in stats['errors']:
                    f.write(f"  • {error}\n")
                f.write("\n")

            f.write("=" * 80 + "\n")

        print(f"📊 Relatório salvo em: {summary_path}")
        return summary_path


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Traduz chunks de texto transcritos usando OpenAI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

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

  # Especificar arquivo de saída
  python translate_chunks.py "pasta/chunks" --output traducao_final.txt

  # Não salvar chunks individuais
  python translate_chunks.py "pasta/chunks" --no-individual

Configuração da API:
  Defina a variável de ambiente OPENAI_API_KEY:
  export OPENAI_API_KEY='sua-chave-aqui'

Formato esperado dos chunks:
  chunk_01.txt, chunk_02.txt, chunk_03.txt, ...
        """
    )

    parser.add_argument(
        'chunks_dir',
        type=str,
        help='Diretório contendo os arquivos de chunks (chunk_01.txt, chunk_02.txt, ...)'
    )

    parser.add_argument(
        '-k', '--api-key',
        type=str,
        help='Chave da API OpenAI (ou use OPENAI_API_KEY)'
    )

    parser.add_argument(
        '-s', '--source',
        type=str,
        default='en',
        help='Idioma de origem (padrão: en)'
    )

    parser.add_argument(
        '-t', '--target',
        type=str,
        default='pt_br',
        help='Idioma de destino (padrão: pt_br). Exemplos: pt_br, pt, en, es, fr, en_us, en_gb'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Arquivo de saída para tradução combinada (padrão: translated_combined_[idioma].txt)'
    )

    parser.add_argument(
        '--no-individual',
        action='store_true',
        help='Não salvar chunks traduzidos individualmente'
    )

    args = parser.parse_args()

    try:
        # Create translator
        translator = ChunkTranslator(
            api_key=args.api_key,
            target_language=args.target,
            source_language=args.source
        )

        # Translate chunks
        combined_text, stats = translator.translate_chunks_folder(
            chunks_dir=Path(args.chunks_dir),
            output_file=args.output,
            save_individual=not args.no_individual
        )

        # Save summary report
        output_path = Path(stats['output_file'])
        translator.save_summary_report(output_path, stats)

        print("🎉 Tradução concluída com sucesso!")

    except ValueError as e:
        print(f"\n❌ Erro: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n❌ Erro: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tradução cancelada pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
