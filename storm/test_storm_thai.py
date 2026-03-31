"""
STORM Thai - สร้างบทความภาษาไทยแบบ Wikipedia
ใช้ OpenRouter + Tavily Search
"""

import os
import sys
import toml
from pathlib import Path
from datetime import datetime

# Import STORM
from knowledge_storm import STORMWikiRunnerArguments, STORMWikiRunner, STORMWikiLMConfigs
from knowledge_storm.lm import LitellmModel
from knowledge_storm.rm import TavilySearchRM


def main():
    # โหลด secrets - ใช้ absolute path
    script_dir = Path(__file__).parent
    secrets_path = script_dir / "secrets.toml"
    
    if not secrets_path.exists():
        print(f"❌ ไม่พบไฟล์ {secrets_path}")
        print("📝 กรุณาสร้างไฟล์ secrets.toml และใส่ API keys")
        return 1
    
    secrets = toml.load(secrets_path)
    for key, value in secrets.items():
        if key not in os.environ:
            os.environ[key] = str(value)
    
    print("=" * 60)
    print("🇹🇭 STORM Thai - ระบบสร้างบทความภาษาไทย")
    print("=" * 60)
    
    # ตรวจสอบ API keys
    llm_api_key = os.getenv("LLM__API_KEY")
    llm_base_url = os.getenv("LLM__BASE_URL")
    llm_model_name = os.getenv("LLM__MODEL_NAME", "openai/gpt-4o-mini")
    tavily_key = os.getenv("TAVILY_API_KEY")
    
    if not llm_api_key:
        print("\n❌ ไม่พบ LLM__API_KEY")
        print("📝 กรุณาเพิ่มใน secrets.toml")
        return
    
    if not tavily_key:
        print("\n❌ ไม่พบ TAVILY_API_KEY")
        print("📝 กรุณาเพิ่มใน secrets.toml หรือสมัครที่ https://tavily.com")
        return
    
    print("\n✅ พบ API keys แล้ว")
    print(f"   • LLM Model: {llm_model_name}")
    print(f"   • LLM Provider: OpenRouter")
    print(f"   • Search: Tavily (AI Research)")
    print(f"   • Language: 🇹🇭 ภาษาไทย")
    
    # ตั้งค่า Language Models
    print("\n📦 กำลังตั้งค่า Language Models สำหรับภาษาไทย...")
    lm_configs = STORMWikiLMConfigs()
    
    # ตั้งค่า LLM พร้อม system prompt ภาษาไทย
    llm_kwargs = {
        'api_key': llm_api_key,
        'api_base': llm_base_url,
        'temperature': 1.0,
        'top_p': 0.9,
    }
    
    # Main model - เพิ่ม instruction ให้ตอบเป็นภาษาไทย
    main_model = LitellmModel(
        model=llm_model_name,
        max_tokens=4000,  # เพิ่มขึ้นเพราะภาษาไทยใช้ tokens มากกว่า
        **llm_kwargs
    )
    
    # Conversation model
    conv_model = LitellmModel(
        model=llm_model_name,
        max_tokens=1000,
        **llm_kwargs
    )
    
    lm_configs.set_conv_simulator_lm(conv_model)
    lm_configs.set_question_asker_lm(conv_model)
    lm_configs.set_outline_gen_lm(main_model)
    lm_configs.set_article_gen_lm(main_model)
    lm_configs.set_article_polish_lm(main_model)
    
    print("✅ ตั้งค่า Models เรียบร้อย")
    
    # ตั้งค่า STORM Runner
    print("\n⚙️  กำลังตั้งค่า STORM Runner สำหรับภาษาไทย...")
    
    output_dir = Path("output/thai_articles")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    engine_args = STORMWikiRunnerArguments(
        output_dir=str(output_dir),
        max_conv_turn=2,                    # จำนวนรอบ conversation (ลดลงเพื่อหลีก rate limit)
        max_perspective=3,                   # จำนวน perspectives (3 เพียงพอ)
        search_top_k=3,                      # ลดเหลือ 3 เพื่อประหยัด API calls
        max_search_queries_per_turn=2,      # ลดเหลือ 2 queries ต่อรอบ
        max_thread_num=1,                    # ✨ ใช้ 1 thread (ส่ง sequential, ไม่พร้อมกัน)
    )
    
    # ตั้งค่า Search Engine (Tavily)
    rm = TavilySearchRM(
        tavily_search_api_key=tavily_key,
        k=engine_args.search_top_k,
        include_raw_content=True
    )
    
    # สร้าง Runner
    runner = STORMWikiRunner(engine_args, lm_configs, rm)
    print("✅ Runner พร้อมใช้งาน")
    
    # รับ input จากผู้ใช้
    print("\n" + "=" * 60)
    print("💡 ตัวอย่างหัวข้อ (ภาษาไทย):")
    print("   - ประวัติศาสตร์ Bitcoin")
    print("   - ประวัติศาสตร์ศูนย์เทคโนโลยีอิเล็กทรอนิกส์และคอมพิวเตอร์แห่งชาติ")
    print("   - การทำงานของ Transformer ใน Deep Learning")
    print("   - ผลกระทบของการเปลี่ยนแปลงสภาพภูมิอากาศต่อแนวปะการัง")
    print("=" * 60)
    
    topic = input("\n🎯 กรุณาใส่หัวข้อที่ต้องการวิจัย (ภาษาไทย): ").strip()
    
    if not topic:
        print("❌ กรุณาใส่หัวข้อ")
        return
    
    print(f"\n🚀 เริ่มการวิจัยหัวข้อ: '{topic}'")
    print("⏳ กรุณารอสักครู่... (อาจใช้เวลา 3-5 นาที)")
    print("\n" + "-" * 60)
    
    try:
        # รัน STORM pipeline พร้อม prompt ภาษาไทย
        runner.run(
            topic=topic,
            do_research=True,
            do_generate_outline=True,
            do_generate_article=True,
            do_polish_article=True,
            remove_duplicate=True,
        )
        
        # แสดงผลลัพธ์
        article_dir = output_dir / topic
        
        print("\n" + "=" * 60)
        print("✅ สำเร็จ! บทความภาษาไทยสร้างเสร็จแล้ว")
        print("=" * 60)
        
        print(f"\n📁 ไฟล์ผลลัพธ์อยู่ที่: {article_dir}")
        
        print(f"\n📄 ไฟล์ที่สร้าง:")
        print(f"   • storm_gen_article_polished.txt  - บทความฉบับสมบูรณ์ (ภาษาไทย)")
        print(f"   • storm_gen_article.txt           - บทความต้นฉบับ")
        print(f"   • storm_gen_outline.txt           - โครงร่าง")
        print(f"   • conversation_log.json           - บันทึกการวิจัย")
        print(f"   • url_to_info.json               - แหล่งอ้างอิง")
        
        print(f"\n💡 เปิดไฟล์เต็มได้ที่:")
        print(f"   {article_dir}/storm_gen_article_polished.txt")
        
        # แสดง preview
        polished_file = article_dir / "storm_gen_article_polished.txt"
        if polished_file.exists():
            print(f"\n📖 ตัวอย่างบทความ (50 บรรทัดแรก):")
            print("-" * 60)
            with open(polished_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:50]
                print(''.join(lines))
            if len(lines) == 50:
                print("\n... (ดูเพิ่มเติมในไฟล์)")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        print("=" * 60)
        
        print(f"\n💡 วิธีแก้ไข:")
        print("1. ตรวจสอบ API keys ใน secrets.toml")
        print("2. ตรวจสอบว่ามี credits ใน OpenRouter account")
        print("3. ตรวจสอบ internet connection")
        print("4. ลองใช้ model อื่น (google/gemini-pro-1.5 หรือ anthropic/claude-3.5-sonnet)")
        
        import traceback
        print(f"\n🔍 Error details:")
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
