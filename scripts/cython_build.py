import os
import sys
from setuptools import setup, Extension
from Cython.Build import cythonize

# Definicao de pastas
BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")
SRC_DIR = os.path.join(BACKEND_DIR, "src")

# Modulos criticos que deverao ser ofuscados via compilacao nativa Cython
CRITICAL_MODULES = [
    # O app principal que contem logica vital
    os.path.join(BACKEND_DIR, "app.py"),

    # Maquina de estados contendo as regras de negocio Edge
    os.path.join(SRC_DIR, "core", "state_machine.py"),

    # Script de seguranca de carregamento do modelo ONNX e TPM
    os.path.join(SRC_DIR, "security", "tpm_model_loader.py"),

    # Se houver outros, adicione os paths (.py) aqui...
]

def build_extensions():
    """
    Configura e executa a conversao (.py -> .c) e compilacao (.c -> .so)
    usando o Cython, protegendo o IP contra analise e engenharia reversa.
    """
    extensions = []

    for module_path in CRITICAL_MODULES:
        if not os.path.exists(module_path):
            print(f"AVISO: Modulo {module_path} nao encontrado para compilacao. Pulando...")
            continue

        # Determina o nome do pacote relativo baseando-se na estrutura de pastas.
        # Ex: "backend.src.core.state_machine"
        rel_path = os.path.relpath(module_path, os.path.dirname(BACKEND_DIR))
        module_name = rel_path.replace(os.sep, ".").replace(".py", "")

        print(f"-> Preparando extensao: {module_name} (origem: {module_path})")
        extensions.append(Extension(module_name, [module_path]))

    if not extensions:
        print("ERRO: Nenhum modulo foi preparado para compilacao Cython.")
        sys.exit(1)

    print("\n[+] Iniciando processo de ofuscacao e compilacao com Cython...")
    setup(
        name="ChikGuard_EdgeSecurity",
        ext_modules=cythonize(
            extensions,
            compiler_directives={
                'language_level': "3", # Python 3
                'always_allow_keywords': True,
                'emit_code_comments': False # Maior seguranca, nao gera comentarios no codigo C
            },
            # build_dir='build_temp', # Pode ser util para debugging do gerador C
        ),
        # Desabilita criacao do zip
        zip_safe=False,
    )
    print("\n[+] Compilacao dos modulos criticos (.so/.pyd) concluida.")
    print("Para gerar os artefatos nativos no GitHub Actions, execute: ")
    print("python scripts/cython_build.py build_ext --inplace")

if __name__ == "__main__":
    build_extensions()
