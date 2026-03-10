"""
Script unificado para inicializar todos os serviços do TelegramRAG.
Uso: python run_all.py
Inicia o Django (Gunicorn), o Bot do Telegram e o Celery Worker em paralelo.
"""
import subprocess
import sys
import os
import signal
import time

# Garante que o diretório de trabalho seja a raiz do projeto
os.chdir(os.path.dirname(os.path.abspath(__file__)))

processes = []

def cleanup(signum=None, frame=None):
    """Encerra todos os processos filhos graciosamente."""
    print("\n[run_all] Encerrando todos os serviços...")
    for name, proc in processes:
        if proc.poll() is None:
            print(f"[run_all] Parando {name}...")
            proc.terminate()
    # Espera um pouco para encerrar
    for name, proc in processes:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

def main():
    print("[run_all] === TelegramRAG - Inicializacao Unificada ===")
    
    # 1. Aplicar migracoes
    print("[run_all] Aplicando migracoes do banco de dados...")
    subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], check=True)
    
    # 2. Coletar arquivos estaticos
    print("[run_all] Coletando arquivos estaticos...")
    subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"], check=True)
    
    # 3. Iniciar o Celery Worker em background
    print("[run_all] Iniciando Celery Worker...")
    celery_proc = subprocess.Popen(
        ["celery", "-A", "telegram_rag_project", "worker", "-l", "INFO"],
        stdout=sys.stdout, stderr=sys.stderr
    )
    processes.append(("Celery", celery_proc))
    
    # 4. Iniciar o Bot do Telegram em background
    print("[run_all] Iniciando Bot do Telegram...")
    bot_proc = subprocess.Popen(
        [sys.executable, "manage.py", "run_bot"],
        stdout=sys.stdout, stderr=sys.stderr
    )
    processes.append(("Bot", bot_proc))
    
    # 5. Iniciar o Gunicorn (foreground - mantém o container/processo vivo)
    print("[run_all] Iniciando servidor web Gunicorn na porta 8000...")
    web_proc = subprocess.Popen(
        ["gunicorn", "telegram_rag_project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"],
        stdout=sys.stdout, stderr=sys.stderr
    )
    processes.append(("Web", web_proc))
    
    print("[run_all] === Todos os servicos iniciados com sucesso! ===")
    
    # Monitora os processos - se algum morrer, reinicia
    while True:
        for i, (name, proc) in enumerate(processes):
            retcode = proc.poll()
            if retcode is not None:
                print(f"[run_all] AVISO: {name} encerrou com codigo {retcode}. Reiniciando...")
                time.sleep(2)
                if name == "Celery":
                    new_proc = subprocess.Popen(
                        ["celery", "-A", "telegram_rag_project", "worker", "-l", "INFO"],
                        stdout=sys.stdout, stderr=sys.stderr
                    )
                elif name == "Bot":
                    new_proc = subprocess.Popen(
                        [sys.executable, "manage.py", "run_bot"],
                        stdout=sys.stdout, stderr=sys.stderr
                    )
                elif name == "Web":
                    new_proc = subprocess.Popen(
                        ["gunicorn", "telegram_rag_project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"],
                        stdout=sys.stdout, stderr=sys.stderr
                    )
                processes[i] = (name, new_proc)
        time.sleep(5)

if __name__ == "__main__":
    main()
