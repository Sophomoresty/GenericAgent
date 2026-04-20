"""
GA 一键启动器 — 无终端窗口
启动 qtapp + stapp2(Streamlit) + desktop_pet_v2
双击此文件即可，或: pythonw.exe start_all.pyw
"""
import os, sys, subprocess, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHONW = os.path.join(SCRIPT_DIR, '.venv', 'Scripts', 'pythonw.exe')
PYTHON  = os.path.join(SCRIPT_DIR, '.venv', 'Scripts', 'python.exe')
NO_WIN = subprocess.CREATE_NO_WINDOW  # 0x08000000

def start_qtapp():
    """Qt GUI — pythonw 启动，无终端"""
    p = subprocess.Popen(
        [PYTHONW, os.path.join(SCRIPT_DIR, 'frontends', 'qtapp.py')],
        cwd=SCRIPT_DIR, creationflags=NO_WIN
    )
    print(f"[OK] qtapp started (PID {p.pid})")
    return p

def start_streamlit():
    """Streamlit Web GUI — CREATE_NO_WINDOW 隐藏终端"""
    st_script = os.path.join(SCRIPT_DIR, 'frontends', 'stapp2.py')
    p = subprocess.Popen(
        [PYTHON, '-m', 'streamlit', 'run', st_script,
         '--server.headless', 'true',
         '--browser.gatherUsageStats', 'false'],
        cwd=SCRIPT_DIR, creationflags=NO_WIN
    )
    print(f"[OK] streamlit started (PID {p.pid})")
    return p

def start_desktop_pet():
    """桌面宠物 — pythonw 启动，无终端"""
    p = subprocess.Popen(
        [PYTHONW, os.path.join(SCRIPT_DIR, 'frontends', 'desktop_pet_v2.pyw')],
        cwd=SCRIPT_DIR, creationflags=NO_WIN
    )
    print(f"[OK] desktop_pet started (PID {p.pid})")
    return p

if __name__ == '__main__':
    procs = []
    try:
        procs.append(start_qtapp())
        time.sleep(1)
        procs.append(start_streamlit())
        time.sleep(1)
        procs.append(start_desktop_pet())
        print(f"\n✅ All {len(procs)} frontends launched (no terminal windows)")
    except Exception as e:
        print(f"[ERROR] {e}")