# 🌩️ STORM — สรุปการทำงานฉบับสมบูรณ์

> เอกสารนี้อธิบาย flow การทำงาน บทบาทของ agent และ prompt จริงที่ใช้ในระบบ STORM  
> ครอบคลุมทั้ง 4 Stage ตั้งแต่ user ใส่หัวข้อจนได้บทความ

---

## ภาพรวม Pipeline

```
User ใส่หัวข้อ
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1: Knowledge Curation  (ค้นคว้าข้อมูลหลายมุมมอง)        │
│  ┌──────────────────┐    ┌───────────────────────────────────┐  │
│  │ Persona Generator │ →  │ ConvSimulator (per persona)       │  │
│  │ สร้างบทบาทนักเขียน│    │ WikiWriter ↔ TopicExpert (5 รอบ) │  │
│  └──────────────────┘    └───────────────────────────────────┘  │
└───────────────────────────────────┬─────────────────────────────┘
                                    │ StormInformationTable
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 2: Outline Generation  (สร้างโครงร่าง)                   │
│  Draft Outline  →  Refined Outline (ปรับโดยดูบทสนทนา)          │
└───────────────────────────────────┬─────────────────────────────┘
                                    │ storm_gen_outline.txt
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 3: Article Generation  (เขียนเนื้อหา parallel)           │
│  Section A ─┐                                                   │
│  Section B ─┼─→  รวมเป็น Draft Article                         │
│  Section C ─┘                                                   │
└───────────────────────────────────┬─────────────────────────────┘
                                    │ storm_gen_article.txt
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 4: Polishing  (ขัดเกลา)                                  │
│  เขียน Lead Section  +  ลบเนื้อหาซ้ำ                           │
└───────────────────────────────────┬─────────────────────────────┘
                                    │
                                    ▼
                    storm_gen_article_polished.txt ✅
```

---

## Stage 1 — Knowledge Curation 🔍

### ขั้นที่ 1.1 — สร้าง Personas

ก่อนค้นคว้า ระบบจะสร้าง "บทบาทนักเขียน" หลายตัว เพื่อมองหัวข้อจากหลายมุม

```
หัวข้อ: "ประวัติศาสตร์กรุงเทพ"
           │
           ▼
   FindRelatedTopic
   "ช่วยหา Wikipedia pages ที่เกี่ยวข้องกับหัวข้อนี้"
           │
           ▼ (URLs ของ Wikipedia pages ที่เกี่ยวข้อง)
           │
   GenPersona
   "สร้างกลุ่ม Wikipedia editors หลายบทบาทสำหรับหัวข้อนี้"
           │
           ▼
   Personas ที่ได้:
   - Basic fact writer (เพิ่มโดยระบบเสมอ)
   - นักประวัติศาสตร์: เน้นพัฒนาการทางประวัติศาสตร์
   - นักผังเมือง: เน้นสถาปัตยกรรมและผังเมือง
   - นักท่องเที่ยว: เน้นสถานที่สำคัญ
```

**Prompt: `FindRelatedTopic`**
```
I'm writing a Wikipedia page for a topic mentioned below.
Please identify and recommend some Wikipedia pages on closely related subjects.
I'm looking for examples that provide insights into interesting aspects
commonly associated with this topic, or examples that help me understand
the typical content and structure included in Wikipedia pages for similar topics.
Please list the urls in separate lines.

Topic of interest: {topic}
→ Output: [URLs]
```

**Prompt: `GenPersona`**
```
You need to select a group of Wikipedia editors who will work together to
create a comprehensive article on the topic. Each of them represents a
different perspective, role, or affiliation related to this topic.
For each editor, add a description of what they will focus on.
Format: 1. short summary: description
        2. short summary: description  ...

Topic of interest: {topic}
Wiki page outlines of related topics for inspiration: {TOC จาก Wikipedia}
→ Output: [รายชื่อ personas]
```

---

### ขั้นที่ 1.2 — ConvSimulator (บทสนทนาระหว่าง agent)

สำหรับ **แต่ละ persona** จะรันบทสนทนาระหว่าง WikiWriter กับ TopicExpert  
ทุก persona รัน **พร้อมกัน (parallel threads)**

```
┌─────────────────────────────────────────────────────────────────────┐
│  Persona: "นักประวัติศาสตร์"                                        │
│                                                                     │
│  วนซ้ำ max_conv_turn ครั้ง (default: 5)                            │
│                                                                     │
│  WikiWriter                           TopicExpert                   │
│  (question_asker_lm)                  (conv_simulator_lm)           │
│       │                                     │                       │
│       │──── "ประวัติการก่อตั้งกรุงเทพ? " ──▶│                       │
│       │                                     │── QuestionToQuery     │
│       │                                     │   แปลงเป็น queries    │
│       │                                     │── Vector Store Search │
│       │                                     │   ค้น Wikipedia ไทย   │
│       │                                     │── AnswerQuestion      │
│       │◀── "กรุงเทพก่อตั้งเมื่อ พ.ศ. 2325 [1][2]..." ──│           │
│       │                                     │                       │
│       │  (บันทึก dialogue turn)              │                       │
│       │                                     │                       │
│  [รอบถัดไป] คิดคำถามใหม่โดยดูประวัติสนทนา  │                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

#### 🤖 WikiWriter — ผู้ถามคำถาม

**บทบาท:** จำลองเป็น Wikipedia editor สวมบทบาทตาม persona กำลังสัมภาษณ์ผู้เชี่ยวชาญ  
**วิธีคิด:** ดูประวัติบทสนทนาทั้งหมด เลือกถามในสิ่งที่ยังไม่รู้และเกี่ยวข้องกับมุมมองของตัวเอง  
**หยุดเมื่อ:** ตอบว่า `"Thank you so much for your help!"` หรือครบ max_conv_turn รอบ

**Prompt: `AskQuestionWithPersona`**
```
You are an experienced Wikipedia writer and want to edit a specific page.
Besides your identity as a Wikipedia writer, you have specific focus when
researching the topic.
Now, you are chatting with an expert to get information. Ask good questions
to get more useful information.
When you have no more question to ask, say "Thank you so much for your help!"
to end the conversation.
Please only ask a question at a time and don't ask what you have asked before.
Your questions should be related to the topic you want to write.

Topic you want to write: {topic}
Your persona besides being a Wikipedia writer: {persona}
Conversation history:
{4 รอบล่าสุด: แสดงทั้ง Q&A}
{รอบก่อนหน้า: แสดงแค่คำถาม เพื่อประหยัด context}
→ question: [คำถาม]
```

---

#### 🤖 TopicExpert — ผู้ตอบคำถาม

**บทบาท:** ผู้เชี่ยวชาญที่ค้นหาข้อมูลจาก database แล้วสังเคราะห์คำตอบ  
**กฎสำคัญ:** ห้าม hallucinate — ถ้าไม่มีข้อมูลต้องบอกว่าไม่รู้  
**ทำงาน 3 ขั้นตอน:**

```
คำถาม (จาก WikiWriter)
      │
      ▼
 QuestionToQuery
 "แปลงคำถามเป็น search queries"
      │
      ▼ (max 2 queries)
      │
 Vector Store (HybridWikipediaRM)
 Dense Search + BM25 → top-k snippets
      │
      ▼ (snippets พร้อม citation index)
      │
 AnswerQuestion
 "สังเคราะห์คำตอบจาก snippets"
      │
      ▼
 คำตอบ + citation [1][2]... (กลับไปหา WikiWriter)
```

**Prompt: `QuestionToQuery`**
```
You want to answer the question using Google search.
What do you type in the search box?
Write the queries you will use in the following format:
- query 1
- query 2
...

Topic you are discussing about: {topic}
Question you want to answer: {question}
→ queries: [list]
```

**Prompt: `AnswerQuestion`**
```
You are an expert who can use information effectively. You are chatting with
a Wikipedia writer who wants to write a Wikipedia page on topic you know.
You have gathered the related information and will now use the information
to form a response.
Make your response as informative as possible, ensuring that every sentence
is supported by the gathered information. If the gathered information is not
directly related to the topic or question, provide the most relevant answer
based on the available information. If no appropriate answer can be formulated,
respond with "I cannot answer this question based on the available information."

Topic: {topic}
Question: {question}
Gathered information:
[1]: {snippet 1}
[2]: {snippet 2}
...
→ Now give your response.
  (Try to use as many different sources as possible and do not hallucinate.)
```

---

## Stage 2 — Outline Generation 📝

```
StormInformationTable (บทสนทนาจาก Stage 1)
           │
           ▼
  ┌─────────────────────────────────────────┐
  │          WriteOutline Module            │
  │                                         │
  │  รอบ 1: WritePageOutline (Draft)        │
  │  LLM สร้าง outline จากความรู้ตัวเอง    │
  │           │                             │
  │           ▼                             │
  │  รอบ 2: WritePageOutlineFromConv        │
  │  LLM ดูบทสนทนา Stage 1 แล้วปรับ outline│
  └─────────────────────────────────────────┘
           │
           ▼
  storm_gen_outline.txt
  # ประวัติ
  ## ยุคก่อตั้ง
  ## ยุคสมัยใหม่
  # ภูมิศาสตร์
  ## ที่ตั้ง
  # วัฒนธรรม
  ...
```

**Prompt รอบ 1: `WritePageOutline` (Draft)**
```
Write an outline for a Wikipedia page.
Format:
1. Use "# Title" for section, "## Title" for subsection, etc.
2. Do not include other information.
3. Do not include topic name itself in the outline.

The topic you want to write: {topic}
→ Write the Wikipedia page outline:
```

**Prompt รอบ 2: `WritePageOutlineFromConv` (Refined)**
```
Improve an outline for a Wikipedia page. You already have a draft outline
that covers the general information. Now you want to improve it based on
the information learned from an information-seeking conversation.
Format: Use "# Title", "## Title", etc.

The topic you want to write: {topic}
Conversation history: {บทสนทนาจาก Stage 1 — จำกัด 5,000 คำ}
Current outline: {draft outline}
→ Write the improved Wikipedia page outline:
```

---

## Stage 3 — Article Generation ✍️

```
Outline + InformationTable
          │
          ▼ (แยกเป็น sections)
          │
  ┌───────┼───────┐
  ▼       ▼       ▼    (parallel threads)
 Sec A  Sec B  Sec C   แต่ละ section:
  │       │       │    1. ดึง snippets จาก InformationTable
  │       │       │    2. ส่งให้ LLM เขียน พร้อม inline citation
  └───────┼───────┘
          │
          ▼
  storm_gen_article.txt (Draft)
```

> **หมายเหตุ:** Section ที่ชื่อ `Introduction` และ `Conclusion/Summary`  
> จะถูก skip ในขั้นตอนนี้ — ไปสร้างใน Stage 4 แทน

**Prompt: `WriteSection`**
```
Write a Wikipedia section based on the collected information.

Format:
1. Use "# Title", "## Title", etc. for structure
2. Use [1], [2], ..., [n] inline citations.
   (e.g., "The capital of Thailand is Bangkok.[1][3].")
   Do NOT include a References section.

The collected information:
[1]
{snippet 1}
[2]
{snippet 2}
...

The topic of the page: {topic}
The section you need to write: {section name}
→ Write the section with proper inline citations
  (Start your writing with # section title):
```

---

## Stage 4 — Article Polishing ✨

```
storm_gen_article.txt (Draft)
          │
          ▼
  WriteLeadSection          PolishPage (optional)
  เขียน Lead Section        ลบเนื้อหาที่ซ้ำกัน
  (บทนำ ≤4 ย่อหน้า)
          │
          ▼
  storm_gen_article_polished.txt ✅
```

**Prompt: `WriteLeadSection`**
```
Write a lead section for the given Wikipedia page:
1. Stand on its own as a concise overview. Identify the topic, establish
   context, explain why notable, summarize the most important points
   including any prominent controversies.
2. No more than four well-composed paragraphs.
3. Carefully sourced with inline citations where necessary.

The topic of the page: {topic}
The draft page: {FULL DRAFT ARTICLE}
→ Write the lead section:
```

**Prompt: `PolishPage`** *(ใช้เมื่อ `remove_duplicate=True`)*
```
You are a faithful text editor that is good at finding repeated information
in the article and deleting them to make sure there is no repetition.
You won't delete any non-repeated part. Keep inline citations and article
structure (indicated by "#", "##", etc.) appropriately.

The draft article: {ARTICLE}
→ Your revised article:
```

---

## สรุปตาราง Agent ทั้งหมด

| # | Agent | LLM Config | บทบาท | Stage |
|---|---|---|---|---|
| 1 | **Persona Generator** | `question_asker_lm` | หา Wikipedia pages เกี่ยวข้อง → สร้างบทบาทนักเขียนหลากหลาย | 1 |
| 2 | **WikiWriter** | `question_asker_lm` | ถามคำถามตามมุมมอง persona — ดูประวัติสนทนาเพื่อไม่ถามซ้ำ | 1 |
| 3 | **TopicExpert** | `conv_simulator_lm` | แปลงคำถาม → query → ค้น Vector Store → สังเคราะห์คำตอบ | 1 |
| 4 | **Outline Writer** | `outline_gen_lm` | สร้าง outline 2 รอบ (draft → refined) | 2 |
| 5 | **Section Writer** | `article_gen_lm` | เขียนเนื้อหา parallel ทุก section พร้อม citation | 3 |
| 6 | **Lead Writer** | `article_gen_lm` | เขียน Lead Section (บทนำ) | 4 |
| 7 | **Page Polisher** | `article_polish_lm` | ขัดเกลาและลบเนื้อหาซ้ำ | 4 |

> ในโปรเจกต์นี้ทุก agent ใช้ `openrouter/openai/gpt-4o-mini` ผ่าน LiteLLM

---

## Call Stack จาก Web API → Codebase

```
POST /api/generate  (web/app.py)
└── run_storm(topic, client_id, settings)
      └── STORMWikiRunner.run()  (knowledge_storm/storm_wiki/engine.py)
            │
            ├── [Stage 1] run_knowledge_curation_module()
            │     └── StormKnowledgeCurationModule.research()
            │           │                   (knowledge_curation.py)
            │           ├── _get_considered_personas()
            │           │     └── StormPersonaGenerator.generate_persona()
            │           │           └── CreateWriterWithPersona.forward()
            │           │                 ├── FindRelatedTopic  → LLM call ①
            │           │                 └── GenPersona        → LLM call ②
            │           │
            │           └── _run_conversation()  [parallel per persona]
            │                 └── ConvSimulator.forward()
            │                       loop max_conv_turn (default 5):
            │                       ├── WikiWriter (AskQuestionWithPersona) → LLM call ③
            │                       └── TopicExpert.forward()
            │                             ├── QuestionToQuery  → LLM call ④
            │                             ├── retriever.retrieve()  → Vector Store
            │                             └── AnswerQuestion   → LLM call ⑤
            │
            ├── [Stage 2] run_outline_generation_module()
            │     └── WriteOutline.forward()  (outline_generation.py)
            │           ├── WritePageOutline         → LLM call ⑥
            │           └── WritePageOutlineFromConv → LLM call ⑦
            │
            ├── [Stage 3] run_article_generation_module()
            │     └── generate_article()  [parallel per section]
            │           └── ConvToSection (WriteSection) → LLM call ⑧×N sections
            │
            └── [Stage 4] run_article_polishing_module()
                  └── PolishPageModule.forward()
                        ├── WriteLeadSection → LLM call ⑨
                        └── PolishPage       → LLM call ⑩ (optional)
```

---

## จำนวน LLM Calls โดยประมาณ

| Stage | LLM Calls |
|---|---|
| Stage 1 | ②(personas) + (③+④+⑤) × max_conv_turn × num_personas |
| Stage 2 | ⑥+⑦ = 2 calls |
| Stage 3 | ⑧ × จำนวน sections |
| Stage 4 | ⑨+⑩ = 1-2 calls |

**ตัวอย่าง:** 4 personas × 5 รอบ × 3 calls + overhead ≈ **70-100+ LLM calls ต่อบทความ**
