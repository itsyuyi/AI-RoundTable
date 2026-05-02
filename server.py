#!/usr/bin/env python3
"""
AI ROUNDTABLE (睿思圆桌) — Web Server
零依赖, 纯标准库 + 可选 OpenAI

启动: python server.py [--port 8080]
"""

import json
import os
import sys
import time
import uuid
import re
import threading
import queue
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# ─── Persona 研究引擎 ────────────────────────────────────────
from persona_researcher import (
    BUILTIN_KNOWLEDGE, get_persona, get_all_domains, get_all_tags
)

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# ══════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════

ROOT = Path(__file__).parent
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)

CUSTOM_PERSONAS = {}  # 用户自定义人物
SESSIONS = {}         # 辩论会话
DATA_FILE = ROOT / "custom_personas.json"

# 加载持久化自定义人物
if DATA_FILE.exists():
    try:
        CUSTOM_PERSONAS = json.loads(DATA_FILE.read_text())
    except:
        pass

def save_custom():
    DATA_FILE.write_text(json.dumps(CUSTOM_PERSONAS, ensure_ascii=False, indent=2))

# ══════════════════════════════════════════════════════════════
# DEBATE SESSION
# ══════════════════════════════════════════════════════════════

MODERATOR_PROMPT = """你是一场跨领域圆桌对话的主持人。以下是各位参与者的发言摘要，请完成综合报告：

1. 每位参与者的核心立场（一句话）
2. 共识区域：哪些观点大家一致
3. 根本分歧：核心矛盾是什么
4. 跨界启发：这些来自不同领域的思维碰撞产生了什么独特洞见？
5. 综合建议：分阶段的行动路径
6. 待验证假设：哪些关键信息缺失会影响决策

格式简洁，用中文。"""

class RoundtableSession:
    def __init__(self, session_id, topic, persona_ids, mode="圆桌讨论"):
        self.session_id = session_id
        self.topic = topic
        self.persona_ids = persona_ids
        self.mode = mode  # 圆桌讨论 / 跨界头脑风暴 / 关键决策
        self.event_queue = queue.Queue()
        self.status = "pending"
        self.created_at = datetime.now().isoformat()
        self.events = []
        self.r1_results = {}
        self.r2_results = {}
        self.moderator_report = ""

    def emit(self, event_type, data):
        event = {"type": event_type, "data": data, "timestamp": datetime.now().isoformat()}
        self.events.append(event)
        self.event_queue.put(json.dumps(event, ensure_ascii=False))

    def call_llm(self, system, prompt, max_tokens=600):
        api_key = os.environ.get("BOARDROOM_API_KEY",
                  os.environ.get("OPENAI_API_KEY", ""))
        if api_key and HAS_OPENAI:
            base_url = os.environ.get("BOARDROOM_BASE_URL",
                       os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"))
            model = os.environ.get("BOARDROOM_MODEL", "gpt-4o")
            client = OpenAI(api_key=api_key, base_url=base_url)
            for attempt in range(3):
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.85, max_tokens=max_tokens)
                    return resp.choices[0].message.content.strip()
                except Exception as e:
                    if attempt == 2: return f"[错误: {e}]"
                    time.sleep(2 ** attempt)
        return self._simulate(system, prompt)

    def _simulate(self, system, prompt):
        import random
        snips = [
            "让我从第一性原理来分析这个问题。核心矛盾不在于表面选择，而在于底层假设是否成立。",
            "说实话，这个问题本身的框架就有问题。你不是在做真问题，是在做伪选择。",
            "从客户角度看，有一个被所有人忽略的关键——用户的真实需求是什么？",
            "寒冬随时会来。我建议先把根据地做扎实，活着比什么都重要。",
            "我不同意前面的看法。市场竞争不是请客吃饭，是用资源砸出来的。",
            "这件事的本质是什么？拆开来看就三个物理量——价值、成本、留存。",
            "五年之后这件事会变成什么样？短期对错不重要，长期趋势决定生死。",
            "我的核心建议很简单：先做减法，再做加法。你现在做的事太多了。",
            "与其争论，不如用数据说话。拿一个小规模实验结果来验证假设。",
            "这个方向有巨大想象空间，但你认真算过单位经济模型吗？",
        ]
        return " ".join(random.sample(snips, min(3, len(snips))))

    def _get_personas(self):
        all_p = {**BUILTIN_KNOWLEDGE, **CUSTOM_PERSONAS}
        # Build a reverse map: persona["id"] -> (key, persona)
        by_id = {}
        for key, p in all_p.items():
            by_id[p.get("id", key)] = (key, p)
        result = {}
        for pid in self.persona_ids:
            if pid in by_id:
                result[pid] = by_id[pid][1]
        return result

    def run(self):
        selected = self._get_personas()
        if len(selected) < 2:
            self.emit("error", {"message": "至少需要 2 位参与者"})
            self.status = "error"
            return

        self.status = "running"
        self.emit("session_start", {
            "session_id": self.session_id, "topic": self.topic, "mode": self.mode,
            "personas": [{"id": pid, "name": p["name"], "avatar": p["avatar"],
                          "color": p["color"], "domain": p.get("domain","")}
                         for pid, p in selected.items()],
        })

        # Round 1
        self.emit("round_start", {"round": 1, "title": "独立阐述", "description": f"每位参与者从自己的领域和思维框架出发，独立阐述观点"})
        lock = threading.Lock()
        threads = []
        for pid, p in selected.items():
            t = threading.Thread(target=self._r1, args=(pid, p, lock))
            t.start(); threads.append(t)
        for t in threads: t.join()
        self.emit("round_end", {"round": 1})

        # Round 2
        self.emit("round_start", {"round": 2, "title": "跨界对话", "description": "参与者互相质询、补充，产生跨界碰撞"})
        threads = []
        for pid, p in selected.items():
            t = threading.Thread(target=self._r2, args=(pid, p, selected, lock))
            t.start(); threads.append(t)
        for t in threads: t.join()
        self.emit("round_end", {"round": 2})

        # Round 3: Moderator
        self.emit("round_start", {"round": 3, "title": "主持人综评", "description": "综合跨界洞见，总结共识与分歧，给出行动建议"})
        views = ""
        for pid, p in selected.items():
            s = self.r1_results[pid][:200] + ("…" if len(self.r1_results[pid])>200 else "")
            views += f"\n### {p['name']}（{p.get('domain','')}）\n{s}\n"
        self.moderator_report = self.call_llm(MODERATOR_PROMPT, f"议题：{self.topic}\n{views}", 800)
        self.emit("moderator_report", {"content": self.moderator_report})
        self.emit("round_end", {"round": 3})

        self.status = "completed"
        self.emit("session_complete", {"session_id": self.session_id})

    def _r1(self, pid, p, lock):
        self.emit("persona_thinking", {"persona_id": pid, "name": p["name"]})
        prompt = f"你正在参加一场跨领域圆桌对话。议题是：\n\n{self.topic}\n\n请从你的领域和专业视角出发，发表你的核心观点。为什么你这么认为？请给出具体的理由。"
        resp = self.call_llm(p.get("system_prompt", ""), prompt, 500)
        with lock: self.r1_results[pid] = resp
        self.emit("persona_response", {"persona_id": pid, "name": p["name"], "avatar": p["avatar"],
                     "color": p["color"], "domain": p.get("domain",""), "content": resp, "round": 1})

    def _r2(self, pid, p, selected, lock):
        self.emit("persona_thinking", {"persona_id": pid, "name": p["name"]})
        others = ""
        for opid, oresp in self.r1_results.items():
            if opid != pid:
                on = selected[opid]["name"]
                s = oresp[:180] + ("…" if len(oresp)>180 else "")
                others += f"【{on}({selected[opid].get('domain','')})】{s}\n\n"
        prompt = f"原始议题：{self.topic}\n\n其他参与者观点：\n{others}\n请回应：你同意谁？反对谁？从你的领域出发，他们忽略了什么？你们的领域视角能否产生新的组合洞见？"
        resp = self.call_llm(p.get("system_prompt", ""), prompt, 500)
        with lock: self.r2_results[pid] = resp
        self.emit("persona_response", {"persona_id": pid, "name": p["name"], "avatar": p["avatar"],
                     "color": p["color"], "domain": p.get("domain",""), "content": resp, "round": 2})


# ══════════════════════════════════════════════════════════════
# HTTP HANDLER
# ══════════════════════════════════════════════════════════════

HTML = None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html, code=200):
        body = html.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _sse(self, sid):
        self.send_response(200)
        for h in ["Content-Type","Cache-Control","Connection","Access-Control-Allow-Origin","X-Accel-Buffering"]:
            self.send_header(h, "text/event-stream" if h=="Content-Type" else "no-cache" if h=="Cache-Control" else "keep-alive" if h=="Connection" else "*" if "Origin" in h else "no")
        self.end_headers()
        s = SESSIONS.get(sid)
        if not s:
            self.wfile.write(f"data: {json.dumps({'type':'error','data':{'message':'Session not found'}})}\n\n".encode())
            return
        for e in s.events:
            self.wfile.write(f"data: {json.dumps(e,ensure_ascii=False)}\n\n".encode())
            self.wfile.flush()
        while s.status in ("pending","running"):
            try:
                d = s.event_queue.get(timeout=30)
                self.wfile.write(f"data: {d}\n\n".encode())
                self.wfile.flush()
            except queue.Empty:
                self.wfile.write(b": hb\n\n"); self.wfile.flush()
        while not s.event_queue.empty():
            try:
                d = s.event_queue.get_nowait()
                self.wfile.write(f"data: {d}\n\n".encode()); self.wfile.flush()
            except: break

    def do_OPTIONS(self):
        self.send_response(204)
        for h in ["Access-Control-Allow-Origin","Access-Control-Allow-Methods","Access-Control-Allow-Headers"]:
            self.send_header(h, "*" if "Origin" in h else "GET,POST,DELETE,OPTIONS" if "Methods" in h else "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/","/index.html"): self._html(HTML)
        elif path == "/api/personas":
            all_p = {**BUILTIN_KNOWLEDGE, **CUSTOM_PERSONAS}
            result = []
            for pid, p in all_p.items():
                real_id = p.get("id", pid)
                result.append({"id":real_id,"name":p["name"],"title":p["title"],"avatar":p["avatar"],
                    "color":p["color"],"domain":p.get("domain",""),"tags":p.get("tags",[]),
                    "framework":p.get("framework",""),"is_custom":pid in CUSTOM_PERSONAS})
            self._json(result)
        elif path == "/api/domains":
            domains = {}
            for p in {**BUILTIN_KNOWLEDGE, **CUSTOM_PERSONAS}.values():
                d = p.get("domain","综合")
                domains[d] = domains.get(d, 0) + 1
            self._json([{"name":k,"count":v} for k,v in sorted(domains.items())])
        elif path == "/api/tags":
            tags = {}
            for p in {**BUILTIN_KNOWLEDGE, **CUSTOM_PERSONAS}.values():
                for t in p.get("tags",[]): tags[t] = tags.get(t,0)+1
            self._json([{"name":k,"count":v} for k,v in sorted(tags.items(),key=lambda x:-x[1])])
        elif path == "/api/sessions":
            sl = [{"session_id":si,"topic":s.topic,"status":s.status,"mode":s.mode,
                   "created_at":s.created_at,"persona_count":len(s.persona_ids)} for si,s in SESSIONS.items()]
            self._json(sorted(sl, key=lambda x:x["created_at"], reverse=True))
        elif path.startswith("/api/stream/"):
            self._sse(path.split("/")[-1])
        else: self._json({"error":"Not found"},404)

    def do_POST(self):
        path = urlparse(self.path).path
        cl = int(self.headers.get("Content-Length",0))
        data = json.loads(self.rfile.read(cl)) if cl else {}

        if path == "/api/roundtable":
            topic = data.get("topic","").strip()
            pids = data.get("persona_ids",[])
            mode = data.get("mode","圆桌讨论")
            if not topic: return self._json({"error":"topic required"},400)
            if len(pids)<2: return self._json({"error":"至少选择 2 位参与者"},400)
            sid = f"rt_{uuid.uuid4().hex[:8]}"
            ses = RoundtableSession(sid, topic, pids, mode)
            SESSIONS[sid] = ses
            threading.Thread(target=ses.run).start()
            self._json({"session_id":sid,"status":"started"})

        elif path == "/api/personas":
            pid = data.get("id","").strip().lower()
            name = data.get("name","").strip()
            title = data.get("title","").strip()
            avatar = data.get("avatar","👤").strip()
            color = data.get("color","#6366f1").strip()
            domain = data.get("domain","综合").strip()
            tags = data.get("tags",[])
            framework = data.get("framework","").strip()
            system = data.get("system","").strip()
            if not pid or not name or not title:
                return self._json({"error":"id,name,title required"},400)
            if pid in BUILTIN_KNOWLEDGE:
                return self._json({"error":f"不能覆盖预置人物 {pid}"},400)
            CUSTOM_PERSONAS[pid] = {"id":pid,"name":name,"title":title,"avatar":avatar,
                "color":color,"domain":domain,"tags":tags,"framework":framework,
                "system_prompt":system or f"你是 {name}，{title}。每次发言3-5句中文。",
                "bio":"","key_ideas":[]}
            save_custom()
            self._json({"ok":True,"persona":CUSTOM_PERSONAS[pid]})

        elif path == "/api/research":
            name = data.get("name","").strip()
            if not name: return self._json({"error":"name required"},400)
            persona = get_persona(name)
            if persona:
                self._json({"found":True,"persona":persona})
            else:
                self._json({"found":False,"message":f"未找到 {name} 的信息，请尝试手动创建或使用更完整的名称"})

        else: self._json({"error":"Not found"},404)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/api/personas/"):
            pid = path.split("/")[-1]
            if pid in BUILTIN_KNOWLEDGE: return self._json({"error":"不能删除预置人物"},400)
            if pid in CUSTOM_PERSONAS:
                del CUSTOM_PERSONAS[pid]; save_custom()
                self._json({"ok":True})
            else: self._json({"error":"Not found"},404)
        elif path.startswith("/api/sessions/"):
            sid = path.split("/")[-1]
            if sid in SESSIONS:
                del SESSIONS[sid]; self._json({"ok":True})
            else: self._json({"error":"Not found"},404)
        else: self._json({"error":"Not found"},404)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    global HTML
    hp = ROOT / "static" / "index.html"
    if not hp.exists(): print("❌ static/index.html not found"); sys.exit(1)
    HTML = hp.read_text(encoding="utf-8")
    port = int(sys.argv[1]) if len(sys.argv)>1 else 8080
    srv = HTTPServer(("0.0.0.0",port), Handler)
    print(f"""
╔══════════════════════════════════════════════════════════╗
║       🏛️  AI ROUNDTABLE  睿思圆桌                    ║
║                                                        ║
║  预置 {len(BUILTIN_KNOWLEDGE)} 位人物 · {len(get_all_domains())} 个领域 · {len(get_all_tags())} 个标签       ║
║  访问: http://localhost:{port}                         ║
║  Ctrl+C 停止                                           ║
╚══════════════════════════════════════════════════════════╝
""")
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\n👋 圆桌休会"); srv.shutdown()

if __name__ == "__main__":
    main()
