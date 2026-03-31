# 🤝 Co-STORM — สรุปการทำงานฉบับสมบูรณ์

> Co-STORM (Collaborative STORM) ต่างจาก STORM ตรงที่ **ผู้ใช้สามารถมีส่วนร่วมในกระบวนการวิจัย** ได้  
> แทนที่ agent จะทำงานเองทั้งหมด ผู้ใช้สามารถถาม ตอบ หรือกำหนดทิศทางการสนทนาได้ตลอดเวลา

---

## ภาพรวม Pipeline

```
User ใส่หัวข้อ
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: Warm Start  (เตรียมความรู้พื้นฐาน)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. ค้นหาข้อมูลพื้นฐาน (Background Research)             │   │
│  │ 2. สร้าง Expert agents                                   │   │
│  │ 3. Expert ↔ Moderator สนทนาแบบ mini-STORM (parallel)    │   │
│  │ 4. สร้าง Outline → Knowledge Base (Mind Map)             │   │
│  │ 5. สร้างบทสนทนาแนะนำหัวข้อ (Report → Conversation)      │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────┘
                                    │ Knowledge Base + Conversation History
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 2: Interactive Conversation  (สนทนาแบบ Round Table)       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ วนซ้ำ total_conv_turn รอบ (default: 20):                 │   │
│  │ 1. DiscourseManager ตัดสินใจว่าใครจะพูดต่อ               │   │
│  │ 2. Agent ที่ถูกเลือกสร้าง utterance                      │   │
│  │ 3. อัปเดต Knowledge Base (Mind Map)                      │   │
│  │ 4. ถ้า user มีส่วนร่วม → Moderator override              │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────┘
                                    │ Knowledge Base สมบูรณ์
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 3: Report Generation  (สร้างบทความ)                       │
│  Knowledge Base → เขียนแต่ละ node เป็น section (parallel)       │
│  → รวมเป็นบทความ                                                │
└───────────────────────────────────┬─────────────────────────────┘
                                    │
                                    ▼
                      costorm_article.txt ✅
```

---

## Phase 1 — Warm Start 🔥

> **เป้าหมาย:** สร้าง Knowledge Base เริ่มต้น ก่อนที่ user จะเข้ามามีส่วนร่วม  
> ทำงานคล้าย **mini-STORM** — spawn agents หลายตัวคุยกันหลายรอบ

### ขั้นที่ 1.1 — Background Research (ค้นข้อมูลพื้นฐาน)

```
หัวข้อ: "สมเด็จพระนเรศวร"
           │
           ▼
  AnswerQuestionModule
  query: "Background information about สมเด็จพระนเรศวร"
           │
  ┌────────┼────────┐
  │ QuestionToQuery  │  แปลงเป็น search queries
  │ Vector Store     │  ค้น Wikipedia ไทย
  │ AnswerQuestion   │  สังเคราะห์ข้อมูลพื้นฐาน
  └────────┼────────┘
           ▼
  Background info พร้อม citation
```

### ขั้นที่ 1.2 — สร้าง Expert Agents

ใช้ข้อมูลพื้นฐานจากขั้นที่ 1.1 มาสร้างผู้เชี่ยวชาญ

**Prompt: `GenerateExpertGeneral`**
```
You need to select a group of diverse experts who will be suitable to be
invited to a roundtable discussion on the given topic.
Each expert should represent a different perspective, role, or affiliation
related to this topic.
You can use the background information provided about the topic for
inspiration. For each expert, add a description of their expertise and
what they will focus on during the discussion.
No need to include speakers name in the output.
Strictly follow format below:
1. [speaker 1 role]: [speaker 1 short description]
2. [speaker 2 role]: [speaker 2 short description]

Topic of interest: {topic}
Background information about the topic: {background_info}
Number of speakers needed: {num_experts}
→ experts: [list]
```

### ขั้นที่ 1.3 — Perspective-Guided QA (Expert ↔ Moderator)

สำหรับ **แต่ละ Expert** (รัน parallel):

```
  WarmStartModerator                     AnswerQuestionModule
  (question_asking_lm)                   (question_answering_lm)
       │                                        │
       │── สร้างคำถามสำหรับ Expert นี้ ──────▶│
       │                                        │── QuestionToQuery
       │                                        │── Vector Store Search
       │                                        │── AnswerQuestion
       │◀── คำตอบพร้อม citation ──────────────│
       │                                        │
       │ [วนซ้ำ max_turn_per_experts ครั้ง]     │
```

**Prompt: `WarmStartModerator`**
```
You are a moderator in a roundtable discussion. The goal is to chat with
multiple experts to discuss the facts and background of the topic to
familiarize the audience with the topic.
You will be presented with the topic, the history of question you have
already asked, and the current expert you are discussing with.
Based on these information, generate the next question for the current
expert to further the discussion.

The output should only include the next question for the current expert.

Topic for roundtable discussion: {topic}
Experts you have already interacted with: {history}
Expert you are talking with: {current_expert}
→ Next question for the expert: [question]
```

### ขั้นที่ 1.4 — สร้าง Outline และ Knowledge Base

```
บทสนทนาจาก Expert ↔ Moderator
           │
           ▼
  ┌──────────────────────────────────────────────┐
  │ GenerateWarmStartOutlineModule                │
  │   1. WritePageOutline (draft จากความรู้ LLM) │
  │   2. GenerateWarmStartOutline (ปรับจากสนทนา) │
  └──────────────────────────────────────────────┘
           │
           ▼
  Knowledge Base (Mind Map)
  ├── root
  │   ├── ประวัติ
  │   │   ├── ยุคต้น [snippet 1, 2]
  │   │   └── ยุคสงคราม [snippet 3, 4, 5]
  │   ├── ผลกระทบ [snippet 6]
  │   └── มรดก [snippet 7, 8]
```

**Prompt: `GenerateWarmStartOutline`**
```
Generate a outline of the wikipedia-like report from a roundtable discussion.
You will be presented discussion points in the conversation and corresponding
queries.
You will be given a draft outline which you can borrow some inspiration.
Do not include sections that are not mentioned in the given discussion history.
Use "#" for section headings, "##" for subsection headings, etc.
The organization of outline should adopt wikipedia style.

The topic discussed: {topic}
Draft outline you can reference to: {draft}
Discussion history: {conv}
→ Write the conversation outline:
```

### ขั้นที่ 1.5 — Report → Engaging Conversation

แปลงเนื้อหาใน Knowledge Base เป็นบทสนทนาที่น่าสนใจ เพื่อนำเสนอให้ user ตามทัน

**Prompt: `SectionToConvTranscript`**
```
You are given a section of a brief report on a specific topic. Your task
is to transform this section into an engaging opening discussion for a
roundtable conversation.
The goal is to help participants and the audience quickly understand the
key information.

Specifically, you need to:
1. Generate an engaging question that leverages section name and topic
2. Provide a brief and engaging answer (with all inline citations)

topic: {topic}
section name: {section_name}
section content: {section_content}
→ Question: [question]
→ Answer: [answer with citations]
```

---

## Phase 2 — Interactive Conversation 💬 (ละเอียดทุกขั้นตอน)

> **หัวใจของ Co-STORM:** Round table discussion ที่ user สามารถเข้าร่วมได้  
> ระบบจะเรียก `CoStormRunner.step()` วนซ้ำ `total_conv_turn` รอบ (default: 20)  
> ในแต่ละรอบ `step()` จะถูกเรียก **2 ครั้ง** — ครั้งแรกบันทึก input, ครั้งที่สอง AI ตอบ

### 💡 สรุปง่ายๆ ก่อนอ่านรายละเอียด

**Phase 2 คืออะไร?**  
คือ "วงสนทนา" ที่มี AI หลายตัว (Expert) คุยกัน โดย **user สามารถพิมพ์คำถามเข้าไปได้ทุกเมื่อ**

**มี 3 สถานการณ์หลัก:**

| สถานการณ์ | เกิดอะไรขึ้น |
|---|---|
| **User พิมพ์คำถาม** | ระบบบันทึกคำถาม → AI ค้นข้อมูลจาก Wikipedia → ตอบ → สร้าง Expert ใหม่ที่เกี่ยวกับคำถาม |
| **User กด SKIP** | AI จำลองเป็น user ถามคำถามแทน → แล้ว AI ตอบเหมือนกัน |
| **Expert ตอบกันไป ≥3 ครั้ง** | Moderator (พิธีกร) เข้ามาเปลี่ยนหัวข้อ โดยหาข้อมูลที่ยังไม่ได้พูดถึง |

**ทุกรอบ ข้อมูลที่ได้จะถูกใส่เข้า "Mind Map" (โครงสร้างความรู้แบบต้นไม้) อัตโนมัติ**

```
สรุป loop ง่ายๆ:
User ถาม (หรือ AI ถามแทน)
  → AI Expert ค้นข้อมูล + ตอบ
    → ใส่ข้อมูลเข้า Mind Map
      → Expert คนถัดไปตอบเพิ่ม (วน round-robin)
        → ถ้าวนนานเกินไป → Moderator เปลี่ยนหัวข้อ
```


### สถาปัตยกรรม Agent ทั้งหมด

```
┌─────────────────────────────────────────────────────────────┐
│                    DiscourseManager                          │
│                    (ผู้ตัดสินนโยบาย)                         │
│                         │                                    │
│    ┌────────────────────┼────────────────────┐               │
│    ▼                    ▼                    ▼               │
│ Moderator        CoStormExpert(s)      SimulatedUser        │
│ (ถามคำถามใหม่   (ตอบ/ถาม/ขยาย       (จำลอง user           │
│  เปลี่ยนทิศทาง)  ข้อมูล)              กรณี user skip)       │
│                                                              │
│  + General Knowledge Provider (Expert พิเศษ)                │
│  + PureRAGAgent (baseline comparison)                        │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
                  Knowledge Base
                  (Mind Map — อัปเดตทุก turn)
```

---

### สิ่งที่เกิดขึ้นเมื่อ User พิมพ์คำถาม (Step-by-Step)

> ตัวอย่าง: User พิมพ์ **"ศึกยุทธหัตถีเกิดขึ้นเมื่อไหร่?"**

---

#### 🔵 Step 1: บันทึกคำถาม User (ไม่เรียก AI เลย)

```
costorm_runner.step(user_utterance="ศึกยุทธหัตถีเกิดขึ้นเมื่อไหร่?")
```

**Code: engine.py บรรทัด 702-709**

```
1. ปิด moderator_override
   → discourse_manager.next_turn_moderator_override = False
   → หมายถึง: turn ถัดไป Moderator จะไม่ถูกบังคับให้ถามคำถาม

2. สร้าง ConversationTurn
   → role = "Guest"
   → raw_utterance = "ศึกยุทธหัตถีเกิดขึ้นเมื่อไหร่?"
   → utterance_type = "Original Question"

3. เพิ่มเข้า conversation_history
   → conversation_history.append(conv_turn)

4. return conv_turn ทันที ← ❌ ไม่มี LLM call เลย!
```

---

#### 🟢 Step 2: AI ตอบคำถาม (เรียก step() อีกครั้ง ไม่มี user_utterance)

```
costorm_runner.step()    ← ไม่มี user_utterance → AI จัดการเอง
```

##### ขั้น 2.1 — DiscourseManager ตัดสินนโยบาย

**Code: engine.py บรรทัด 461-502 → get_next_turn_policy()**

DiscourseManager เช็คเงื่อนไขตามลำดับ:

```
✅ เมื่อ user เพิ่งถามคำถาม ระบบจะเดินตาม path นี้:

1. simulate_user?                              → ❌ NO
2. rag_only_baseline_mode?                     → ❌ NO
3. moderator_override?                         → ❌ NO (ถูกปิดใน Step 1)
4. Expert ตอบต่อกัน ≥ 3 ครั้ง?                 → ❌ NO (user เพิ่งถาม)
5. เข้า else block:
   _is_last_turn_questioning()?                → ✅ YES!
   (เพราะ user utterance_type = "Original Question")

   ผลลัพธ์:
   → agent = General Knowledge Provider       ← ตอบก่อน
   → should_update_experts_list = True         ← สร้าง Expert ใหม่ตาม focus
   → should_polish_utterance = True            ← ขัดเกลาคำตอบ
   → should_reorganize_knowledge_base = False  ← ไม่ reorganize
```

| TurnPolicySpec Field | ค่า |
|---|---|
| `agent` | `General Knowledge Provider` |
| `should_update_experts_list` | `True` |
| `should_polish_utterance` | `True` |
| `should_reorganize_knowledge_base` | `False` |

---

##### ขั้น 2.2 — General Knowledge Provider สร้าง utterance

**Code: co_storm_agents.py → CoStormExpert.generate_utterance()**

General Knowledge Provider เป็น `CoStormExpert` ที่มี role = `"General Knowledge Provider"`  
ทำงาน **3 ขั้นตอนย่อย:**

---

**2.2.1 — Action Planning (วางแผน)**

```
เพราะ last turn = "Original Question" (user ถาม)
→ ข้ามขั้น GenExpertActionPlanning ทันที!
→ action_type = "Potential Answer" อัตโนมัติ
→ action_content = "ศึกยุทธหัตถีเกิดขึ้นเมื่อไหร่?" (ใช้คำถาม user เลย)
```

> **Code จริง (costorm_expert_utterance_generator.py:111-116):**
> ```python
> if last_conv_turn.utterance_type in ["Original Question", "Information Request"]:
>     action_type = "Potential Answer"
>     action_content = last_utterance  # ← ใช้คำถาม user ตรงๆ
> ```
> ⚡ ประหยัด 1 LLM call — ไม่ต้องคิดว่าจะทำอะไร เพราะ user ถามมาก็ต้อง "ตอบ"

> **หมายเหตุ:** ถ้ารอบก่อนเป็น "คำตอบ" จาก Expert อื่น (ไม่ใช่คำถาม) → จะเรียก `GenExpertActionPlanning` เพื่อคิดว่าจะตอบ/ถามมเพิ่ม/ขยายข้อมูล

**Prompt `GenExpertActionPlanning` (ใช้เมื่อรอบก่อนไม่ใช่คำถาม):**
```
You are an invited speaker in the round table conversation. Your task is
to make a very short note to your assistant to help you prepare for your
turn in the conversation.
You will be given the topic, your expertise, and the conversation history.
Take a look at conversation history, especially last few turns, then let
your assistant prepare the material with one of following ways.
1. Original Question: Initiates a new question
2. Further Details: Provides additional information
3. Information Request: Requests information from other speakers
4. Potential Answer: Offers a possible solution or answer

Strictly follow format: [type of contribution]: [one sentence description]

topic of discussion: {topic}
You are invited as: {expert}
Discussion history: {summary}
Last utterance in the conversation: {last_utterance}
→ [type]: [description]
```

---

**2.2.2 — AnswerQuestionModule (ค้นหา + สังเคราะห์คำตอบ)**

```
คำถาม: "ศึกยุทธหัตถีเกิดขึ้นเมื่อไหร่?"
           │
           ▼ 🤖 LLM call ①
  QuestionToQuery
  → Output:
    - ศึกยุทธหัตถี สมเด็จพระนเรศวร ปี
    - ยุทธหัตถี หนองสาหร่าย
           │
           ▼ 🗄️ Vector Store Search
  HybridWikipediaRM.retrieve(queries)
  → Dense Vector Search + BM25
  → top-10 snippets เช่น:
    [1] "ศึกยุทธหัตถีเกิดขึ้นในปี พ.ศ. 2135..."
    [2] "สมเด็จพระนเรศวรทรงกระทำยุทธหัตถีกับพระมหาอุปราชา..."
    [3] "สมรภูมิหนองสาหร่าย จ.สุพรรณบุรี..."
           │
           ▼ 🤖 LLM call ②
  AnswerQuestion
  → Output:
    "ศึกยุทธหัตถีเกิดขึ้นในปี พ.ศ. 2135 ณ ทุ่งหนองสาหร่าย[1]
     สมเด็จพระนเรศวรทรงกระทำยุทธหัตถีกับพระมหาอุปราชาแห่งพม่า[2]..."
```

**Prompt: `QuestionToQuery`**
```
You want to answer the question or support a claim using Google search.
What do you type in the search box?
The question is raised in a round table discussion on a topic.
The question may or may not focus on the topic itself.
Write queries in the format:
- query 1
- query 2
...

Topic context: {topic}
I want to collect information about: {question}
→ Queries:
```

**Prompt: `AnswerQuestion`**
```
You are an expert who can use information effectively. You have gathered
the related information and will now use the information to form a response.
Make your response as informative as possible and make sure every sentence
is supported by the gathered information.
If gathered information is not directly related, provide the most relevant
answer based on available information, and explain any limitations or gaps.
Use [1], [2], ..., [n] in line.
Do NOT include References/Sources section. The style should be formal.

Topic: {topic}
You want to provide insight on: {question}
Gathered information: {info}
Style of your response should be: {style}
→ Now give your response (use many sources, do not hallucinate.)
```

---

**2.2.3 — Polish Utterance (ขัดเกลาให้เป็นธรรมชาติ)**

```
           ▼ 🤖 LLM call ③
  ConvertUtteranceStyle
  → Input:
    expert = "General Knowledge Provider"
    action = "Potential Answer about: ศึกยุทธหัตถีเกิดขึ้นเมื่อไหร่?"
    prev   = "ศึกยุทธหัตถีเกิดขึ้นเมื่อไหร่?" (คำถาม user)
    content = "ศึกยุทธหัตถีเกิดขึ้นในปี พ.ศ. 2135...[1][2]" (raw answer)
    
  → Output:
    "คำถามดีมากครับ ศึกยุทธหัตถีเกิดขึ้นเมื่อ พ.ศ. 2135 ที่ทุ่งหนองสาหร่าย[1]
     เป็นการรบตัวต่อตัวระหว่างพระนเรศวรกับพระมหาอุปราชา[2]..."
```

**Prompt: `ConvertUtteranceStyle`**
```
You are an invited speaker in the round table conversation.
Your task is to make the question or the response more conversational and
engaging to facilitate the flow of conversation.
Note that this is ongoing conversation so no need to have welcoming and
concluding words. Previous speaker utterance is provided only for making
the conversation more natural.
Note that do not hallucinate and keep the citation index like [1] as it is.

You are invited as: {expert}
You want to contribute to conversation by: {action}
Previous speaker said: {prev}
Question or response you want to say: {content}
→ Your utterance (keep citations, prefer shorter answers):
```

---

##### ขั้น 2.3 — อัปเดตรายชื่อ Expert (เพราะ should_update_experts_list = True)

**Code: engine.py บรรทัด 731-738**

เมื่อ user ถามคำถามใหม่ → ระบบสร้าง Expert ใหม่ที่เหมาะกับ focus นั้น:

```
           ▼ 🤖 LLM call ④
  GenerateExpertWithFocus
  → Input:
    topic = "สมเด็จพระนเรศวร"
    focus = "ศึกยุทธหัตถีเกิดขึ้นเมื่อไหร่?"  (คำถาม user)
    background_info = "ศึกยุทธหัตถีเกิดขึ้นเมื่อ พ.ศ. 2135..." (คำตอบ)

  → Output:
    1. Military Historian: เน้นการรบและยุทธศาสตร์
    2. Cultural Researcher: เน้นผลกระทบต่อวัฒนธรรมและความเชื่อ
```

> ⚠️ Expert เดิมถูก **แทนที่ทั้งหมด** ด้วย Expert ใหม่ที่เกี่ยวกับ focus!  
> turn ถัดๆ ไป Expert เหล่านี้จะผลัดกันตอบแบบ round-robin

**Prompt: `GenerateExpertWithFocus`**
```
You need to select a group of speakers who will be suitable to have
roundtable discussion on the [topic] of specific [focus].
You may consider inviting speakers having opposite stands on the topic;
speakers representing different interest parties;
Ensure that the selected speakers are directly connected to the specific
context and scenario provided.
Use the background information provided. For each speaker, add a description
of their interests and what they will focus on during the discussion.
Strictly follow format:
1. [speaker 1 role]: [speaker 1 short description]
2. [speaker 2 role]: [speaker 2 short description]

Topic of interest: {topic}
Background information: {background_info}
Discussion focus: {focus}
Number of speakers needed: {topN}
→ experts: [list]
```

---

##### ขั้น 2.4 — สอดข้อมูลเข้า Knowledge Base (Mind Map)

**Code: engine.py บรรทัด 747-751**

```
           ▼ 🤖 LLM call ⑤ (×N snippets)
  InsertInformationModule
  สำหรับแต่ละ cited snippet จาก คำตอบ:

  InsertInformation Prompt:
  "given the mind map structure, where should this info go?
    Quest: ศึกยุทธหัตถีเกิดขึ้นเมื่อไหร่?
    Tree:
    # root
      ## ประวัติ
        ### ยุคต้น
        ### ยุคสงคราม    ← น่าจะอยู่ตรงนี้
      ## ผลกระทบ
      ## มรดก"

  → Output: "ยุคสงคราม"
  → สอด snippet เข้า node "ยุคสงคราม"
```

**Prompt: `InsertInformation`**
```
You are given a mind map organized into a hierarchical tree structure.
Your task is to decide where the new information snippet should be placed.
Given the question and query leads to this info, and the mind map structure,
select the best section to insert.

Question and query leads to this info: {intent}
Tree structure: {structure}
→ Choice:
```

---

##### ขั้น 2.5 — Reorganize Knowledge Base (ไม่ทำรอบนี้)

```
should_reorganize_knowledge_base = False
→ ❌ ข้ามขั้นนี้ — ExpandNodeModule จะไม่ถูกเรียก
→ จะทำเมื่อ Moderator เป็นคนถามเท่านั้น
```

> **เมื่อไร Reorganize จะทำงาน?**  
> เมื่อ Moderator ถูกเรียก (Expert ตอบ ≥3 ครั้งต่อกัน) → `should_reorganize_knowledge_base = True``
> → `ExpandNodeModule` จะเช็คทุก node ว่ามี snippets > 10 ชิ้นไหม → ถ้ามี จะแตก sub-nodes

**Prompt: `ExpandSection` (ใช้เมื่อ reorganize)**
```
Your task is to expand a section in the mind map by creating new subsections.
You will be given a list of question and query used to collect information.

If there's no need to expand, output None.

→ Expanded subsection names:
```

---

### สรุป LLM Calls เมื่อ User พิมพ์ 1 คำถาม

| # | LLM Call | Module | ทำอะไร |
|---|---|---|---|
| - | *(ไม่มี)* | Step 1 | บันทึกคำถาม user เข้า history |
| ① | `QuestionToQuery` | AnswerQuestionModule | แปลงคำถาม → search queries |
| ② | `AnswerQuestion` | AnswerQuestionModule | สังเคราะห์คำตอบจาก snippets |
| ③ | `ConvertUtteranceStyle` | CoStormExpert | Polish ให้เป็นภาษาธรรมชาติ |
| ④ | `GenerateExpertWithFocus` | GenerateExpertModule | สร้าง Expert ใหม่ตาม focus |
| ⑤ | `InsertInformation` (×N) | InsertInformationModule | สอดข้อมูลเข้า Mind Map |

**รวม: ~5-7 LLM calls ต่อ 1 คำถามจาก user**

---

### เมื่อ User กด SKIP (ไม่พิมพ์อะไร) — เปรียบเทียบ

เมื่อ user ไม่พิมพ์ ระบบจะเรียก `SimulatedUser` แทน:

```
costorm_runner.step(simulate_user=True, simulate_user_intent="...")
```

SimulatedUser ใช้ **prompt เดียวกับ STORM** — `AskQuestionWithPersona`:

```
persona = "researcher with interest in {simulate_user_intent}"
→ สร้างคำถามใน 1 LLM call → บันทึกเป็น Guest
→ แล้วเรียก step() อีกครั้งเพื่อให้ AI ตอบ (เหมือน flow ข้างบน)
```

---

### เมื่อ Expert ตอบไป 3+ ครั้ง → Moderator เข้ามา

ถ้าไม่มีคำถามใหม่ (user ไม่พิมพ์ หรือ Expert แค่ตอบกันไปมา) ≥3 รอบ:

```
DiscourseManager ตัดสินใจ:
   _should_generate_question() → ✅ YES (consecutive_non_questioning ≥ 3)
   → agent = Moderator
   → should_reorganize_knowledge_base = True
```

**Moderator ทำงาน:**
```
1. หา unused snippets (ค้นมาแต่ยังไม่ cite)
   → rank ด้วย:
     score = (1 - query_sim)^0.5 × (1 - cited_sim)^0.5 × claim_filter
           │
           ▼ 🤖 LLM call
2. GroundedQuestionGeneration
   → สร้างคำถามเปลี่ยนมุมมองจาก unused snippets
           │
           ▼ 🤖 LLM call
3. ConvertUtteranceStyle
   → polish คำถามให้เป็นธรรมชาติ
           │
           ▼
4. อัปเดต Knowledge Base + Reorganize (ExpandNodeModule)
```

**Prompt: `GroundedQuestionGeneration`**
```
Your job is to find next discussion focus in a roundtable conversation.
You will be given previous conversation summary and some information that
might assist you discover new discussion focus.
Note that the new focus should bring new angle and avoid repetition.
Grounded on available information, push boundaries for broader exploration.
Natural flow from last utterance. Use [1][2] inline.

topic: {topic}
Discussion history: {summary}
Available information: {unused_snippets}
Last utterance in the conversation: {last_utterance}
→ Next discussion focus in the format of one sentence question:
```

---

### เมื่อ Expert ตอบต่อจาก Expert อีกคน (round-robin)

ถ้ารอบก่อนคือ Expert ตอบ (ไม่ใช่คำถาม):

```
DiscourseManager:
   _is_last_turn_questioning() → ❌ NO
   → agent = experts.pop(0)       ← หมุน Expert ถัดไป
   → experts.append(agent)        ← เอาไปต่อท้าย queue
   → should_update_experts_list = False
   → should_polish_utterance = True
```

**Expert คนนี้ต้องเรียก `GenExpertActionPlanning`** (เพราะรอบก่อนไม่ใช่คำถาม):

```
           ▼ 🤖 LLM call
  GenExpertActionPlanning
  → ตัดสินใจ: "Further Details: ให้ข้อมูลเพิ่มเติมเรื่อง..."
           │
           ▼ 🤖 LLM calls (QuestionToQuery + AnswerQuestion)
  AnswerQuestionModule
           │
           ▼ 🤖 LLM call
  ConvertUtteranceStyle (polish)
           │
           ▼ 🤖 LLM call(s)
  InsertInformationModule (สอดข้อมูลเข้า Mind Map)
```

**รวม: ~5-8 LLM calls ต่อ 1 turn (เมื่อ Expert ตอบต่อ)**

---

### สรุป Flow ทั้งหมดใน Phase 2

```
  ┌─────────────────────────────────────────────────────┐
  │              Phase 2 Loop (20 turns)                 │
  │                                                       │
  │  แต่ละ turn:                                          │
  │  ┌─────────────────────────────────────────────────┐  │
  │  │ Input: user พิมพ์ หรือ กด SKIP?                 │  │
  │  │                                                   │  │
  │  │ ├─ User พิมพ์ → step(user_utterance) → บันทึก   │  │
  │  │ └─ User SKIP → step(simulate_user) → AI ถามแทน │  │
  │  └──────────────────────┬──────────────────────────┘  │
  │                         ▼                              │
  │  ┌─────────────────────────────────────────────────┐  │
  │  │ step() → DiscourseManager ตัดสินว่าใครพูด       │  │
  │  │                                                   │  │
  │  │ ├─ User เพิ่งถาม → General Knowledge Provider   │  │
  │  │ │    + สร้าง Expert ใหม่                          │  │
  │  │ │                                                 │  │
  │  │ ├─ Expert ตอบก่อนหน้า → Expert ถัดไป (rotation)  │  │
  │  │ │    + Action Planning + ค้น + ตอบ                │  │
  │  │ │                                                 │  │
  │  │ └─ Expert ตอบ ≥3 ครั้ง → Moderator inject คำถาม  │  │
  │  │      + unused snippets ranking + reorganize KB   │  │
  │  └──────────────────────┬──────────────────────────┘  │
  │                         ▼                              │
  │  ┌─────────────────────────────────────────────────┐  │
  │  │ อัปเดต Knowledge Base (Mind Map)                 │  │
  │  │ InsertInformationModule → สอดข้อมูลเข้า node     │  │
  │  │ ExpandNodeModule → แตก sub-node ถ้าจำเป็น        │  │
  │  └─────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────┘
```

---

## Phase 3 — Report Generation 📄

> **เป้าหมาย:** แปลง Knowledge Base (Mind Map) เป็นบทความ Wikipedia

```
Knowledge Base (Mind Map)
├── ประวัติ [snippets 1,2]
│   ├── ยุคต้น [snippets 3,4,5]
│   └── ยุคสงคราม [snippets 6,7]
├── ผลกระทบ [snippets 8,9]
└── มรดก [snippets 10,11,12]
           │
           ▼ (parallel per node)
     แต่ละ node → WriteSection → เขียนเนื้อหาพร้อม citation
           │
           ▼
     รวมเป็นบทความตาม hierarchy ของ Mind Map
```

**Prompt: `WriteSection` (Co-STORM version)**
```
Write a Wikipedia section based on the collected information.
You will be given the topic, the section you are writing and relevant
information.
Each information will be provided with the raw content along with question
and query lead to that information.
Format: Use [1], [2], ..., [n] inline citations.
Do NOT include References/Sources section.

The collected information: {info}
The topic of the page: {topic}
The section you need to write: {section}
→ Write the section with proper inline citations
  (Don't include page title, section name, or try to write other sections):
```

---

## สรุปตาราง Agent ทั้งหมดใน Co-STORM

| # | Agent | LLM Config | บทบาท | ใช้เมื่อ |
|---|---|---|---|---|
| 1 | **WarmStartModerator** | `question_asking_lm` | ถามคำถามให้ Expert ตอนเตรียมข้อมูล | Phase 1 (Warm Start) |
| 2 | **GenerateExpertModule** (General) | `discourse_manage_lm` | สร้าง Expert agents จาก background info | Phase 1 + Phase 2 |
| 3 | **GenerateExpertModule** (WithFocus) | `discourse_manage_lm` | สร้าง Expert ใหม่ตาม discussion focus | Phase 2 (หลังคำถามใหม่) |
| 4 | **CoStormExpert** | `discourse_manage_lm` + `question_answering_lm` + `utterance_polishing_lm` | วางแผน → ค้น+ตอบ → polish | Phase 2 (ตอบในวงสนทนา) |
| 5 | **Moderator** | `question_asking_lm` | หา unused snippets → สร้างคำถามเปลี่ยนมุมมอง | Phase 2 (เมื่อ Expert ตอบวนไป) |
| 6 | **SimulatedUser** | `question_answering_lm` | จำลอง user ถามคำถาม (เมื่อ user กด SKIP) | Phase 2 |
| 7 | **General Knowledge Provider** | `question_answering_lm` | Expert default ตอบคำถามทั่วไป | Phase 2 (คำถามใหม่) |
| 8 | **InsertInformationModule** | `knowledge_base_lm` | สอดข้อมูลเข้า Mind Map | Phase 2 (ทุก turn) |
| 9 | **ExpandNodeModule** | `knowledge_base_lm` | แตก sub-node เมื่อ node ใหญ่เกินไป | Phase 2 |
| 10 | **ArticleGenerationModule** | `knowledge_base_lm` | เขียน section จาก Mind Map | Phase 3 |
| 11 | **ReportToConversation** | `knowledge_base_lm` | แปลง report เป็นบทสนทนาแนะนำ | Phase 1 (ตอนจบ) |

---

## สรุป DSPy Signatures (Prompts) ทั้งหมด

| # | Signature | ใช้โดย | หน้าที่ |
|---|---|---|---|
| 1 | `GenerateExpertGeneral` | GenerateExpertModule | สร้าง Expert จาก background |
| 2 | `GenerateExpertWithFocus` | GenerateExpertModule | สร้าง Expert ตาม focus |
| 3 | `WarmStartModerator` | WarmStartConversation | ถามคำถามตอน warm start |
| 4 | `WritePageOutline` | GenerateWarmStartOutlineModule | Draft outline |
| 5 | `GenerateWarmStartOutline` | GenerateWarmStartOutlineModule | Outline จากบทสนทนา |
| 6 | `SectionToConvTranscript` | ReportToConversation | แปลง section → Q&A |
| 7 | `GenExpertActionPlanning` | CoStormExpert | วางแผน action |
| 8 | `QuestionToQuery` | AnswerQuestionModule | แปลงคำถาม → query |
| 9 | `AnswerQuestion` | AnswerQuestionModule | สังเคราะห์คำตอบ |
| 10 | `ConvertUtteranceStyle` | Expert + Moderator | Polish คำพูดให้เป็นธรรมชาติ |
| 11 | `GroundedQuestionGeneration` | Moderator | สร้างคำถามจาก unused info |
| 12 | `KnowledgeBaseSummary` | Moderator | สรุป Knowledge Base |
| 13 | `AskQuestionWithPersona` | SimulatedUser | จำลอง user ถามคำถาม |
| 14 | `InsertInformation` | InsertInformationModule | ตัดสินใจ placement ใน Mind Map |
| 15 | `InsertInformationCandidateChoice` | InsertInformationModule | เลือก candidate node |
| 16 | `ExpandSection` | ExpandNodeModule | แตก sub-nodes |
| 17 | `WriteSection` | ArticleGenerationModule | เขียนเนื้อหาแต่ละ section |

---

## Call Stack จาก Web API → Codebase

```
POST /api/generate  (web/app.py)
└── run_costorm(topic, client_id, settings)
      └── costorm_interactive.py: run_costorm_interactive()
            │
            ├── [Phase 1] CoStormRunner.warm_start()    (engine.py)
            │     └── WarmStartModule.initiate_warm_start()
            │           │
            │           ├── Step 1: WarmStartConversation.forward()
            │           │     ├── AnswerQuestionModule("Background info...")  → LLM ①②
            │           │     ├── GenerateExpertModule(general)               → LLM ③
            │           │     └── per expert (parallel):
            │           │           loop max_turn_per_experts:
            │           │           ├── WarmStartModerator                    → LLM ④
            │           │           └── AnswerQuestionModule                  → LLM ⑤⑥
            │           │
            │           ├── Step 2: GenerateWarmStartOutlineModule.forward()
            │           │     ├── WritePageOutline (draft)                    → LLM ⑦
            │           │     └── GenerateWarmStartOutline (refined)          → LLM ⑧
            │           │
            │           ├── Step 3: knowledge_base.insert_from_outline + update_from_conv_turn
            │           │     └── InsertInformationModule × N turns           → LLM ⑨...
            │           │
            │           ├── Step 4: knowledge_base.to_report()
            │           │     └── ArticleGenerationModule (WriteSection) × N  → LLM ⑩...
            │           │
            │           └── Step 5: ReportToConversation
            │                 └── SectionToConvTranscript × N sections        → LLM ⑪...
            │
            ├── [Phase 2] loop total_conv_turn (default: 20):
            │     └── CoStormRunner.step()
            │           │
            │           ├── ถ้า user_utterance → บันทึกเป็น Guest + return
            │           │
            │           ├── DiscourseManager.get_next_turn_policy()
            │           │     └── ตัดสินใจว่า agent ไหนจะพูด
            │           │
            │           ├── Agent.generate_utterance()
            │           │     ├── Moderator:
            │           │     │     ├── _get_sorted_unused_snippets()
            │           │     │     └── GroundedQuestionGenerationModule
            │           │     │           ├── GroundedQuestionGeneration       → LLM
            │           │     │           └── ConvertUtteranceStyle            → LLM
            │           │     │
            │           │     ├── CoStormExpert:
            │           │     │     ├── GenExpertActionPlanning                → LLM
            │           │     │     ├── AnswerQuestionModule
            │           │     │     │     ├── QuestionToQuery                  → LLM
            │           │     │     │     ├── retriever.retrieve()             → Vector Store
            │           │     │     │     └── AnswerQuestion                   → LLM
            │           │     │     └── ConvertUtteranceStyle (polish)         → LLM
            │           │     │
            │           │     └── SimulatedUser:
            │           │           └── AskQuestionWithPersona                 → LLM
            │           │
            │           ├── _update_expert_list_from_utterance() (ถ้าเป็นคำถามใหม่)
            │           │     └── GenerateExpertWithFocus                      → LLM
            │           │
            │           ├── knowledge_base.update_from_conv_turn()
            │           │     └── InsertInformationModule                      → LLM
            │           │
            │           └── knowledge_base.reorganize() (ถ้า Moderator turn)
            │                 └── ExpandNodeModule                             → LLM (ถ้าจำเป็น)
            │
            └── [Phase 3] CoStormRunner.generate_report()
                  └── knowledge_base.to_report()
                        └── ArticleGenerationModule.forward() (parallel)
                              └── WriteSection × N nodes                      → LLM
```

---

## เปรียบเทียบ STORM vs Co-STORM

| หัวข้อ | STORM | Co-STORM |
|---|---|---|
| **User participation** | ❌ ไม่มี (อัตโนมัติทั้งหมด) | ✅ ร่วมสนทนาได้ทุกรอบ |
| **Knowledge storage** | InformationTable (flat) | Knowledge Base / Mind Map (hierarchical) |
| **Agent types** | WikiWriter + TopicExpert (2 ตัว) | Expert + Moderator + SimulatedUser + GenerateExpert (5+ ตัว) |
| **Warm start** | ❌ ไม่มี | ✅ mini-STORM สร้างพื้นฐาน |
| **Discourse management** | ตายตัว (วนรอบ) | DiscourseManager ตัดสินใจ dynamic |
| **Expert generation** | สร้างครั้งเดียว (Persona) | สร้างใหม่ตาม focus ที่เปลี่ยนไป |
| **Article generation** | outline → section → polish | Mind Map → section (ไม่มี separate polish) |
| **LLM calls ต่อบทความ** | ~70-100 | ~150-300+ (ขึ้นกับจำนวน turn) |

---

## จำนวน LLM Calls โดยประมาณ

| Phase | LLM Calls |
|---|---|
| Phase 1 (Warm Start) | ~20-40 (background + expert QA + outline + insert + report + conv) |
| Phase 2 (per turn) | ~3-6 (action plan + QA + polish + insert + possible expert gen) |
| Phase 2 (20 turns) | ~60-120 |
| Phase 3 (Report) | ~5-15 (1 per Mind Map node) |
| **รวมทั้งหมด** | **~85-175 LLM calls ต่อบทความ** |
