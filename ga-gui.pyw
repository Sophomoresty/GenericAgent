"""
ga-gui.pyw — GA GUI 启动器, 无终端窗口
启动 Streamlit 服务 + pywebview 桌面窗口
用法: ga gui [--tg] [--qq] [--feishu] [--wecom] [--dingtalk] [--sched]
"""
import webview, threading, subprocess, sys, time, os, ctypes, atexit, socket, random

WINDOW_WIDTH, WINDOW_HEIGHT = 480, 720

script_dir = os.path.dirname(os.path.abspath(__file__))
frontends_dir = os.path.join(script_dir, "frontends")

def find_free_port(lo=18501, hi=18599):
    ports = list(range(lo, hi+1)); random.shuffle(ports)
    for p in ports:
        try: s = socket.socket(); s.bind(('127.0.0.1', p)); s.close(); return p
        except OSError: continue
    raise RuntimeError(f'No free port in {lo}-{hi}')

def get_screen_size():
    try:
        sw = ctypes.windll.user32.GetSystemMetrics(0)
        sh = ctypes.windll.user32.GetSystemMetrics(1)
        return sw, sh
    except: return 1920, 1080

def start_streamlit(port):
    global proc
    cmd = [sys.executable, "-m", "streamlit", "run", os.path.join(frontends_dir, "stapp.py"),
           "--server.port", str(port), "--server.address", "localhost", "--server.headless", "true"]
    kw = {}
    if os.name == 'nt':
        kw['creationflags'] = subprocess.CREATE_NO_WINDOW
    proc = subprocess.Popen(cmd, **kw)
    atexit.register(proc.kill)

def inject(text):
    window.evaluate_js(f"""
        const textarea = document.querySelector('textarea[data-testid="stChatInputTextArea"]');
        if (textarea) {{
            const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
            nativeTextAreaValueSetter.call(textarea, {repr(text)});
            textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
            textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
            setTimeout(() => {{
                const btn = document.querySelector('[data-testid="stChatInputSubmitButton"]');
                if (btn) {{btn.click();console.log('Submitted:', {repr(text)});}}
            }}, 200);
        }}""")

def get_last_reply_time():
    last = window.evaluate_js("""
        const el = document.getElementById('last-reply-time');
        el ? parseInt(el.textContent) : 0;
    """) or 0
    return last or int(time.time())

def idle_monitor():
    last_trigger_time = 0
    while True:
        time.sleep(5)
        try:
            now = time.time()
            if now - last_trigger_time < 120: continue
            last_reply = get_last_reply_time()
            if now - last_reply > 1800:
                print('[Idle Monitor] Detected idle state, injecting task...')
                inject("[AUTO]🤖 用户已经离开超过30分钟，作为自主智能体，请阅读自动化sop，执行自动任务。")
                last_trigger_time = now
        except Exception as e:
            print(f'[Idle Monitor] Error: {e}')

def start_bot(name, script_name):
    proc = subprocess.Popen(
        [sys.executable, os.path.join(frontends_dir, script_name)],
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    atexit.register(proc.kill)
    print(f'[Launch] {name} Bot started')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='GA GUI Launcher')
    parser.add_argument('--tg', action='store_true', help='启动 Telegram Bot')
    parser.add_argument('--qq', action='store_true', help='启动 QQ Bot')
    parser.add_argument('--feishu', '--fs', dest='feishu', action='store_true', help='启动 Feishu Bot')
    parser.add_argument('--wecom', action='store_true', help='启动 WeCom Bot')
    parser.add_argument('--dingtalk', '--dt', dest='dingtalk', action='store_true', help='启动 DingTalk Bot')
    parser.add_argument('--sched', action='store_true', help='启动计划任务调度器')
    parser.add_argument('--llm_no', type=int, default=0, help='LLM编号')
    args = parser.parse_args()

    port = str(find_free_port())
    print(f'[Launch] Using port {port}')
    threading.Thread(target=start_streamlit, args=(port,), daemon=True).start()

    bots = [
        ('Telegram', 'tgapp.py', args.tg),
        ('QQ', 'qqapp.py', args.qq),
        ('Feishu', 'fsapp.py', args.feishu),
        ('WeCom', 'wecomapp.py', args.wecom),
        ('DingTalk', 'dingtalkapp.py', args.dingtalk),
    ]
    for name, script, enabled in bots:
        if enabled:
            start_bot(name, script)
        else:
            print(f'[Launch] {name} Bot not enabled')

    if args.sched:
        scheduler_proc = subprocess.Popen(
            [sys.executable, os.path.join(script_dir, "agentmain.py"), "--reflect",
             os.path.join(script_dir, "reflect", "scheduler.py"), "--llm_no", str(args.llm_no)],
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        atexit.register(scheduler_proc.kill)
        print('[Launch] Task Scheduler started')
    else:
        print('[Launch] Task Scheduler not enabled (--sched)')

    monitor_thread = threading.Thread(target=idle_monitor, daemon=True)
    monitor_thread.start()

    screen_w, screen_h = get_screen_size() if os.name == 'nt' else (1920, 1080)
    x_pos = (screen_w - WINDOW_WIDTH) // 2
    y_pos = (screen_h - WINDOW_HEIGHT) // 2
    time.sleep(2)
    window = webview.create_window(
        title='GenericAgent', url=f'http://localhost:{port}',
        width=WINDOW_WIDTH, height=WINDOW_HEIGHT, x=x_pos, y=y_pos,
        resizable=True, text_select=True)
    webview.start()
