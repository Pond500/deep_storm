# Co-STORM Outline — สรุป Logic การสร้างและจัดการ Outline (Mind Map)

## Outline ใน Co-STORM คืออะไร?

ใน Co-STORM **Outline = Mind Map = Knowledge Base** เป็นสิ่งเดียวกัน  
มันคือ **โครงสร้างต้นไม้ (tree)** ที่เก็บข้อมูลทั้งหมดที่ agent ค้นมาได้

```
root
├── ประวัติ                    ← node (หัวข้อ)
│   ├── ยุคต้น                 ← sub-node
│   │   └── [snippet 1, 2]    ← ข้อมูลที่เก็บ
│   └── ยุคสงคราม
│       └── [snippet 3, 4, 5]
├── ผลกระทบ
│   └── [snippet 6]
└── มรดก
    └── [snippet 7, 8]
```

**แต่ละ node** = หัวข้อ เช่น "ประวัติ", "ยุคต้น"  
**content ของ node** = set ของ snippet index ที่ถูกจัดเข้ามา

---

## Outline ถูกสร้างเมื่อไร?

Outline ถูกสร้าง **1 ครั้ง** ใน **Phase 1 (Warm Start) ขั้นที่ 4** แล้ว**ขยาย/ปรับ**ตลอด Phase 2

```
Phase 1 ขั้น 4:
  สร้าง Outline เริ่มต้น
  └── ใช้ 2 LLM calls

Phase 2 ทุกรอบ:
  ใส่ข้อมูลเข้า node ที่มีอยู่ (InsertInformationModule)
  ถ้า node ใหญ่เกินไป → แตก sub-node (ExpandNodeModule)
```

---

## ขั้นตอนการสร้าง Outline (Phase 1 ขั้น 4)

### Step 1: สร้าง Draft Outline จากความรู้ของ LLM

ใช้ `WritePageOutline` (ยืมมาจาก STORM) — ให้ LLM คิด outline จากหัวข้อเลย ไม่ต้องดูข้อมูลอะไร

**Prompt: `WritePageOutline`**
```
Write an outline for a Wikipedia page.
Here is the format of your writing:
1. Use "#" Title" to indicate section title,
   "##" Title" to indicate subsection title,
   "###" Title" to indicate subsubsection title, and so on.
2. Do not include other information.
3. Do not include topic name itself in the outline.

The topic you want to write: {topic}
→ Write the Wikipedia page outline:
```

**ตัวอย่าง Output:**
```
# ประวัติ
## ยุคต้น
## ยุคสงคราม
# ผลกระทบ
# มรดกทางวัฒนธรรม
# อ้างอิง          ← จะถูกลบทิ้ง
```

> **หมายเหตุ:** Draft นี้มาจากความรู้ของ LLM โดยตรง ยังไม่ได้ดูข้อมูลจาก round table  
> มีไว้เป็น "แม่แบบ" ให้ step ถัดไป

---

### Step 2: สร้าง Refined Outline จากบทสนทนา

ใช้ `GenerateWarmStartOutline` — ให้ LLM ดู **draft** + **ประวัติการสนทนาจาก Expert** แล้วสร้าง outline ใหม่

**ก่อนเรียก LLM ระบบจะเตรียมข้อมูล:**

```python
# แปลงบทสนทนาเป็น string
def extract_questions_and_queries(conv):
    for turn in conv:
        focus = turn.claim_to_make       # คำถามที่ถาม
        queries = turn.queries           # search queries ที่ใช้ค้น
        → "Discussion focus 1: {focus}\n\tQuery 1: {q1}\n\tQuery 2: {q2}"
```

**ตัวอย่าง Discussion History ที่ส่งให้ LLM:**
```
Discussion focus 1: Background information about สมเด็จพระนเรศวร
    Query 1: สมเด็จพระนเรศวร ประวัติ
    Query 2: พระนเรศวร กษัตริย์ อยุธยา
Discussion focus 2: ศึกยุทธหัตถีมีความสำคัญอย่างไร?
    Query 1: ยุทธหัตถี สมเด็จพระนเรศวร
    Query 2: ศึกหนองสาหร่าย
Discussion focus 3: ผลกระทบต่อการเมืองภูมิภาค
    Query 1: ผลกระทบ สงคราม พม่า อยุธยา
```

**Prompt: `GenerateWarmStartOutline`**
```
Generate a outline of the wikipedia-like report from a roundtable discussion.
You will be presented discussion points in the conversation and
corresponding queries.
You will be given a draft outline which you can borrow some inspiration.
Do not include sections that are not mentioned in the given discussion history.
Use "#" to denote section headings, "##" to denote subsection headings, etc.
Follow these guidelines:
1. Use "#" for section titles, "##" for subsection titles, etc.
2. Do not include any additional information.
3. Exclude the topic name from the outline.
The organization of outline should adopt wikipedia style.

The topic discussed: {topic}
Draft outline you can reference to: {draft}        ← จาก Step 1
Discussion history: {discussion_history}            ← จากบทสนทนา Expert
→ Write the conversation outline:
```

**ตัวอย่าง Output:**
```
# ประวัติ
## พระราชประวัติ
## การขึ้นครองราชย์
# ศึกยุทธหัตถี
## สาเหตุ
## เหตุการณ์
# ผลกระทบทางการเมือง
```

---

### Step 3: Clean Up Outline

ก่อนใช้งาน ระบบจะเรียก `ArticleTextProcessing.clean_up_outline()` เพื่อ:

```python
# 1. แปลง bullet points เป็น heading
"-  สาเหตุ"  →  "## สาเหตุ"

# 2. ลบ sections ที่ไม่ต้องการ
"# References"     → ลบ
"# See also"       → ลบ
"# External links" → ลบ
"# Bibliography"   → ลบ
"# Summary"        → ลบ
"# Appendix"       → ลบ

# 3. ลบ citations ใน outline
"# ศึกยุทธหัตถี [1][2]"  →  "# ศึกยุทธหัตถี"
```

---

### Step 4: แปลง Outline String → Mind Map (Tree)

ระบบเรียก `knowledge_base.insert_from_outline_string(outline)` เพื่อแปลง text เป็น tree:

```python
def insert_from_outline_string(outline_string):
    for line in outline_string.split("\n"):
        level = line.count("#")        # นับ # = ระดับ
        title = line.strip("# ")      # เอาชื่อ
        
        # ข้าม sections ทั่วไป
        if title.lower() in ["overview", "summary", "introduction"]:
            continue
        
        # หา parent node จาก level ก่อนหน้า
        parent = last_node_at_level[level - 1]
        
        # สร้าง node ใหม่
        new_node = insert_node(title, parent)
        last_node_at_level[level] = new_node
```

**ตัวอย่าง:**
```
Input Outline String:                     Output Tree:

# ประวัติ                                root
## พระราชประวัติ                          ├── ประวัติ (level 1)
## การขึ้นครองราชย์                       │   ├── พระราชประวัติ (level 2)
# ศึกยุทธหัตถี                           │   └── การขึ้นครองราชย์ (level 2)
## สาเหตุ                                ├── ศึกยุทธหัตถี (level 1)
## เหตุการณ์                              │   ├── สาเหตุ (level 2)
# ผลกระทบ                                │   └── เหตุการณ์ (level 2)
                                          └── ผลกระทบ (level 1)
```

---

### Step 5: ใส่ข้อมูลจากบทสนทนาเข้า Mind Map

หลังจากสร้าง tree แล้ว ระบบจะวนแต่ละ conversation turn จาก Warm Start แล้ว insert ข้อมูลเข้าไป:

```python
# สำหรับแต่ละ turn จากบทสนทนา Expert
for turn in warm_start_conversation_history:
    knowledge_base.update_from_conv_turn(
        conv_turn=turn,
        allow_create_new_node=False    # ← ห้ามสร้าง node ใหม่ตอน warm start!
    )
```

**`update_from_conv_turn` ทำอะไร:**
```
1. ดึง cited_info จาก turn (snippets ที่ถูก cite [1][2])
2. เรียก InsertInformationModule:
   → LLM ดูโครงสร้าง tree + คำถาม/query ของ snippet
   → ตัดสินใจว่า snippet นี้ควรอยู่ node ไหน
   → ใส่ snippet index เข้า node.content
3. อัปเดต citation index ใน utterance ให้ตรงกับ global uuid
```

> **สังเกต:** ตอน Warm Start ใช้ `allow_create_new_node=False`  
> หมายถึง snippet ต้องใส่เข้า node ที่มีอยู่แล้วเท่านั้น ไม่สร้าง node ใหม่

---

## Outline เปลี่ยนแปลงยังไงใน Phase 2?

### ทุก Turn: Insert ข้อมูลเข้า node

```python
knowledge_base.update_from_conv_turn(
    conv_turn=turn,
    allow_create_new_node=True    # ← Phase 2 อนุญาตให้สร้าง node ใหม่!
)
```

> **ต่างจาก Warm Start:** Phase 2 ใช้ `allow_create_new_node=True`  
> ถ้า LLM ตัดสินใจว่าไม่มี node ไหนเหมาะ → จะสร้าง node ใหม่ได้

### เมื่อ Moderator ถาม: Reorganize Mind Map

เมื่อ Moderator เข้ามา (Expert ตอบ ≥3 ครั้ง) ระบบจะ reorganize:

```python
knowledge_base.reorganize()
```

**Reorganize ทำ 5 ขั้นตอน:**

```
1. trim_empty_leaf_nodes()    → ลบ leaf node ที่ไม่มีข้อมูล
2. merge_single_child_nodes() → รวม node ที่มีลูกเดียว
3. ExpandNodeModule()          → แตก node ที่ใหญ่เกินไป (LLM call)
4. trim_empty_leaf_nodes()    → ลบอีกรอบ
5. merge_single_child_nodes() → รวมอีกรอบ
```

---

#### Reorganize ขั้น 1: ลบ Leaf Node ว่าง

```
ก่อน:                          หลัง:
root                            root
├── ประวัติ                     ├── ประวัติ
│   ├── ยุคต้น [1,2]           │   ├── ยุคต้น [1,2]
│   ├── ยุคกลาง []  ← ว่าง!   │   └── ยุคสงคราม [3,4,5]
│   └── ยุคสงคราม [3,4,5]     └── ผลกระทบ [6]
├── ผลกระทบ [6]
└── มรดก []          ← ว่าง!
```

---

#### Reorganize ขั้น 2: รวม Node ที่มีลูกเดียว

```
ก่อน:                          หลัง:
root                            root
├── สงคราม                      ├── สงคราม → ยุทธหัตถี [1,2,3]
│   └── ยุทธหัตถี [1,2,3]     └── ผลกระทบ [4]
└── ผลกระทบ [4]

(node "สงคราม" มีลูกเดียว → รวม content ของลูกเข้ามา ลบลูกทิ้ง)
```

---

#### Reorganize ขั้น 3: ExpandNodeModule (แตก Node ใหญ่)

**เมื่อไรจะแตก?**  
เมื่อ node มี snippets ≥ `node_expansion_trigger_count` (default: 10)

```python
def _find_first_node_to_expand(root, expanded_nodes):
    # DFS หา node ที่:
    # 1. มี content ≥ trigger_count (10)
    # 2. ยังไม่เคย expand
    # 3. เป็น leaf node (ไม่มีลูก) หรือ node ที่ลูกยังเล็กอยู่
```

**เมื่อเจอ node ที่ต้อง expand:**

```
1. 🤖 LLM call: ExpandSection
   ให้ LLM ดูข้อมูลใน node → คิดชื่อ sub-sections

2. สร้าง sub-nodes ใหม่

3. ย้ายข้อมูลเดิม: ลบข้อมูลออกจาก node เดิม →
   เรียก InsertInformationModule ใหม่ เพื่อจัดข้อมูลเข้า sub-node ที่เหมาะสม
```

**Prompt: `ExpandSection`**
```
Your task is to expand a section in the mind map by creating new
subsections under the given section.
You will be given a list of question and query that are used to collect
information.
Output should be subsection names where each section should serve as a
coherent and thematic organization of information and corresponding
citation numbers. These subsection names are preferred to be concise
and precise.
Output format:
subsection 1
subsection 2
subsection 3

The section you need to expand: {section}
The collected information: {info}
→ Now provide the expanded subsection names
  (If there's no need to expand, output None):
```

**ตัวอย่าง:**
```
ก่อน Expand:
ศึกยุทธหัตถี [snippet 1,2,3,4,5,6,7,8,9,10,11,12]
↑ มี 12 snippets ≥ 10 → ต้อง expand!

🤖 LLM คิด sub-sections:
→ "สาเหตุของสงคราม"
→ "เหตุการณ์การรบ"
→ "ผลลัพธ์และผลกระทบ"

หลัง Expand:
ศึกยุทธหัตถี []                          ← content ถูกย้ายออก
├── สาเหตุของสงคราม [snippet 1,3,5]     ← LLM จัดเข้าที่ใหม่
├── เหตุการณ์การรบ [snippet 2,4,6,8,10]
└── ผลลัพธ์และผลกระทบ [snippet 7,9,11,12]
```

---

## สรุป Flow ทั้งหมดของ Outline / Mind Map

```
Phase 1 Warm Start:
│
├── Step 1: 🤖 WritePageOutline
│   LLM คิด draft outline จากหัวข้อ
│   → "# ประวัติ\n## ยุคต้น\n## ยุคสงคราม\n# ผลกระทบ"
│
├── Step 2: 🤖 GenerateWarmStartOutline
│   LLM ดู draft + ประวัติสนทนา Expert → สร้าง outline ที่ตรงกับข้อมูลจริง
│   → "# ประวัติ\n## พระราชประวัติ\n# ศึกยุทธหัตถี\n## สาเหตุ"
│
├── Step 3: clean_up_outline()
│   ลบ References, See also, citations → outline สะอาด
│
├── Step 4: insert_from_outline_string()
│   แปลง text → tree structure (KnowledgeNode objects)
│
├── Step 5: update_from_conv_turn() × N turns
│   🤖 InsertInformationModule: จัดข้อมูลเข้าแต่ละ node
│   (allow_create_new_node = False)
│
└── to_report() → สร้าง report จาก Mind Map (ใช้ตอนจบ Warm Start)

Phase 2 Interactive:
│
├── ทุก Turn:
│   update_from_conv_turn()
│   🤖 InsertInformationModule: จัดข้อมูลใหม่เข้า node
│   (allow_create_new_node = True ← สร้าง node ใหม่ได้!)
│
└── เมื่อ Moderator ถาม (ทุก ~3-4 turns):
    reorganize()
    ├── ลบ leaf node ว่าง
    ├── รวม node ลูกเดียว
    ├── 🤖 ExpandNodeModule: แตก node ≥10 snippets
    ├── ลบ leaf node ว่างอีกรอบ
    └── รวม node ลูกเดียวอีกรอบ
```

---

## สรุป Prompts ที่เกี่ยวกับ Outline

| # | Prompt | ใช้เมื่อ | ทำอะไร |
|---|---|---|---|
| 1 | `WritePageOutline` | Phase 1 Step 1 | LLM คิด draft outline จากหัวข้อ |
| 2 | `GenerateWarmStartOutline` | Phase 1 Step 2 | LLM สร้าง outline จาก draft + บทสนทนา |
| 3 | `InsertInformation` | Phase 1 Step 5 + Phase 2 ทุก turn | LLM ตัดสินใจว่า snippet ใส่ node ไหน |
| 4 | `InsertInformationCandidateChoice` | Phase 1 Step 5 + Phase 2 ทุก turn | LLM เลือกจาก candidate nodes (embedding) |
| 5 | `ExpandSection` | Phase 2 (reorganize) | LLM คิดชื่อ sub-sections สำหรับ node ใหญ่ |

---

## ข้อสังเกตสำคัญ

1. **Outline ถูกสร้างจาก LLM 2 รอบ:** draft (จากความรู้ LLM) → refined (จากข้อมูลจริง)
2. **Warm Start ห้ามสร้าง node ใหม่** (allow_create_new_node=False) เพื่อให้ outline คงโครงสร้างเดิม
3. **Phase 2 อนุญาตสร้าง node ใหม่** (allow_create_new_node=True) เพราะอาจมีหัวข้อที่ไม่ได้อยู่ใน outline เดิม
4. **Node ≥10 snippets จะถูกแตก** → LLM คิด sub-sections → ข้อมูลเดิมถูกจัดใหม่
5. **Node ว่างถูกลบ + Node ลูกเดียวถูกรวม** ทุกครั้งที่ reorganize
6. **clean_up_outline ลบ sections ไม่จำเป็น** เช่น References, See also, Bibliography
