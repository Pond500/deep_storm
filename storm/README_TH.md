# 🌩️ STORM - Deep Research System

> **Synthesis of Topic Outlines through Retrieval and Multi-perspective Question Asking**

ระบบ AI สำหรับสร้างบทความวิจัยเชิงลึกสไตล์ Wikipedia โดยอัตโนมัติ พร้อม citations และ references จากอินเทอร์เน็ต

## 📋 สารบัญ

- [✨ คุณสมบัติเด่น](#-คุณสมบัติเด่น)
- [🚀 Quick Start](#-quick-start)
- [📦 สิ่งที่ติดตั้งแล้ว](#-สิ่งที่ติดตั้งแล้ว)
- [🎯 วิธีใช้งาน](#-วิธีใช้งาน)
- [⚙️ Configuration](#️-configuration)
- [📚 เอกสารเพิ่มเติม](#-เอกสารเพิ่มเติม)

---

## ✨ คุณสมบัติเด่น

### 🔍 STORM (Automatic Research)
- **Perspective-Guided Research**: สร้างคำถามจากมุมมองต่างๆ เพื่อความครอบคลุม
- **Simulated Conversation**: จำลองบทสนทนาระหว่างผู้เขียน-ผู้เชี่ยวชาญ
- **Automatic Citation**: สร้าง references อัตโนมัติจากแหล่งที่น่าเชื่อถือ
- **Outline Generation**: สร้างโครงสร้างบทความแบบ hierarchical

### 👥 Co-STORM (Human-in-the-Loop)
- **Multi-Agent System**: LLM experts, Moderator, และ Human collaboration
- **Mind Map**: แสดงโครงสร้างความรู้แบบ interactive
- **Real-time Interaction**: ผู้ใช้สามารถเข้าร่วมและชี้นำการวิจัย

### 🎨 Streamlit UI
- **Visual Interface**: หน้าต่างสร้างบทความที่ใช้งานง่าย
- **Progress Tracking**: ติดตามความคืบหน้าแบบ real-time
- **Article Management**: จัดเก็บและเรียกดูบทความที่สร้างไว้

---

## 🚀 Quick Start

### 1. ติดตั้งเสร็จแล้ว ✓

```bash
# ตรวจสอบว่าอยู่ใน directory ถูกต้อง
pwd
# Output: /Users/pond500/RAG/deep_storm/storm

# Activate virtual environment
source .venv/bin/activate

# ตรวจสอบการติดตั้ง
python -c "import knowledge_storm; print('✅ STORM ready!')"
```

### 2. เติม API Keys

**แก้ไขไฟล์ `secrets.toml`:**

```bash
nano secrets.toml
```

**ใส่ค่าขั้นต่ำ:**
```toml
OPENAI_API_KEY = "sk-..."        # จาก https://platform.openai.com/
YDC_API_KEY = "your-you-key"     # จาก https://api.you.com/
OPENAI_API_TYPE = "openai"
ENCODER_API_TYPE = "openai"
```

### 3. ทดสอบรัน

#### Option A: ใช้ Script ง่าย ๆ

```bash
# Activate environment ก่อน
source .venv/bin/activate

# รัน test script
python test_storm_simple.py
```

จะมี prompt ให้ใส่หัวข้อ เช่น:
```
🎯 กรุณาใส่หัวข้อที่ต้องการวิจัย: The history of Bitcoin
```

#### Option B: รัน Streamlit UI

```bash
cd frontend/demo_light
streamlit run storm.py
```

เปิดเบราว์เซอร์ไปที่: http://localhost:8501

---

## 📦 สิ่งที่ติดตั้งแล้ว

### ✅ Environment
- Python 3.12 virtual environment
- Path: `/Users/pond500/RAG/deep_storm/storm/.venv`

### ✅ Core Dependencies
- `dspy_ai` 2.4.9 - STORM framework core
- `litellm` - รองรับ LLM หลายตัว (OpenAI, Claude, etc.)
- `sentence-transformers` - Embedding models
- `qdrant-client` - Vector database
- `trafilatura` - Web scraping

### ✅ Search Engines Support
- You.com Search
- Bing Search
- Google Search (via Serper)
- Tavily Search
- Brave Search
- DuckDuckGo Search

### ✅ UI
- Streamlit 1.31.1 + extensions
- Real-time progress tracking
- Article management system

---

## 🎯 วิธีใช้งาน

### A. Streamlit UI (แนะนำ)

```bash
cd frontend/demo_light
source ../../.venv/bin/activate
streamlit run storm.py
```

**Features:**
- 📝 Create New Article - สร้างบทความใหม่
- 📊 Real-time Progress - ดูความคืบหน้าแบบ live
- 📚 My Articles - จัดการบทความที่สร้าง
- 🔗 References - แสดงแหล่งอ้างอิง

### B. Command Line

```bash
source .venv/bin/activate

# ใช้ You.com search
python examples/storm_examples/run_storm_wiki_gpt.py \
    --output-dir ./results \
    --retriever you \
    --do-research \
    --do-generate-outline \
    --do-generate-article \
    --do-polish-article

# ใช้ Bing search
python examples/storm_examples/run_storm_wiki_gpt.py \
    --output-dir ./results \
    --retriever bing \
    --do-research \
    --do-generate-outline \
    --do-generate-article \
    --do-polish-article
```

### C. Python API

```python
from knowledge_storm import STORMWikiRunner, STORMWikiRunnerArguments, STORMWikiLMConfigs
from knowledge_storm.lm import LitellmModel
from knowledge_storm.rm import YouRM

# Setup (ดูตัวอย่างเต็มใน test_storm_simple.py)
lm_configs = STORMWikiLMConfigs()
# ... config models ...

runner = STORMWikiRunner(args, lm_configs, retriever)
runner.run(topic="Your topic", do_research=True, ...)
```

---

## ⚙️ Configuration

### เปลี่ยน Models

**ใน `test_storm_simple.py` หรือ `frontend/demo_light/demo_util.py`:**

```python
# ใช้ GPT-4o แทน GPT-4o-mini (คุณภาพสูงกว่า แต่แพงกว่า)
gpt_4o = LitellmModel(model='gpt-4o', max_tokens=3000, ...)

# ใช้ Claude
claude = LitellmModel(
    model='claude-3-5-sonnet-20241022',
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    ...
)
```

### ปรับ Parameters

```python
engine_args = STORMWikiRunnerArguments(
    max_conv_turn=5,        # เพิ่มรอบ conversation → ลึกขึ้น
    max_perspective=5,      # เพิ่ม perspectives → ครอบคลุมมากขึ้น
    search_top_k=10,       # เพิ่ม search results
    max_search_queries=30, # เพิ่มจำนวน queries
)
```

### เปลี่ยน Retriever

```python
# Bing Search
from knowledge_storm.rm import BingSearch
rm = BingSearch(bing_search_api_key=os.getenv("BING_SEARCH_API_KEY"), k=5)

# Vector Database (ground บน corpus ของคุณ)
from knowledge_storm.rm import VectorRM
rm = VectorRM(collection_name="my_docs", embedding_model="...", ...)
```

---

## 📁 โครงสร้าง Output

หลังรันเสร็จจะได้:

```
output/
└── [topic_name]/
    ├── conversation_log.json           # บันทึกการวิจัย
    ├── raw_search_results.json         # ผล search
    ├── storm_gen_outline.txt           # Outline
    ├── storm_gen_article.txt           # บทความต้นฉบับ
    ├── storm_gen_article_polished.txt  # บทความฉบับสมบูรณ์ ⭐
    └── url_to_info.json               # แหล่งอ้างอิง
```

**ไฟล์สำคัญ:** `storm_gen_article_polished.txt`

---

## 💰 ค่าใช้จ่าย (โดยประมาณ)

| Configuration | ต่อบทความ | เหมาะสำหรับ |
|--------------|-----------|-------------|
| GPT-3.5 + GPT-4o-mini | $0.30-0.50 | ทดสอบ/งานทั่วไป |
| GPT-3.5 + GPT-4o | $0.75-1.50 | คุณภาพดี |
| GPT-4o ทั้งหมด | $2.00-4.00 | คุณภาพสูงสุด |
| Claude 3.5 Sonnet | $1.50-3.00 | Alternative |
| Local Models (ฟรี) | $0 (Search API เท่านั้น) | Mistral/Llama |

**Tips ประหยัด:**
- ลด `max_conv_turn` และ `max_perspective`
- ใช้ GPT-3.5-turbo สำหรับ conversation
- ใช้ GPT-4o-mini แทน GPT-4o

---

## 🐛 Troubleshooting

### ❌ ModuleNotFoundError
```bash
# ตรวจสอบ venv
source .venv/bin/activate
pip list | grep storm
```

### ❌ API Key Error
```bash
# ตรวจสอบ secrets.toml
cat secrets.toml | grep API_KEY
```

### ❌ Streamlit Port ซ้อน
```bash
# ใช้ port อื่น
streamlit run storm.py --server.port 8502
```

### ❌ Out of Memory (M1/M2 Mac)
```python
# ใช้ 'mps' device แทน 'cuda'
# หรือลด model size
```

---

## 📚 เอกสารเพิ่มเติม

### 📄 ในโปรเจคนี้
- **`SETUP_GUIDE.md`** - คู่มือละเอียด + troubleshooting
- **`test_storm_simple.py`** - ตัวอย่าง Python script
- **`examples/`** - ตัวอย่างการใช้งานขั้นสูง

### 🌐 External Links
- **Web Demo**: https://storm.genie.stanford.edu/
- **GitHub**: https://github.com/stanford-oval/storm
- **STORM Paper**: https://arxiv.org/abs/2402.14207
- **Co-STORM Paper**: https://arxiv.org/abs/2408.15232
- **Official Site**: https://storm-project.stanford.edu/

### 🎓 Papers
```bibtex
@inproceedings{shao-etal-2024-assisting,
    title = "Assisting in Writing Wikipedia-like Articles From Scratch with Large Language Models",
    author = "Shao, Yijia and Jiang, Yucheng and ...",
    booktitle = "NAACL 2024",
    year = "2024"
}
```

---

## 🤝 Contributing

STORM เป็น open-source project ที่เปิดรับ contributions:

- 🐛 Report bugs: [GitHub Issues](https://github.com/stanford-oval/storm/issues)
- 💡 Feature requests: Welcome!
- 🔧 Pull requests: Highly appreciated

---

## 📧 Contact

- **Authors**: Yijia Shao, Yucheng Jiang
- **Email**: shaoyj@stanford.edu, yuchengj@stanford.edu
- **Affiliation**: Stanford University

---

## 📊 Stats

- ⭐ **27.9k+ Stars** on GitHub
- 👥 **70,000+ Users** on web demo
- 📄 **NAACL 2024** + **EMNLP 2024** papers

---

## 🎉 Ready to Start!

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Edit API keys
nano secrets.toml

# 3. Run!
python test_storm_simple.py
# หรือ
cd frontend/demo_light && streamlit run storm.py
```

**Happy Researching! 🚀**
