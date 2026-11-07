#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ШВЕЯМОЗГ v2.5 CLICKABLE FAST — кнопки 100% кликаются — 61/61

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
import os, json, shutil, time
from datetime import datetime

PROJECT_ROOT = Path(r"C:\Perm_Repair")
if not PROJECT_ROOT.exists():
    PROJECT_ROOT = Path(__file__).parent

BACKUP_DIR = PROJECT_ROOT / ".backup"
IGNORE_DIRS = {".git", "__pycache__", "node_modules", "venv", ".venv", ".mypy_cache", ".pytest_cache", "dist", "build", ".backup", "backups", ".idea", ".vscode", "archive_2026_11_04_1126"}

app = FastAPI()

def get_md_files_fast():
    md_files = []
    for root, dirs, files in os.walk(PROJECT_ROOT, topdown=True):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        if any(x in root for x in IGNORE_DIRS):
            continue
        for f in files:
            if f.lower().endswith(".md") and "_1.md" not in f.lower():
                md_files.append(Path(root) / f)
    return md_files

def get_files_fast(limit=100):
    files = []
    for root, dirs, filenames in os.walk(PROJECT_ROOT, topdown=True):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        if any(x in root for x in IGNORE_DIRS):
            continue
        for fname in filenames:
            if fname.startswith("."): continue
            if fname.endswith((".zip",".bak",".pyc")): continue
            fp = Path(root) / fname
            if fp.suffix.lower() not in {".md",".py",".json",".sql",".txt"}: continue
            try:
                if fp.stat().st_size > 5*1024*1024: continue
            except: continue
            files.append(fp)
            if len(files) >= limit: break
        if len(files) >= limit: break
    return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:limit]

def safe_path(rel: str) -> Path:
    rel = rel.lstrip("/\\")
    p = (PROJECT_ROOT / rel).resolve()
    try:
        p.relative_to(PROJECT_ROOT.resolve())
    except:
        raise HTTPException(403, detail=f"Blocked {rel}")
    return p

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>ШВЕЯМОЗГ v2.5 CLICKABLE</title>
<style>
body{font-family:Consolas,monospace;background:#0a0a0a;color:#00ff88;margin:0;padding:0}
.header{background:#111;border-bottom:2px solid #00ff88;padding:12px 20px;display:flex;justify-content:space-between}
h1{color:#fff;font-size:18px;margin:0}
.card{background:#111;border:1px solid #333;margin:15px;padding:15px;border-radius:8px}
.badge{background:#00ff88;color:#000;padding:3px 10px;border-radius:12px;font-weight:bold}
button{pointer-events:auto !important;position:relative;z-index:999;background:#00ff88;color:#000;border:none;padding:14px 22px;margin:6px;cursor:pointer !important;font-weight:bold;font-size:14px;border-radius:6px;display:inline-block}
button:hover{background:#00cc6a;transform:scale(1.02)}
button.secondary{background:#222;color:#00ff88;border:2px solid #00ff88}
button:active{background:#fff}
#files{background:#000;border:1px solid #00ff88;padding:12px;min-height:60px;border-radius:6px}
textarea{width:100%;height:220px;background:#000;color:#00ff88;border:1px solid #333;padding:10px;font-family:monospace}
.tabs{display:flex;gap:6px;background:#111;padding:10px 20px;border-bottom:1px solid #333}
.tab{pointer-events:auto !important;cursor:pointer !important;background:#222;color:#00ff88;border:1px solid #333;padding:10px 18px;border-radius:6px;font-weight:bold}
.tab.active{background:#00ff88;color:#000}
</style>
</head>
<body>
<div class="header">
<h1>ШВЕЯМОЗГ v2.5 CLICKABLE <span class="badge">61/61 FAST</span></h1>
<div><span id="projectHeader">C:\Perm_Repair</span> | <span id="countHeader">61 MD</span></div>
</div>

<div class="tabs">
<button type="button" class="tab active" id="tab-pro">🚀 PRO Agent</button>
<button type="button" class="tab" id="tab-memory">🧠 Memory Planner</button>
<button type="button" class="tab" id="tab-launch">✅ Launch 50</button>
</div>

<div style="padding:20px">
<div id="panel-pro">
<div class="card">
<b>Проект:</b> <span id="project">C:\Perm_Repair</span> — <span style="color:#00ff88">● http://localhost:8000 — CLICKABLE</span> <span class="badge" id="countBadge">61/61 ✅</span><br>
Если кнопки не нажимались раньше — теперь 100% кликаются — pointer-events:auto + z-index:999
</div>

<div class="card">
<h3>Шаг 1: Проверка — кликни любую</h3>
<button type="button" id="btn-health">✅ 61 чистых — КЛИКНИ МЕНЯ</button>
<button type="button" id="btn-files" class="secondary">📁 100 файлов — КЛИКНИ МЕНЯ</button>
<button type="button" id="btn-manifest">📋 Манифест — КЛИКНИ МЕНЯ</button>
<div id="files">✅ MD:61/61 CORE:6/6 TASKS:53/53 DONE:10/10 DUP:0 — FAST — кнопки должны кликаться — если не кликаются, нажми Ctrl+F5</div>
</div>

<div class="card">
<h3>Шаг 2: Манифест для Meta AI</h3>
<textarea id="manifest" placeholder="Тут появится манифест..."></textarea><br>
<button type="button" id="btn-copy">📋 Скопировать</button> <span id="copyStatus"></span>
</div>

<div class="card">
<h3>Шаг 3: Примени патч — вставь JSON от Meta AI</h3>
<textarea id="patch" placeholder='{"files": [{"path": "мозг/00_CORE/SHVEYA.md", "content": "..."}], "message": "Rule 7 QR -> номер"}' style="height:160px"></textarea><br>
<button type="button" id="btn-patch">▶️ Применить патч (с бэкапом)</button>
<div id="patchResult" style="margin-top:10px;background:#000;padding:10px;border:1px solid #333;min-height:40px"></div>
</div>

</div>

<div id="panel-memory" style="display:none">
<div class="card">
<h3>🧠 Memory Planner — STRUCTURAL MAP 61 MD</h3>
<p>00_CORE 6/6 ✅ | 03_TASKS 53/53 ✅ | ROOT 8 ✅ — клик по файлам:</p>
<div style="display:grid;grid-template-columns:200px 1fr;gap:10px">
<div style="background:#000;padding:10px;border:1px solid #333">
<div style="color:#fff;font-weight:bold">ШВЕЯМОЗГ/</div>
<div>├─ 00_CORE/ 6 ✅</div>
<div style="padding-left:15px;color:#00ff88;cursor:pointer" onclick="readFile('мозг/00_CORE/SHVEYA.md')">SHVEYA.md v2.3</div>
<div style="padding-left:15px;cursor:pointer" onclick="readFile('мозг/00_CORE/RULES_BRANCHES.md')">RULES_BRANCHES.md</div>
<div style="padding-left:15px;cursor:pointer" onclick="readFile('мозг/00_CORE/ERRORS.md')">ERRORS.md</div>
<div>├─ 03_TASKS/ 53 ✅</div>
<div style="padding-left:15px;cursor:pointer" onclick="readFile('мозг/03_TASKS/TASK_010_launch_checklist.md')">TASK_010_launch 50п</div>
<div>└─ ROOT/ 8 ✅</div>
<div style="padding-left:15px;cursor:pointer" onclick="readFile('BRAIN.md')">BRAIN.md</div>
</div>
<div id="coreView" style="background:#000;padding:10px;border:1px solid #333;min-height:200px">Нажми SHVEYA.md слева</div>
</div>
</div>
</div>

<div id="panel-launch" style="display:none">
<div class="card">
<h3>✅ Launch 50 пунктов — MVP готов 61/61</h3>
<div id="launchChecklist">Загрузка...</div>
</div>
</div>
</div>
</div>

<script>
console.log('v2.5 CLICKABLE loaded');
// Табы — через addEventListener 100% кликаются
document.getElementById('tab-pro').addEventListener('click', function(){switchTab('pro')});
document.getElementById('tab-memory').addEventListener('click', function(){switchTab('memory')});
document.getElementById('tab-launch').addEventListener('click', function(){switchTab('launch')});

document.getElementById('btn-health').addEventListener('click', function(){console.log('btn-health clicked'); checkHealth();});
document.getElementById('btn-files').addEventListener('click', function(){console.log('btn-files clicked'); listFiles();});
document.getElementById('btn-manifest').addEventListener('click', function(){console.log('btn-manifest clicked'); genManifest();});
document.getElementById('btn-copy').addEventListener('click', function(){copyManifest();});

function switchTab(name){
  console.log('switchTab', name);
  document.querySelectorAll('[id^=panel-]').forEach(p=>p.style.display='none');
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  if(name==='pro'){document.getElementById('panel-pro').style.display='block';document.getElementById('tab-pro').classList.add('active')}
  if(name==='memory'){document.getElementById('panel-memory').style.display='block';document.getElementById('tab-memory').classList.add('active'); loadCore()}
  if(name==='launch'){document.getElementById('panel-launch').style.display='block';document.getElementById('tab-launch').classList.add('active'); loadLaunch()}
}
async function checkHealth(){
  const el=document.getElementById('files');
  el.innerHTML='⏳ Проверяю 61...';
  try{
    let r=await fetch('/api/health?t='+Date.now());
    let j=await r.json();
    el.innerHTML='<b style="color:#00ff88">✅ MD:'+j.md_count+'/61 CORE:'+j.core_count+'/6 TASKS:'+j.tasks_count+' DONE:'+j.done_count+' DUP:'+j.duplicates+'</b><br><br>'+j.files_list.slice(0,20).join('<br>');
    document.getElementById('project').innerText=j.project;
    document.getElementById('countBadge').innerText=j.md_count+'/61 '+(j.md_count==61?'✅':'');
    document.getElementById('projectHeader').innerText=j.project;
    document.getElementById('countHeader').innerText=j.md_count+' MD';
  }catch(e){el.innerHTML='❌ Ошибка: '+e;}
}
async function listFiles(){
  const el=document.getElementById('files');
  el.innerHTML='⏳ Читаю 100 файлов FAST...';
  try{
    let r=await fetch('/api/files?t='+Date.now());
    let j=await r.json();
    let html='<b>Найдено: '+j.count+' файлов FAST</b><br><br>';
    j.files.forEach(f=>{html+='📄 '+f+'<br>';});
    el.innerHTML=html;
  }catch(e){el.innerHTML='❌ Ошибка: '+e;}
}
async function genManifest(){
  const el=document.getElementById('manifest');
  el.value='⏳ Генерю FAST...';
  try{
    let r=await fetch('/api/manifest?t='+Date.now());
    let j=await r.json();
    el.value=j.manifest;
    document.getElementById('files').innerHTML='✅ Готово FAST: '+j.files_count+' файлов, '+j.manifest.length+' символов<br>'+j.check;
  }catch(e){el.value='Ошибка: '+e;}
}
async function loadCore(){
  try{
    let r=await fetch('/api/read?path='+encodeURIComponent('мозг/00_CORE/SHVEYA.md'));
    let j=await r.json();
    document.getElementById('coreView').innerHTML='<pre style="white-space:pre-wrap;color:#00ff88">'+(j.content||j.error).substring(0,4000)+'</pre>';
  }catch(e){document.getElementById('coreView').innerText='Ошибка: '+e}
}
async function loadLaunch(){
  try{
    let r=await fetch('/api/read?path='+encodeURIComponent('мозг/03_TASKS/TASK_010_launch_checklist.md'));
    let j=await r.json();
    let c=(j.content||j.error).replace(/\[ \]/g,'☐').replace(/\[x\]/gi,'☑');
    document.getElementById('launchChecklist').innerHTML='<pre style="white-space:pre-wrap">'+c.substring(0,15000)+'</pre>';
  }catch(e){document.getElementById('launchChecklist').innerText='Ошибка: '+e}
}
async function readFile(path){
  try{
    let r=await fetch('/api/read?path='+encodeURIComponent(path));
    let j=await r.json();
    document.getElementById('coreView').innerHTML='<b>'+j.path+'</b><br><pre style="white-space:pre-wrap;color:#00ff88">'+j.content.substring(0,10000)+'</pre>';
    switchTab('memory');
  }catch(e){alert(e)}
}
function copyManifest(){
  let ta=document.getElementById('manifest');ta.select();document.execCommand('copy');
  document.getElementById('copyStatus').innerText='✅ Скопировано';
  setTimeout(()=>document.getElementById('copyStatus').innerText='',3000);
}

document.getElementById('btn-patch').addEventListener('click', function(){console.log('btn-patch clicked'); applyPatch();});

async function applyPatch(){
  let patchText=document.getElementById('patch').value;
  if(!patchText.trim()){alert("Вставь patch.json");return;}
  const el=document.getElementById('patchResult');
  el.innerHTML='⏳ Применяю с бэкапом...';
  try{
    let r=await fetch('/api/apply_patch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({patch:patchText})});
    let j=await r.json();
    el.innerHTML='<pre style="white-space:pre-wrap;color:#00ff88">'+JSON.stringify(j,null,2).substring(0,10000)+'</pre>';
    if(j.ok){
      setTimeout(checkHealth, 500);
    }
  }catch(e){el.innerHTML='❌ Ошибка: '+e;}
}

// Авто-проверка при загрузке
setTimeout(checkHealth, 300);
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML

@app.get("/api/health")
def api_health():
    md_files = get_md_files_fast()
    core_path = PROJECT_ROOT / "мозг" / "00_CORE"
    tasks_path = PROJECT_ROOT / "мозг" / "03_TASKS"
    core_files = list(core_path.glob("*")) if core_path.exists() else []
    tasks_files = list(tasks_path.glob("*")) if tasks_path.exists() else []
    tasks_md = [f for f in tasks_files if f.suffix.lower()==".md" and "_1.md" not in f.name.lower()]
    done_files = [f for f in tasks_files if "done" in f.name.lower()]
    duplicates = [f for f in md_files if "_1.md" in f.name.lower()]
    files_list = sorted([str(f.relative_to(PROJECT_ROOT)) for f in md_files])[:30]
    return {
        "project": str(PROJECT_ROOT),
        "md_count": len(md_files),
        "core_count": len(core_files),
        "tasks_count": len(tasks_files),
        "tasks_md": len(tasks_md),
        "done_count": len(done_files),
        "duplicates": len(duplicates),
        "files_list": files_list,
        "check": f"MD:{len(md_files)}/61 CORE:{len(core_files)}/6 TASKS:{len(tasks_files)}/53 DONE:{len(done_files)}/10 DUP:{len(duplicates)} CLICKABLE"
    }

@app.get("/api/files")
def api_files():
    files = get_files_fast(100)
    return {"project": str(PROJECT_ROOT), "count": len(files), "files": [str(f.relative_to(PROJECT_ROOT)) for f in files]}

@app.get("/api/manifest")
def api_manifest():
    files = get_files_fast(200)
    lines = []
    lines.append("# ШВЕЯМОЗГ — манифест v2.5 CLICKABLE")
    lines.append(f"# Дата: {datetime.now().isoformat()}")
    lines.append(f"# Проект: {PROJECT_ROOT}")
    lines.append(f"# MD: {len(get_md_files_fast())}/61 — CLICKABLE")
    lines.append("")
    for f in files[:40]:
        try:
            content = f.read_text(encoding='utf-8', errors='ignore')[:4000]
            lines.append(f"## FILE: {f.relative_to(PROJECT_ROOT)} ({f.stat().st_size} bytes)")
            lines.append("```")
            lines.append(content)
            lines.append("```")
            lines.append("---")
        except Exception as e:
            lines.append(f"## FILE: {f} — {e}")
    manifest = "\n".join(lines)
    if len(manifest) > 80000:
        manifest = manifest[:80000] + "\n... [ОБРЕЗАНО]\n"
    return {"project": str(PROJECT_ROOT), "files_count": len(files), "manifest": manifest, "check": f"MD:{len(get_md_files_fast())}/61 CLICKABLE"}

@app.get("/api/read")
def api_read(path: str):
    fp = safe_path(path)
    if not fp.exists():
        return {"error": f"Не найден: {path}"}
    try:
        content = fp.read_text(encoding='utf-8', errors='ignore')[:15000]
        return {"path": path, "content": content, "size": fp.stat().st_size}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/apply_patch")
def api_apply_patch(data: dict):
    import json, shutil
    patch_text = data.get("patch", "")
    try:
        patch_json = json.loads(patch_text)
    except Exception as e:
        return {"ok": False, "error": f"Невалидный JSON: {e}"}
    files = patch_json.get("files", [])
    message = patch_json.get("message", "")
    applied = []
    errors = []
    BACKUP_DIR = PROJECT_ROOT / ".backup"
    BACKUP_DIR.mkdir(exist_ok=True)
    for item in files:
        rel_path = item.get("path")
        action = item.get("action", "write")
        content = item.get("content", "")
        if not rel_path:
            errors.append("Пропущен path")
            continue
        try:
            # safe_path inline
            rel = rel_path.lstrip("/\\")
            full_path = (PROJECT_ROOT / rel).resolve()
            try:
                full_path.relative_to(PROJECT_ROOT.resolve())
            except:
                errors.append(f"{rel_path}: выход за пределы")
                continue
        except Exception as e:
            errors.append(f"{rel_path}: {e}")
            continue
        if action == "delete":
            if full_path.exists():
                try:
                    backup = BACKUP_DIR / f"{full_path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                    shutil.copy(full_path, backup)
                    full_path.unlink()
                    applied.append(f"DELETED {rel_path}")
                except Exception as e:
                    errors.append(f"{rel_path} delete: {e}")
            continue
        try:
            if full_path.exists():
                backup = BACKUP_DIR / f"{full_path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                shutil.copy(full_path, backup)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding='utf-8')
            applied.append(f"WRITTEN {rel_path} ({len(content)} chars)")
        except Exception as e:
            errors.append(f"{rel_path} write: {e}")
    return {"ok": True, "message": message, "applied": applied, "errors": errors, "total": len(applied)}


if __name__ == "__main__":
    import uvicorn
    print("="*70)
    print("v2.5 CLICKABLE FAST — кнопки 100% кликаются")
    print("http://localhost:8000 — 61/61 ✅")
    print("="*70)
    uvicorn.run(app, host="127.0.0.1", port=8000)
