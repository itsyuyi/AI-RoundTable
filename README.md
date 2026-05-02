# 🏛️ AI ROUNDTABLE · 睿思圆桌

**跨领域智识对话平台** — 召集任何时代、任何领域的顶尖头脑，进行圆桌辩论、跨界头脑风暴与关键决策。

---

## ✨ 核心亮点

- **23 位预置人物**：覆盖金融、科技、哲学、医学、经济学等 12 个领域
- **100+ 标签系统**：多维度筛选，快速找到对的人
- **智能研究引擎**：输入人名 → 自动匹配深度人格分析
- **3 轮辩论流程**：独立阐述 → 跨界对话 → 主持人综评
- **3 种对话模式**：圆桌讨论 / 跨界头脑风暴 / 关键决策
- **SSE 实时推流**：辩论过程边思考边呈现
- **自定义人物**：完全自定义任何领域的角色
- **零依赖**：纯 Python 标准库 + 可选 OpenAI API

---

## 🚀 快速启动

```bash
# 1. 启动服务（纯模拟模式，无需 API key）
cd ai-roundtable
python server.py

# 2. 接入真实大模型（可选）
export BOARDROOM_API_KEY=sk-your-key
export BOARDROOM_BASE_URL=https://api.openai.com/v1  # 或 MiMo / DeepSeek
export BOARDROOM_MODEL=gpt-4o
python server.py

# 3. 浏览器打开
open http://localhost:8080
```

---

## 👥 人物矩阵

| 领域 | 人物 |
|------|------|
| 💰 金融投资 | Warren Buffett · Ray Dalio · Charlie Munger |
| 📈 经济学 | John Maynard Keynes · Adam Smith · Milton Friedman |
| 🧠 哲学 | 孔子 · 苏格拉底 · Nietzsche · Karl Marx |
| 🧪 医学 | 屠呦呦 |
| 🔬 科学 | Marie Curie · Jane Goodall |
| 🤖 科技 | Alan Turing |
| 📚 管理 | Peter Drucker · Simon Sinek |
| 🏛️ 政治 | Alexander Hamilton · Franklin D. Roosevelt |
| 🌌 文学 | 刘慈欣 |
| 🏀 体育 | Kobe Bryant |
| 🎙️ 媒体 | Oprah Winfrey |
| 👗 时尚 | Coco Chanel |
| ✨ 生活方式 | Marie Kondo |

每位人物都包含：
- 深度人格分析（传记、核心理念、思维框架）
- 专属 System Prompt（定义发言方式与决策逻辑）
- 多维度标签（可筛选、可组合）

---

## 🎯 使用场景

### 商业决策
> 召集 Buffett + Dalio + Drucker，讨论「我们的 SaaS 产品应该涨价还是做量？」

### 跨界头脑风暴
> 让 Kobe Bryant + 任正非 + 刘慈欣一起聊「如何打造一个百年组织」

### 哲学思辨
> 孔子 + 苏格拉底 + Nietzsche 对谈「技术奇点会解放还是奴役人类？」

### 投资分析
> Buffett + Munger + Keynes 辩论「AI 泡沫会不会破裂？」

---

## 🛠️ 架构

```
┌─────────────────────────────────────────┐
│  🌐 前端 (static/index.html)            │
│  领域筛选 · 标签筛选 · 智能研究 · 自定义  │
└──────────────┬──────────────────────────┘
               │ SSE (实时推流)
┌──────────────▼──────────────────────────┐
│  🖥️ 后端 (server.py)                    │
│  HTTP Server · SSE · 会话管理            │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  🧠 人格引擎 (persona_researcher.py)    │
│  23人内置知识库 · Web搜索 · LLM合成      │
└─────────────────────────────────────────┘
```

---

## 📝 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/personas` | GET | 获取所有人物 |
| `/api/domains` | GET | 获取所有领域 |
| `/api/tags` | GET | 获取所有标签 |
| `/api/research` | POST | 研究一个特定人物 |
| `/api/roundtable` | POST | 启动一场圆桌对话 |
| `/api/stream/<id>` | GET | SSE 流式订阅辩论过程 |

---

## 🔧 技术栈

- **后端**：Python 标准库 (`http.server` + `threading` + `queue`)
- **实时通信**：Server-Sent Events (SSE)
- **前端**：纯 HTML/CSS/JavaScript（零框架）
- **AI 推理**：OpenAI API 兼容接口（MiMo / DeepSeek / Claude 均可）

---

## 📄 License

MIT
