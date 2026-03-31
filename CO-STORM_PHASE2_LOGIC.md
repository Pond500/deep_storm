# Co-STORM Phase 2 — สรุป Logic "User พิมพ์" vs "User SKIP"

## ภาพรวม

Phase 2 คือ **วงสนทนาโต๊ะกลม** ที่วนซ้ำ 20 รอบ  
แต่ละรอบ ระบบเรียก `step()` **2 ครั้ง** เสมอ:

```
ครั้งที่ 1: รับ input (คำถามจาก user หรือจาก AI)
ครั้งที่ 2: AI ตอบคำถามนั้น
```

---

## กรณี 1: User พิมพ์คำถาม ✍️

```
User พิมพ์: "ศึกยุทธหัตถีเกิดขึ้นเมื่อไหร่?"
```

### step() ครั้งที่ 1 — บันทึกคำถาม

```
เรียก: step(user_utterance="ศึกยุทธหัตถีเกิดขึ้นเมื่อไหร่?")

สิ่งที่เกิดขึ้น:
  ✅ บันทึกเป็น ConversationTurn(role="Guest", type="Original Question")
  ✅ ปิด moderator_override (ไม่ให้ Moderator แทรก)
  ❌ ไม่เรียก LLM เลย
  → return ทันที
```

### step() ครั้งที่ 2 — AI ตอบ

```
เรียก: step()  ← ไม่มี argument

สิ่งที่เกิดขึ้น (ตามลำดับ):

① DiscourseManager ดูว่ารอบก่อนเป็น "คำถาม"
   → เลือก General Knowledge Provider ตอบ
   → ตั้ง flag: ต้องสร้าง Expert ใหม่

② General Knowledge Provider (ข้ามขั้น Action Planning)
   → เพราะรอบก่อนเป็นคำถาม ไม่ต้องคิดว่าจะทำอะไร → ตอบเลย!
   │
   ├─ 🤖 LLM call 1: QuestionToQuery
   │  แปลงคำถาม → คำค้น เช่น "ศึกยุทธหัตถี พ.ศ."
   │
   ├─ 🗄️ Vector Store Search
   │  ค้น Wikipedia ได้ snippets เช่น [1] [2] [3]
   │
   ├─ 🤖 LLM call 2: AnswerQuestion
   │  สังเคราะห์คำตอบจาก snippets พร้อม citation [1][2]
   │
   └─ 🤖 LLM call 3: ConvertUtteranceStyle
      ขัดเกลาให้เป็นภาษาธรรมชาติ

③ 🤖 LLM call 4: GenerateExpertWithFocus
   สร้าง Expert ใหม่ที่เหมาะกับคำถาม user
   เช่น "Military Historian", "Cultural Researcher"
   → Expert เดิมถูกแทนที่!

④ 🤖 LLM call 5+: InsertInformationModule
   สอดข้อมูลที่ได้เข้า Mind Map (Knowledge Base)
   เช่น snippet เรื่องยุทธหัตถี → ใส่ใน node "ยุคสงคราม"

❌ ไม่ Reorganize Mind Map รอบนี้
```

**รวม: ~5-7 LLM calls**

---

## กรณี 2: User กด SKIP ⏭️

```
User ไม่พิมพ์อะไร → กด SKIP
```

### step() ครั้งที่ 1 — AI ถามแทน User

```
เรียก: step(simulate_user=True, simulate_user_intent="...")

สิ่งที่เกิดขึ้น:
  🤖 LLM call 1: AskQuestionWithPersona
     AI สวมบทบาท "researcher with interest in {intent}"
     สร้างคำถามจาก conversation history
     เช่น "สมเด็จพระนเรศวรมีบทบาทอย่างไรในการรวมชาติ?"
  
  ✅ บันทึกเป็น ConversationTurn(role="Guest", type="Original Question")
  → return
```

### step() ครั้งที่ 2 — AI ตอบ

```
เรียก: step()  ← เหมือนกรณี User พิมพ์เลย!

② → ⑤ ทำเหมือนกันทุกประการ
```

**รวม: ~6-8 LLM calls** (เพิ่ม 1 call สำหรับ SimulatedUser)

---

## เปรียบเทียบ 2 กรณี

```
                    User พิมพ์                    User SKIP
                    ─────────                    ─────────
step() ครั้งที่ 1:  บันทึกคำถาม (0 LLM)          AI สร้างคำถาม (1 LLM)
                    ▼                             ▼
step() ครั้งที่ 2:  ┌─────────────────────────────────────────┐
                    │ เหมือนกันทุกประการ:                      │
                    │  ① DiscourseManager เลือก Expert ตอบ    │
                    │  ② ค้นข้อมูล + สังเคราะห์คำตอบ          │
                    │  ③ ขัดเกลาคำตอบ                         │
                    │  ④ สร้าง Expert ใหม่ตาม focus            │
                    │  ⑤ ใส่ข้อมูลเข้า Mind Map               │
                    └─────────────────────────────────────────┘
```

**ข้อแตกต่างจริงๆ มีแค่ step() ครั้งที่ 1:**

| | User พิมพ์ | User SKIP |
|---|---|---|
| ใครถาม? | **User จริง** | **AI จำลอง** (SimulatedUser) |
| LLM calls | 0 | 1 (AskQuestionWithPersona) |
| คำถามมาจาก? | User พิมพ์เอง | AI คิดจาก intent + ประวัติสนทนา |
| role ใน history | "Guest" | "Guest" (เหมือนกัน!) |
| utterance_type | "Original Question" | "Original Question" (เหมือนกัน!) |

> **สรุป: หลังจากได้คำถามแล้ว ระบบทำงานเหมือนกัน 100%**  
> ต่างกันแค่ "คำถามมาจากไหน" — user พิมพ์เอง หรือ AI คิดให้

---

## แล้วหลังจาก AI ตอบแล้วเกิดอะไรต่อ?

หลังจาก step() ครั้งที่ 2 จบ (AI ตอบแล้ว) → **วนรอบถัดไป**:

```
รอบถัดไป → User เลือกอีกครั้ง: พิมพ์ หรือ SKIP?

ถ้า User ไม่ทำอะไร (ไม่พิมพ์ ไม่ SKIP):
→ Expert คนถัดไปจาก list จะตอบต่อ (round-robin)
→ ตอบกันไปเรื่อยๆ จนครบ 3 รอบ

ถ้า Expert ตอบกัน ≥3 ครั้งโดยไม่มีคำถามใหม่:
→ Moderator (พิธีกร) เข้ามา
→ หาข้อมูลที่ค้นมาแล้วแต่ยังไม่มีใครพูดถึง
→ สร้างคำถามใหม่เปลี่ยนมุมมอง
→ Reorganize Mind Map (แตก sub-node ถ้าจำเป็น)
→ วน loop ต่อ
```

---

## Flow รวมทั้ง Phase 2

```
เริ่ม Phase 2 (วนซ้ำ 20 รอบ)
│
├─ รอบที่ 1:
│  ├─ User พิมพ์/SKIP → ได้คำถาม
│  └─ AI ตอบ + สร้าง Expert ใหม่ + ใส่ Mind Map
│
├─ รอบที่ 2:
│  └─ Expert คนที่ 1 ตอบเพิ่ม (round-robin) + ใส่ Mind Map
│
├─ รอบที่ 3:
│  └─ Expert คนที่ 2 ตอบเพิ่ม + ใส่ Mind Map
│
├─ รอบที่ 4:  ← Expert ตอบครบ 3 ครั้ง!
│  └─ 🎯 Moderator เข้ามาถามคำถามใหม่ + Reorganize Mind Map
│
├─ รอบที่ 5:
│  ├─ User พิมพ์/SKIP → ได้คำถามใหม่
│  └─ AI ตอบ + สร้าง Expert ใหม่อีกรอบ
│
├─ ... (วนต่อจนครบ 20 รอบ)
│
└─ จบ Phase 2 → ไป Phase 3 (สร้างบทความจาก Mind Map)
```
