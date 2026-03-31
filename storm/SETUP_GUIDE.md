# 🚀 STORM Setup Guide - คู่มือการใช้งานฉบับสมบูรณ์

## ✅ สรุปสิ่งที่ติดตั้งเสร็จแล้ว

### 1. โครงสร้าง Project
```
/Users/pond500/RAG/deep_storm/storm/
├── .venv/                      # Python virtual environment (3.12)
├── secrets.toml                # ไฟล์ API keys (ต้องกรอก!)
├── requirements.txt            # Dependencies หลัก
├── examples/                   # ตัวอย่างการใช้งาน
├── frontend/
│   └── demo_light/            # Streamlit UI
│       ├── .streamlit/
│       │   └── secrets.toml   # Config สำหรับ UI
│       ├── storm.py           # Main UI file
│       └── requirements.txt   # UI dependencies
└── knowledge_storm/           # STORM library
```

### 2. Dependencies ที่ติดตั้งแล้ว ✓
- ✅ Python 3.12 virtual environment
- ✅ STORM core library (dspy_ai, litellm, etc.)
- ✅ Search & retrieval tools (sentence-transformers, qdrant, etc.)
- ✅ Streamlit UI และ dependencies ทั้งหมด

---

## 📝 ขั้นตอนถัดไป: เติม API Keys

### ไฟล์ที่ต้องแก้ไข
```bash
/Users/pond500/RAG/deep_storm/storm/secrets.toml
```

### API Keys ที่ต้องมี (เลือกอย่างน้อย 1 ชุด)

#### **Option 1: OpenAI + You.com (แนะนำ)**
```toml
OPENAI_API_KEY = "sk-..."        # จาก https://platform.openai.com/api-keys
YDC_API_KEY = "your-you-key"     # จาก https://api.you.com/
OPENAI_API_TYPE = "openai"
ENCODER_API_TYPE = "openai"
```

#### **Option 2: OpenAI + Bing Search**
```toml
OPENAI_API_KEY = "sk-..."
BING_SEARCH_API_KEY = "your-bing-key"  # จาก Azure Bing Search API
OPENAI_API_TYPE = "openai"
```

#### **Option 3: Claude + Bing**
```toml
ANTHROPIC_API_KEY = "sk-ant-..."       # จาก https://console.anthropic.com/
BING_SEARCH_API_KEY = "your-bing-key"
```

### วิธีหา API Keys (ฟรีหรือมี Free Tier)

1. **OpenAI** 
   - URL: https://platform.openai.com/signup
   - ค่าใช้จ่าย: ~$0.75-1.80 ต่อบทความ
   - Free trial: $5 credit สำหรับผู้ใช้ใหม่

2. **You.com Search**
   - URL: https://api.you.com/
   - มี free tier สำหรับทดสอบ

3. **Bing Search API**
   - URL: https://www.microsoft.com/en-us/bing/apis/bing-web-search-api
   - Free tier: 1,000 queries/month

---

## 🎯 วิธีรันโปรเจค

### A. รัน Streamlit UI (แนะนำสำหรับเริ่มต้น)

```bash
# 1. เปิด terminal และไปยัง directory
cd /Users/pond500/RAG/deep_storm/storm/frontend/demo_light

# 2. Activate virtual environment
source ../../.venv/bin/activate

# 3. รัน Streamlit app
streamlit run storm.py
```

**หลังรันคำสั่ง:**
- เบราว์เซอร์จะเปิดอัตโนมัติที่ `http://localhost:8501`
- ถ้าไม่เปิด ให้เปิดเบราว์เซอร์แล้วไปที่ URL นั้น

**Features ของ UI:**
- ✅ สร้างบทความใหม่ (Create New Article)
- ✅ ดูความคืบหน้า real-time
- ✅ แสดงบทความและอ้างอิงแบบ side-by-side
- ✅ เรียกดูบทความที่สร้างไว้ (My Articles)

---

### B. รันจาก Command Line (สำหรับ Advanced)

#### ตัวอย่าง 1: รันด้วย GPT + You.com Search

```bash
cd /Users/pond500/RAG/deep_storm/storm
source .venv/bin/activate

python examples/storm_examples/run_storm_wiki_gpt.py \
    --output-dir ./results \
    --retriever you \
    --do-research \
    --do-generate-outline \
    --do-generate-article \
    --do-polish-article
```

**จะถาม Topic ที่ต้องการวิจัย:**
```
Topic: The history of artificial intelligence
```

#### ตัวอย่าง 2: รันด้วย Bing Search

```bash
python examples/storm_examples/run_storm_wiki_gpt.py \
    --output-dir ./results \
    --retriever bing \
    --do-research \
    --do-generate-outline \
    --do-generate-article \
    --do-polish-article
```

#### ตัวอย่าง 3: Ground บน Corpus ของคุณเอง (VectorRM)

```bash
python examples/storm_examples/run_storm_wiki_gpt_with_VectorRM.py \
    --output-dir ./results \
    --vector-db-mode offline \
    --offline-vector-db-dir ./vector_db \
    --csv-file-path ./your_documents.csv \
    --device mps \
    --do-research \
    --do-generate-outline \
    --do-generate-article \
    --do-polish-article
```

---

### C. ใช้ Python API โดยตรง

สร้างไฟล์ `test_storm.py`:

```python
import os
from knowledge_storm import STORMWikiRunnerArguments, STORMWikiRunner, STORMWikiLMConfigs
from knowledge_storm.lm import LitellmModel
from knowledge_storm.rm import YouRM

# ตั้งค่า Language Models
lm_configs = STORMWikiLMConfigs()
openai_kwargs = {
    'api_key': os.getenv("OPENAI_API_KEY"),
    'temperature': 1.0,
    'top_p': 0.9,
}

# Model ถูกสำหรับ conversation
gpt_35 = LitellmModel(model='gpt-3.5-turbo', max_tokens=500, **openai_kwargs)

# Model แรงสำหรับ article generation
gpt_4o = LitellmModel(model='gpt-4o', max_tokens=3000, **openai_kwargs)

lm_configs.set_conv_simulator_lm(gpt_35)
lm_configs.set_question_asker_lm(gpt_35)
lm_configs.set_outline_gen_lm(gpt_4o)
lm_configs.set_article_gen_lm(gpt_4o)
lm_configs.set_article_polish_lm(gpt_4o)

# ตั้งค่า Runner
engine_args = STORMWikiRunnerArguments(
    output_dir='./results',
    max_conv_turn=3,
    max_perspective=3,
    search_top_k=3,
)

# ตั้งค่า Search Engine
rm = YouRM(ydc_api_key=os.getenv('YDC_API_KEY'), k=engine_args.search_top_k)

# สร้าง Runner
runner = STORMWikiRunner(engine_args, lm_configs, rm)

# รันการวิจัย
topic = "The evolution of large language models"
runner.run(
    topic=topic,
    do_research=True,
    do_generate_outline=True,
    do_generate_article=True,
    do_polish_article=True,
)

runner.post_run()
runner.summary()

print(f"✅ บทความเสร็จแล้ว! ดูได้ที่: {engine_args.output_dir}")
```

รัน:
```bash
source .venv/bin/activate
python test_storm.py
```

---

## 📊 Output Files

หลังรันเสร็จจะได้ไฟล์:

```
results/
├── conversation_log.json           # บันทึกการสนทนา research
├── raw_search_results.json         # ผลการค้นหาดิบ
├── storm_gen_outline.txt           # Outline ของบทความ
├── storm_gen_article.txt           # บทความฉบับเต็ม
├── storm_gen_article_polished.txt  # บทความหลัง polish
└── url_to_info.json               # ข้อมูลแหล่งอ้างอิง
```

---

## 🎛️ การปรับแต่ง Configuration

### เปลี่ยน Models

แก้ในไฟล์ `frontend/demo_light/demo_util.py`:

```python
def set_storm_runner():
    # เปลี่ยนโมเดล
    gpt_4o = LitellmModel(model='gpt-4o-mini', ...)  # ใช้ mini version ถูกกว่า
    
    # หรือใช้ Claude
    claude = LitellmModel(model='claude-3-5-sonnet-20241022', ...)
    
    # เปลี่ยน retriever
    rm = BingSearch(bing_search_api_key=..., k=5)  # เพิ่มจำนวน results
```

### เปลี่ยนพารามิเตอร์

```python
runner_args = STORMWikiRunnerArguments(
    max_conv_turn=5,                   # จำนวนรอบ conversation (default: 3)
    max_perspective=5,                 # จำนวน perspectives (default: 3)
    search_top_k=5,                    # จำนวน search results (default: 3)
    max_search_queries_per_turn=5,     # จำนวน queries ต่อรอบ (default: 3)
)
```

---

## 🐛 Troubleshooting

### ปัญหา 1: `ModuleNotFoundError`
```bash
# ตรวจสอบว่า activate venv แล้ว
source /Users/pond500/RAG/deep_storm/storm/.venv/bin/activate

# ติดตั้ง dependencies ใหม่
pip install -r requirements.txt
```

### ปัญหา 2: API Key Error
```bash
# ตรวจสอบว่ามี API keys ใน secrets.toml
cat /Users/pond500/RAG/deep_storm/storm/secrets.toml

# สำหรับ Streamlit UI ต้องมีใน .streamlit/ ด้วย
cat /Users/pond500/RAG/deep_storm/storm/frontend/demo_light/.streamlit/secrets.toml
```

### ปัญหา 3: Streamlit ไม่เปิด
```bash
# ลอง port อื่น
streamlit run storm.py --server.port 8502
```

### ปัญหา 4: Out of Memory (Apple Silicon)
```bash
# ใช้ device='mps' แทน 'cuda'
# หรือใช้ model เล็กกว่า (gpt-3.5-turbo, gpt-4o-mini)
```

---

## 💡 Tips & Best Practices

### 1. ประหยัดค่าใช้จ่าย
- ใช้ `gpt-3.5-turbo` สำหรับ conversation/question asking
- ใช้ `gpt-4o-mini` แทน `gpt-4o` (ถูกกว่า 10 เท่า)
- ลด `max_conv_turn` และ `max_perspective`

### 2. เพิ่มคุณภาพ
- เพิ่ม `max_conv_turn` = 5-7
- เพิ่ม `search_top_k` = 5-10
- ใช้ `gpt-4o` หรือ `claude-3-5-sonnet` สำหรับ article generation

### 3. หัวข้อที่เหมาะสม
✅ **เหมาะกับ:**
- หัวข้อที่มีข้อมูลเยอะบนอินเทอร์เน็ต
- เหตุการณ์ล่าสุด (ถ้าใช้ search engine)
- หัวข้อเชิงสำรวจ (survey topics)

❌ **ไม่เหมาะกับ:**
- หัวข้อที่ต้องการความเชี่ยวชาญสูง
- ข้อมูลลับ/ไม่เปิดเผย
- งานที่ต้องการการตรวจสอบแบบละเอียด

---

## 📚 ทรัพยากรเพิ่มเติม

- 📄 **STORM Paper**: https://arxiv.org/abs/2402.14207
- 📄 **Co-STORM Paper**: https://arxiv.org/abs/2408.15232
- 🌐 **Web Demo**: https://storm.genie.stanford.edu/
- 💻 **GitHub**: https://github.com/stanford-oval/storm
- 📖 **Documentation**: ดูใน `examples/` folder

---

## 🎉 Quick Start Commands

```bash
# 1. เปิด Terminal
cd /Users/pond500/RAG/deep_storm/storm

# 2. Activate environment
source .venv/bin/activate

# 3. แก้ไข API keys
nano secrets.toml  # หรือใช้ editor ที่ชอบ

# 4. รัน Streamlit UI
cd frontend/demo_light
streamlit run storm.py
```

---

## 📧 ติดต่อ/ช่วยเหลือ

- GitHub Issues: https://github.com/stanford-oval/storm/issues
- Email: shaoyj@stanford.edu, yuchengj@stanford.edu

---

**สนุกกับการใช้ STORM! 🚀**
