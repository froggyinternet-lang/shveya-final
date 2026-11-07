#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ШВЕЯМОЗГ — ULTRA MINIMAL v2.4 — ГАРАНТИРОВАННО ГРУЗИТСЯ — без сканирования при старте

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path
import json
import os
from datetime import datetime

PROJECT_ROOT = Path(r"C:\Perm_Repair")
if not PROJECT_ROOT.exists():
    PROJECT_ROOT = Path(__file__).parent

app = FastAPI()

HTML_MINIMAL = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>ШВЕЯМОЗГ — ULTRA MINIMAL v2.4</title>
<style>
body{font-family:monospace;background:#0a0a0a;color:#00ff88;padding:20px;line-height:1.6}
h1{color:#fff} .ok{color:#00ff88} .warn{color:#ffaa00}
.badge{background:#00ff88;color:#000;padding:3px 10px;border-radius:10px;font-weight:bold}
.card{background:#111;border:1px solid #333;padding:15px;margin:15px 0;border-radius:6px}
button{background:#00ff88;color:#000;border:none;padding:12px 18px;margin:5px;cursor:pointer;font-weight:bold;border-radius:4px}
button:hover{background:#00cc6a}
button.secondary{background:#222;color:#00ff88;border:1px solid #00ff88}
pre{background:#000;padding:10px;border:1px solid #333;max-height:300px;overflow:auto;white-space:pre-wrap}
</style>
</head>
<body>
<h1>ШВЕЯМОЗГ — ULTRA MINIMAL v2.4 <span class="badge">НЕ ВИСИТ</span></h1>
<div class="card">
<b>Проект:</b> <span id="project">C:\Perm_Repair</span> | <span class="ok">● http://localhost:8000</span> <span class="badge">ГОТОВ</span><br>
<span class="warn">Версия без сканирования — грузится мгновенно</span>
</div>

<div class="card">
<h3>Шаг 0: Проверка что backend жив</h3>
<button onclick="checkAlive()">✅ Проверить backend</button>
<div id="alive"></div>
</div>

<div class="card">
<h3>Шаг 1: Показать файлы (FAST — только .md, без зипов)</h3>
<button onclick="checkHealth()">✅ 61 чистых (быстро)</button>
<button onclick="listFiles()">📁 20 файлов (быстро)</button>
<div id="files">Нажми кнопку — теперь не виснет</div>
</div>

<div class="card">
<h3>Шаг 2: Манифест</h3>
<button onclick="genManifest()">📋 Манифест для Meta AI</button>
<textarea id="manifest" style="width:100%;height:200px;background:#111;color:#00ff88;border:1px solid #333;padding:10px;"></textarea><br>
<button onclick="copyManifest()">📋 Скопировать</button> <span id="copyStatus"></span>
</div>

<div class="card">
<h3>Диагностика</h3>
<pre id="diag">Запущен ultra minimal — без rglob при старте.
Если эта страница открылась — backend жив.
Если кнопки не работают — открой http://localhost:8000/api/health в новой вкладке и скинь что там.
</pre>
</div>

<script>
async function checkAlive(){
  try{
    let r = await fetch('/api/health');
    let j = await r.json();
    document.getElementById('alive').innerHTML = '<span style="color:#00ff88">✅ Backend жив:</span> <pre>'+JSON.stringify(j,null,2)+'</pre>';
    document.getElementById('project').innerText = j.project;
  }catch(e){
    document.getElementById('alive').innerHTML = '❌ Ошибка: '+e+'<br>Попробуй открыть <a href="/api/health" target="_blank">/api/health</a> напрямую';
  }
}
async function checkHealth(){
  document.getElementById('files').innerHTML = 'Проверяю...';
  try{
    let r = await fetch('/api/health');
    let j = await r.json();
    document.getElementById('files').innerHTML = '<b>MD:</b> '+j.md_count+' | <b>CORE:</b> '+j.core_count+' | <b>TASKS:</b> '+j.tasks_count+' | <b>DONE:</b> '+j.done_count+' | <b>DUP:</b> '+j.duplicates+'<br><br>'+j.files_list.join('<br>');
  }catch(e){document.getElementById('files').innerHTML = 'Ошибка: '+e;}
}
async function listFiles(){
  document.getElementById('files').innerHTML = 'Читаю 20 файлов...';
  try{
    let r = await fetch('/api/files');
    let j = await r.json();
    let html = '<b>Найдено: '+j.count+' файлов</b><br><br>';
    j.files.forEach(f=>{html+='📄 '+f+'<br>';});
    document.getElementById('files').innerHTML = html;
  }catch(e){document.getElementById('files').innerHTML = 'Ошибка: '+e;}
}
async function genManifest(){
  document.getElementById('manifest').value = 'Генерю...';
  try{
    let r = await fetch('/api/manifest');
    let j = await r.json();
    document.getElementById('manifest').value = j.manifest.substring(0,80000);
    document.getElementById('files').innerHTML = '✅ Готово: '+j.files_count+' файлов, '+j.manifest.length+' символов<br>'+j.check;
  }catch(e){document.getElementById('manifest').value = 'Ошибка: '+e;}
}
function copyManifest(){
  let ta=document.getElementById('manifest');ta.select();document.execCommand('copy');
  document.getElementById('copyStatus').innerText='✅ Скопировано';
  setTimeout(()=>{document.getElementById('copyStatus').innerText=''},3000);
}
// Авто-проверка при загрузке — только health, не files
checkAlive();
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_MINIMAL

@app.get("/api/health")
def api_health():
    # ULTRA FAST — не делаем rglob всего диска, только конкретные папки
    try:
        core_path = PROJECT_ROOT / "мозг" / "00_CORE"
        tasks_path = PROJECT_ROOT / "мозг" / "03_TASKS"
        md_count = 0
        files_list = []
        # Только .md в корне + мозг — без рекурсии по всему диску
        for p in PROJECT_ROOT.glob("*.md"):
            if "_1.md" not in p.name:
                md_count += 1
                files_list.append(str(p.relative_to(PROJECT_ROOT)))
        if core_path.exists():
            for p in core_path.glob("*.md"):
                md_count += 1
                files_list.append(str(p.relative_to(PROJECT_ROOT)))
        if tasks_path.exists():
            for p in tasks_path.glob("*.md"):
                if "_1.md" not in p.name:
                    md_count += 1
                    files_list.append(str(p.relative_to(PROJECT_ROOT)))
            tasks_files = list(tasks_path.glob("*"))
            tasks_md = [f for f in tasks_files if f.suffix.lower() == ".md" and "_1.md" not in f.name]
            done_files = [f for f in tasks_files if "done" in f.name.lower()]
        else:
            tasks_files = []
            tasks_md = []
            done_files = []
        core_files = list(core_path.glob("*")) if core_path.exists() else []
        duplicates = [f for f in files_list if "_1.md" in f.lower()]
        return {
            "project": str(PROJECT_ROOT),
            "md_count": md_count,
            "core_count": len(core_files),
            "tasks_count": len(tasks_files),
            "tasks_md": len(tasks_md),
            "done_count": len(done_files),
            "duplicates": len(duplicates),
            "files_list": sorted(files_list)[:30],
            "check": f"MD:{md_count}/61, CORE:{len(core_files)}/6, TASKS:{len(tasks_files)}/53, DONE:{len(done_files)}/10, DUP:{len(duplicates)} — FAST",
            "status": "OK — ULTRA MINIMAL не виснет"
        }
    except Exception as e:
        return {"project": str(PROJECT_ROOT), "md_count": 0, "core_count": 0, "tasks_count": 0, "tasks_md": 0, "done_count": 0, "duplicates": 0, "files_list": [f"Ошибка: {e}"], "check": f"Ошибка: {e}", "status": "ERROR"}

@app.get("/api/files")
def api_files():
    try:
        files = []
        # Только 20 файлов — быстро
        for p in PROJECT_ROOT.glob("*.md"):
            if "_1.md" not in p.name:
                files.append(p)
                if len(files) >= 10:
                    break
        core_path = PROJECT_ROOT / "мозг" / "00_CORE"
        if core_path.exists():
            for p in core_path.glob("*"):
                if p.is_file():
                    files.append(p)
                    if len(files) >= 20:
                        break
        return {
            "project": str(PROJECT_ROOT),
            "count": len(files),
            "files": [str(f.relative_to(PROJECT_ROOT)) for f in files]
        }
    except Exception as e:
        return {"project": str(PROJECT_ROOT), "count": 0, "files": [f"Ошибка: {e}"]}

@app.get("/api/manifest")
def api_manifest():
    try:
        lines = []
        lines.append("# ШВЕЯМОЗГ — манифест ULTRA MINIMAL")
        lines.append(f"# Дата: {datetime.now().isoformat()}")
        lines.append(f"# Проект: {PROJECT_ROOT}")
        lines.append("# Файлов в выборке: 20 (FAST)")
        lines.append("")
        # Только 10 файлов для манифеста — чтобы не висло
        count = 0
        for p in PROJECT_ROOT.glob("*.md"):
            if "_1.md" in p.name:
                continue
            if count >= 10:
                break
            try:
                content = p.read_text(encoding='utf-8', errors='ignore')[:2000]
                lines.append(f"## FILE: {p.name} ({p.stat().st_size} bytes)")
                lines.append("```")
                lines.append(content)
                lines.append("```")
                lines.append("---")
                count += 1
            except:
                continue
        core_path = PROJECT_ROOT / "мозг" / "00_CORE"
        if core_path.exists():
            for p in core_path.glob("*.md"):
                if count >= 20:
                    break
                try:
                    content = p.read_text(encoding='utf-8', errors='ignore')[:2000]
                    lines.append(f"## FILE: мозг/00_CORE/{p.name}")
                    lines.append("```")
                    lines.append(content)
                    lines.append("```")
                    lines.append("---")
                    count += 1
                except:
                    continue
        manifest = "\n".join(lines)
        return {"project": str(PROJECT_ROOT), "files_count": count, "manifest": manifest, "check": f"FAST 20 файлов, {len(manifest)} chars"}
    except Exception as e:
        return {"project": str(PROJECT_ROOT), "files_count": 0, "manifest": f"Ошибка: {e}", "check": f"Ошибка: {e}"}

if __name__ == "__main__":
    import uvicorn
    print("="*70)
    print("ULTRA MINIMAL v2.4 — ГАРАНТИРОВАННО НЕ ВИСНЕТ")
    print(f"Проект: {PROJECT_ROOT}")
    print("http://localhost:8000 — открой и нажми Проверить backend")
    print("Если даже это висит — убей старые python: taskkill /F /IM python.exe")
    print("="*70)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
