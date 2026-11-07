
import os, sys, time, webbrowser, subprocess
from pathlib import Path

ROOT = Path(r"C:\Perm_Repair")
if not ROOT.exists():
    ROOT = Path(__file__).parent

def copy_to_clipboard(text):
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except:
        try:
            process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, close_fds=True)
            process.communicate(text.encode('utf-8'))
            return True
        except:
            return False

def open_new_terminal(task_id):
    bat_content = f"@echo off\ntitle SHVEYA TASK {task_id}\necho TASK {task_id}\npause\n"
    bat_path = ROOT / f"task_{task_id}.bat"
    try:
        bat_path.write_text(bat_content, encoding='cp1251')
        subprocess.Popen(f'start cmd /k "{bat_path}"', shell=True)
        print(f"  Открыл терминал для {task_id}")
        return True
    except Exception as e:
        print(f"  Ошибка терминала: {e}")
        return False

def open_new_browser_tab(task_id):
    url = "https://www.meta.ai/"
    try:
        webbrowser.open_new_tab(url)
        print(f"  Открыл вкладку для {task_id}")
        return True
    except Exception as e:
        print(f"  Ошибка браузера: {e}")
        return False

def get_task_prompt(task_id):
    prompts = {
        "TASK_001": "Читаю SHVEYA.md + PLAN_V5 раздел 5. TASK_001 ER-модель 20 сущностей + Knowledge Graph. Order 1:N Garment, Garment 1:N EstimateVersion, Garment 1:N Photo, Order 1:2 DeliveryLeg. Обнови KNOWLEDGE_GRAPH.md + schema_v1_draft.sql",
        "TASK_002": "Читаю SHVEYA.md + SOP Ф0.10. TASK_002 State Machine 8 шагов NEW-DELIVERED + 14 исключений курьера таблица",
        "TASK_003": "TASK_003 Event Log idempotency_key + Price Lock EstimateVersion v1/v2",
        "TASK_004": "TASK_004 DDL для b2.medium PostgreSQL SSOT",
        "TASK_005": "TASK_005 docker-compose для гранта 10к b2.medium",
    }
    return prompts.get(task_id, f"Начинаем {task_id}")

def main():
    print("ШВЕЯМОЗГ Tab Orchestrator — как Claude Code открывает вкладки")
    tasks = [
        ('TASK_001', 'ER-модель 20 сущностей'),
        ('TASK_002', 'State Machine + 14 исключений'),
        ('TASK_003', 'Event Log + Price Lock'),
        ('TASK_004', 'DDL для b2.medium'),
        ('TASK_005', 'docker-compose для гранта'),
        ('TASK_006', 'SOP чеклисты QR'),
        ('TASK_007', 'Concierge MVP без сервера'),
    ]
    print(f"Найдено задач: {len(tasks)}")
    input("Enter чтобы начать открывать вкладки как Claude Code...")

    for tid, desc in tasks:
        print(f"\n--- {tid} ---")
        prompt = get_task_prompt(tid)
        if copy_to_clipboard(prompt):
            print(f"  Промпт скопирован ({len(prompt)} симв)")
        open_new_terminal(tid)
        time.sleep(0.5)
        open_new_browser_tab(tid)
        time.sleep(0.5)
        print(f"  В новой вкладке нажми Ctrl+V и работай только над {tid}")
        input(f"  Enter когда {tid} DONE для следующей...")

    print("\nВсе вкладки открыты как в Claude Code!")

if __name__ == "__main__":
    main()
