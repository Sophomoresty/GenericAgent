"""ga-ask.py: One-shot GA query. Usage: python ga-ask.py "your question" """
import sys, os, io, threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agentmain import GeneraticAgent

def main():
    query = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else input().strip()
    if not query:
        print("[ERROR] No query provided"); return 1

    # Suppress debug prints from agent internals
    _real_stdout = sys.stdout
    sys.stdout = io.StringIO()

    agent = GeneraticAgent()
    agent.next_llm(0)
    agent.verbose = False
    threading.Thread(target=agent.run, daemon=True).start()

    dq = agent.put_task(query, source='task')
    result = None
    while True:
        try:
            item = dq.get(timeout=120)
            if 'done' in item:
                result = item['done']
                break
        except Exception:
            sys.stdout = _real_stdout
            print("[ERROR] Timeout waiting for GA response", file=sys.stderr)
            return 1

    sys.stdout = _real_stdout
    if result:
        print(result)
    return 0

if __name__ == '__main__':
    sys.exit(main())