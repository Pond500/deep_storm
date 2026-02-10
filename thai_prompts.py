"""
Thai Prompt Templates สำหรับ STORM
ใช้แทน default English prompts
"""

# ===============================================
# Prompt Templates ภาษาไทย
# ===============================================

THAI_CONV_SIMULATOR_PROMPT = """คุณเป็นผู้เชี่ยวชาญที่กำลังคุยกับนักวิจัยเกี่ยวกับหัวข้อ: {topic}

บริบท: {context}

กรุณาตอบคำถามต่อไปนี้เป็นภาษาไทยอย่างละเอียด โดยอิงจากข้อมูลที่มี:

คำถาม: {question}

คำตอบ (ภาษาไทย):"""

THAI_QUESTION_ASKER_PROMPT = """คุณเป็นนักวิจัยที่กำลังสัมภาษณ์ผู้เชี่ยวชาญเกี่ยวกับหัวข้อ: {topic}

บทบาทของคุณ: {perspective}

บทสนทนาที่ผ่านมา:
{conversation_history}

กรุณาสร้างคำถามต่อไป (เป็นภาษาไทย) ที่:
1. ต่อเนื่องจากบทสนทนา
2. เจาะลึกประเด็นที่น่าสนใจ
3. ช่วยให้เข้าใจหัวข้อมากขึ้น

คำถามถัดไป (ภาษาไทย):"""

THAI_OUTLINE_GEN_PROMPT = """กรุณาสร้างโครงร่างบทความสไตล์ Wikipedia เป็นภาษาไทยสำหรับหัวข้อ: {topic}

ข้อมูลที่รวบรวมได้:
{research_data}

โครงร่างควรมี:
1. บทนำ (Introduction)
2. หัวข้อหลัก 3-5 หัวข้อ
3. หัวข้อย่อยในแต่ละหัวข้อหลัก
4. สรุป (Conclusion)

รูปแบบ Markdown:
# หัวข้อหลัก
## หัวข้อย่อย
### หัวข้อย่อยระดับ 3

โครงร่างบทความ (ภาษาไทย):"""

THAI_ARTICLE_GEN_PROMPT = """กรุณาเขียนบทความสไตล์ Wikipedia เป็นภาษาไทยสำหรับหัวข้อ: {topic}

โครงร่าง:
{outline}

ข้อมูลอ้างอิง:
{references}

คำแนะนำ:
1. เขียนเป็นภาษาไทยที่เป็นทางการ
2. ใช้ประโยคที่กระชับ ชัดเจน
3. อ้างอิงแหล่งที่มา [1], [2], [3]...
4. หลีกเลี่ยงความคิดเห็นส่วนตัว
5. เขียนในรูปแบบสารานุกรม (encyclopedic)

บทความ (ภาษาไทย):"""

THAI_ARTICLE_POLISH_PROMPT = """กรุณาปรับปรุงบทความนี้ให้ดีขึ้น:

บทความต้นฉบับ:
{draft_article}

ปรับปรุงโดย:
1. แก้ไขไวยากรณ์และการสะกด
2. ปรับประโยคให้อ่านง่าย
3. เพิ่มความเชื่อมโยงระหว่างหัวข้อ
4. ตรวจสอบการอ้างอิง
5. ให้ภาษาเป็นทางการมากขึ้น

บทความที่ปรับปรุงแล้ว (ภาษาไทย):"""

THAI_SEARCH_QUERY_GEN_PROMPT = """กรุณาสร้าง search queries เป็นภาษาอังกฤษสำหรับหัวข้อ: {topic}

บริบท: {context}

สร้าง {num_queries} queries ที่:
1. เขียนเป็นภาษาอังกฤษ (เพื่อค้นหาข้อมูลจาก internet)
2. เฉพาะเจาะจง ไม่กว้างเกินไป
3. ครอบคลุมมุมมองต่างๆ

รูปแบบ:
- query 1
- query 2
- query 3

Search queries:"""


# ===============================================
# Helper Functions สำหรับใช้ Thai Prompts
# ===============================================

def get_thai_prompts():
    """
    คืนค่า dictionary ของ prompts ภาษาไทย
    """
    return {
        'conv_simulator': THAI_CONV_SIMULATOR_PROMPT,
        'question_asker': THAI_QUESTION_ASKER_PROMPT,
        'outline_gen': THAI_OUTLINE_GEN_PROMPT,
        'article_gen': THAI_ARTICLE_GEN_PROMPT,
        'article_polish': THAI_ARTICLE_POLISH_PROMPT,
        'search_query_gen': THAI_SEARCH_QUERY_GEN_PROMPT,
    }


def format_thai_prompt(template, **kwargs):
    """
    Format prompt template ด้วยค่าที่ให้มา
    
    Args:
        template: Template string
        **kwargs: ค่าที่จะแทนใน template
    
    Returns:
        Formatted prompt string
    """
    return template.format(**kwargs)


# ===============================================
# ตัวอย่างการใช้งาน
# ===============================================

if __name__ == "__main__":
    prompts = get_thai_prompts()
    
    # ตัวอย่างการใช้
    conv_prompt = format_thai_prompt(
        prompts['conv_simulator'],
        topic="Bitcoin",
        context="Bitcoin เป็น cryptocurrency ที่ถูกสร้างขึ้นในปี 2009",
        question="Bitcoin ทำงานอย่างไร?"
    )
    
    print("ตัวอย่าง Prompt:")
    print("=" * 60)
    print(conv_prompt)
    print("=" * 60)
