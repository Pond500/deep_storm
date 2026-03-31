# Co-STORM Optimization Plan — แนวทางลดเวลาให้เร็วขึ้น
## ปัญหา
Co-STORM ใช้เวลานานเกินไป (~15-25 นาที ต่อ 1 หัวข้อ)  
เป้าหมาย: **ลดเวลาลง 50-70%** โดยพยายามรักษาคุณภาพบทความ
## คอขวดหลัก (เรียงตามผลกระทบ)
| อันดับ | คอขวด | เวลา | % ของทั้งหมด | Parallel ได้? |
|---|---|---|---|---|
| 🔴 1 | Phase 2: LLM chain ทุก turn (20 turns × 5-6 calls) | 8-15 นาที | 55% | ❌ Sequential |
| 🟡 2 | InsertInformation ทุก turn (20 turns × 2-5 calls) | 3-8 นาที | 25% | บางส่วน |
| 🟠 3 | Phase 1: Expert QA (3 experts × 2 turns) | 1-3 นาที | 15% | บางส่วน |
| 🟢 4 | Outline + Report + Conv | 0.5-1 นาที | 5% | ✅ Parallel |
---
## แนวทาง Optimize
### ⚡ กลุ่ม A: ลด Parameters (ง่ายสุด — แก้ config ไม่กระทบ logic)
#### A1. ลด total_conv_turn (Phase 2)
```
ก่อน: 20 turns × ~6 calls = ~120 LLM calls
หลัง: 10 turns × ~6 calls = ~60 LLM calls
```
| ไฟล์ | ตัวแปร | เดิม | แนะนำ |
|---|---|---|---|
| `engine.py` RunnerArgument | `total_conv_turn` | 20 | **10** |
- ⏱️ ประหยัด: **~40-50% ของเวลาทั้งหมด**
- 📊 ผลกระทบคุณภาพ: ปานกลาง — ข้อมูลน้อยลง แต่ยังมี warm start เป็นฐาน
- 🔧 ความยาก: ⭐ ง่ายมาก
---
#### A2. ลด Warm Start Parameters
```
ก่อน: 3 experts × 2 turns = 6 expert sessions
หลัง: 2 experts × 1 turn  = 2 expert sessions
```
| ไฟล์ | ตัวแปร | เดิม | แนะนำ |
|---|---|---|---|
| `engine.py` RunnerArgument | `warmstart_max_num_experts` | 3 | **2** |
| `engine.py` RunnerArgument | `warmstart_max_turn_per_experts` | 2 | **1** |
- ⏱️ ประหยัด: **~8-12 LLM calls** (~1-2 นาที)
- 📊 ผลกระทบคุณภาพ: ต่ำ — warm start ยังมี background research + 2 expert views
- 🔧 ความยาก: ⭐ ง่ายมาก
---
#### A3. ลด Search Queries
```
ก่อน: QuestionToQuery สร้าง 3 queries → ค้น 3 ครั้ง
หลัง: สร้าง 2 queries → ค้น 2 ครั้ง
```
| ไฟล์ | ตัวแปร | เดิม | แนะนำ |
|---|---|---|---|
| `engine.py` RunnerArgument | `max_search_queries` | 3 | **2** |
- ⏱️ ประหยัด: **~30% ของเวลา search** ต่อ turn
- 📊 ผลกระทบคุณภาพ: ต่ำ — 2 queries ยังครอบคลุมเพียงพอ
- 🔧 ความยาก: ⭐ ง่ายมาก
---

### ⚡ กลุ่ม B: ลด LLM Calls ต่อ Turn (แก้ code เล็กน้อย)
#### B1. ตัด ConvertUtteranceStyle (Polish) ออก
```
ก่อน: ทุก turn มี 1 call เพื่อ polish คำพูดให้สวย
หลัง: ใช้ raw answer เลย
```
**แก้ที่:**
- `engine.py` → `step()` → ตรง `should_polish_utterance`
- หรือตั้ง `turn_policy.should_polish_utterance = False` เสมอ
- ⏱️ ประหยัด: **20 LLM calls** (1 call × 20 turns)
- 📊 ผลกระทบคุณภาพ: ต่ำ — output จะ "แข็ง" กว่าเดิมเล็กน้อย แต่เนื้อหาเหมือนกัน
- 🔧 ความยาก: ⭐⭐ ง่าย (แก้ 1-2 บรรทัด)
---
#### B2. ข้าม GenerateExpertWithFocus ทุก turn
```
ก่อน: ทุกครั้งที่มีคำถามใหม่ → สร้าง Expert ใหม่ (1 LLM call)
หลัง: สร้าง Expert ใหม่ทุก 3 คำถาม แทน
```
**แก้ที่:**
- `engine.py` → `step()` → เพิ่ม counter สำหรับ expert regeneration
- ⏱️ ประหยัด: **~5-7 LLM calls**
- 📊 ผลกระทบคุณภาพ: ต่ำ — Expert เปลี่ยนช้าลง แต่ยังเปลี่ยนได้
- 🔧 ความยาก: ⭐⭐ ง่าย
---
#### B3. Lazy Insert — batch ทุก 3-5 turns แทนทุก turn
```
ก่อน: ทุก turn → InsertInformation ทันที (2-5 calls)
หลัง: เก็บไว้ก่อน → insert ทุก 5 turns (batch)
```
**แก้ที่:**
- `engine.py` → `step()` → เก็บ conv_turns ใน buffer
- insert เมื่อ buffer เต็ม หรือเมื่อ Moderator เข้ามา
- ⏱️ ประหยัด: **~30-50 LLM calls** (ลด insert frequency)
- 📊 ผลกระทบคุณภาพ: ต่ำ — Mind Map อัปเดตช้าลง แต่ข้อมูลยังครบ
- 🔧 ความยาก: ⭐⭐⭐ ปานกลาง (แก้ logic)

---
### ⚡ กลุ่ม C: ใช้ Model เร็วขึ้น (แก้ config)
#### C1. แยก Model ตาม Task
```
Task ง่าย → model เล็ก (เร็ว + ถูก)
Task สำคัญ → model ใหญ่ (ช้า + แม่น)
```
| LLM Config | Task | เดิม | แนะนำ | เหตุผล |
|---|---|---|---|---|
| `question_answering_lm` | ค้น+ตอบคำถาม | gpt-4o | **คงไว้ gpt-4o** | สำคัญมาก ต้องแม่น |
| `discourse_manage_lm` | Action Planning | gpt-4o | **gpt-4o-mini** | แค่เลือก 1 ใน 4 action |
| `utterance_polishing_lm` | Polish คำพูด | gpt-4o | **ตัดออก (B1)** | ไม่จำเป็น |
| `warmstart_outline_gen_lm` | สร้าง Outline | gpt-4o | **gpt-4o-mini** | ทำแค่ 2 ครั้ง |
| `knowledge_base_lm` | Insert/Expand | gpt-4o | **gpt-4o-mini** | เลือก node ไม่ต้อง creative |
- ⏱️ ประหยัด: gpt-4o-mini เร็วกว่า gpt-4o **~2-3 เท่า**
- 📊 ผลกระทบคุณภาพ: ต่ำ — task ง่ายๆ model เล็กทำได้ดี
- 🔧 ความยาก: ⭐⭐ ง่าย (แก้ config)
---
### ⚡ กลุ่ม D: ตัด Step ที่ไม่จำเป็น (แก้ code)
#### D1. ตัด Report-to-Conversation (Phase 1 ขั้นสุดท้าย)
```
ก่อน: แปลง report → บทสนทนาเปิด (5-8 LLM calls)
หลัง: ส่ง Mind Map summary ให้ user ดูแทน
```
- ⏱️ ประหยัด: **5-8 LLM calls**
- 📊 ผลกระทบคุณภาพ: ไม่กระทบบทความ — แค่ UI ที่ user เห็นตอนเริ่ม
- 🔧 ความยาก: ⭐⭐ ง่าย

#### D2. ตัด to_report() ตอนจบ Warm Start
```
ก่อน: สร้าง report จาก Mind Map ตอนจบ Phase 1
หลัง: ข้ามไป → สร้างตอน Phase 3 ครั้งเดียว
```
- ⏱️ ประหยัด: **5-10 LLM calls** (WriteSection × N nodes)
- 📊 ผลกระทบคุณภาพ: ไม่กระทบ — ถ้า D1 ตัดแล้วก็ไม่ต้องสร้าง report ตรงนี้
- 🔧 ความยาก: ⭐⭐ ง่าย
---
## 🎯 แผนแนะนำ (เรียงตามลำดับ: ง่าย → ยาก)
### ขั้น 1: Quick Wins (แก้ config อย่างเดียว) → **ลด ~50%**
| ทำอะไร | ผลลัพธ์ |
|---|---|
| A1: ลด turns 20→10 | ลด ~60 LLM calls |
| A2: ลด experts 3→2, turns 2→1 | ลด ~8 calls |
| A3: ลด queries 3→2 | ลดเวลา search |
### ขั้น 2: ตัดส่วนไม่จำเป็น → **ลดเพิ่ม ~15%**
| ทำอะไร | ผลลัพธ์ |
|---|---|
| B1: ตัด Polish | ลด ~10 calls (หลังลด turns) |
| D1: ตัด Report-to-Conv | ลด ~5-8 calls |
| D2: ตัด to_report() ใน warm start | ลด ~5-10 calls |
### ขั้น 3: Model เล็กลง → **เร็วขึ้นอีก 2x**
| ทำอะไร | ผลลัพธ์ |
|---|---|
| C1: ใช้ gpt-4o-mini สำหรับ task ง่าย | เร็วขึ้น 2-3x ต่อ call |
### ขั้น 4: Logic Optimization → **ลดเพิ่ม ~10%**
| ทำอะไร | ผลลัพธ์ |
|---|---|
| B2: Expert regen ทุก 3 คำถาม | ลด ~5 calls |
| B3: Lazy insert ทุก 5 turns | ลด ~30-50 calls |
---
## 📊 ผลรวมที่คาดการณ์
```
                          ก่อน optimize    หลัง optimize
LLM calls ทั้งหมด:       ~100-150         ~35-50
เวลา (gpt-4o ทั้งหมด):  ~15-25 นาที      ~3-5 นาที (ถ้าใช้ mini ด้วย)
คุณภาพบทความ:            100%             ~85-90%
```
