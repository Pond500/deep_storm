# วิธีแก้ไขปัญหา You.com API (403 Forbidden)

## สาเหตุ
You.com API key ไม่ valid, หมดอายุ, หรือไม่มีสิทธิ์ใช้งาน

## ตัวเลือกแก้ไข

### 1. ใช้ Search Engine อื่น (แนะนำ)

#### Tavily Search (แนะนำที่สุด)
- 🎁 **Free tier**: 1,000 requests/month
- 🎯 Optimized for AI research และ RAG
- 🚀 ลงทะเบียนง่าย: https://tavily.com

```bash
# แก้ใน secrets.toml
TAVILY_API_KEY = "tvly-xxxxxxxxxxxx"
```

```python
# แก้ใน test_storm_simple.py
from knowledge_storm.rm import TavilySearchRM

rm = TavilySearchRM(
    tavily_api_key=tavily_key,
    k=engine_args.search_top_k,
    include_raw_content=True
)
```

#### Serper (Google Search API)
- 🎁 **Free**: $5 credit (~2,500 queries)
- 🔥 Google search results (ดีที่สุด)
- 📝 Sign up: https://serper.dev

```bash
# secrets.toml
SERPER_API_KEY = "xxxxxxxxxxxxxx"
```

```python
# test_storm_simple.py
from knowledge_storm.rm import SerperRM

rm = SerperRM(
    serper_search_api_key=serper_key,
    query_params={"autocorrect": True, "num": engine_args.search_top_k}
)
```

#### Bing Search
- 🎁 **Free tier**: 1,000 queries/month
- 🔗 Azure Marketplace: https://azure.microsoft.com/en-us/services/cognitive-services/bing-web-search-api/

```bash
# secrets.toml
BING_SEARCH_API_KEY = "xxxxxxxxxxxxxxxxxxxxxxx"
```

```python
# test_storm_simple.py
from knowledge_storm.rm import BingSearch

rm = BingSearch(
    bing_search_api_key=bing_key,
    k=engine_args.search_top_k
)
```

### 2. Offline Mode (ไม่ใช้ Search)

ถ้าไม่อยากใช้ search engine เลย สามารถให้ STORM ใช้ knowledge จาก LLM อย่างเดียวได้

```python
# ใน test_storm_simple.py เปลี่ยนเป็น
from knowledge_storm.rm import VectorRM

# ใช้ vector search จาก embeddings (ไม่ต้อง internet search)
rm = VectorRM(
    collection_name="storm_knowledge",
    embedding_model="paraphrase-MiniLM-L6-v2",
    device="mps"  # ใช้ Mac GPU
)
```

**ข้อจำกัดของ Offline Mode:**
- ไม่มีข้อมูลใหม่จาก internet
- ขึ้นอยู่กับ knowledge cutoff ของ LLM
- คุณภาพต่ำกว่าเมื่อเทียบกับการใช้ search

### 3. หา You.com API Key ใหม่

ลงทะเบียนใหม่ที่: https://you.com/api

**ข้อสังเกต:** You.com API อาจเปลี่ยน pricing model หรือยกเลิก free tier แล้ว

---

## สรุป

**ลำดับความแนะนำ:**
1. ✅ **Tavily** - ดีที่สุดสำหรับ AI research, มี free tier
2. ✅ **Serper** - Google results, $5 credit ฟรี
3. ⚠️ **Bing** - Free tier จำกัด
4. ⚠️ **Offline Mode** - ถ้าไม่มี internet search

---

## ติดตั้ง Search Engine ใหม่

```bash
# ไม่ต้องติดตั้งเพิ่ม - STORM รองรับแล้ว
# แค่เพิ่ม API key ใน secrets.toml
```

ถ้าต้องการความช่วยเหลือในการตั้งค่า search engine ใดๆ บอกได้เลยครับ!
