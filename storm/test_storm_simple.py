#!/usr/bin/env python3
"""
ตัวอย่างการใช้ STORM API แบบง่าย
สร้างบทความจากหัวข้อที่กำหนด
"""

import os
import sys
from pathlib import Path

# เพิ่ม path สำหรับ import
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from knowledge_storm import STORMWikiRunnerArguments, STORMWikiRunner, STORMWikiLMConfigs
from knowledge_storm.lm import LitellmModel
from knowledge_storm.rm import TavilySearchRM

def main():
    print("=" * 60)
    print("🌩️  STORM - ตัวอย่างการใช้งานแบบง่าย")
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

    
    # ตั้งค่า Language Models
    print("\n📦 กำลังตั้งค่า Language Models...")
    lm_configs = STORMWikiLMConfigs()
    
    # ตั้งค่า OpenRouter LLM
    llm_kwargs = {
        'api_key': llm_api_key,
        'api_base': llm_base_url,
        'temperature': 1.0,
        'top_p': 0.9,
    }
    
    # Main model สำหรับงานที่ต้องการ reasoning
    main_model = LitellmModel(
        model=llm_model_name,  # OpenRouter รองรับ model name ตรงๆ
        max_tokens=3000,
        **llm_kwargs
    )
    
    # Conversation model (ใช้ tokens น้อยกว่า)
    conv_model = LitellmModel(
        model=llm_model_name,
        max_tokens=500,
        **llm_kwargs
    )
    
    lm_configs.set_conv_simulator_lm(conv_model)   # Conversation
    lm_configs.set_question_asker_lm(conv_model)   # Question asking
    lm_configs.set_outline_gen_lm(main_model)      # Outline generation
    lm_configs.set_article_gen_lm(main_model)      # Article generation
    lm_configs.set_article_polish_lm(main_model)   # Polishing
    
    print("✅ ตั้งค่า Models เรียบร้อย")
    
    # ตั้งค่า Runner Arguments
    print("\n⚙️  กำลังตั้งค่า STORM Runner...")
    output_dir = project_root / "output" / "test_run"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    engine_args = STORMWikiRunnerArguments(
        output_dir=str(output_dir),
        max_conv_turn=1,                    # ลดเหลือ 1 รอบ (ทดสอบก่อน)
        max_perspective=2,                  # ลดเหลือ 2 perspectives
        search_top_k=3,                     # จำนวน search results
        max_search_queries_per_turn=2,     # ลดเหลือ 2 queries ต่อรอบ
    )
    
    # ตั้งค่า Search Engine (Tavily)
    rm = TavilySearchRM(
        tavily_search_api_key=tavily_key,
        k=engine_args.search_top_k,
        include_raw_content=True  # รับ full content สำหรับ context ที่ดีขึ้น
    )
    
    # สร้าง Runner
    runner = STORMWikiRunner(engine_args, lm_configs, rm)
    print("✅ Runner พร้อมใช้งาน")
    
    # รับ input จากผู้ใช้
    print("\n" + "=" * 60)
    print("💡 ตัวอย่างหัวข้อ:")
    print("   - The history of Bitcoin")
    print("   - How do transformers work in deep learning")
    print("   - The impact of climate change on coral reefs")
    print("=" * 60)
    
    topic = input("\n🎯 กรุณาใส่หัวข้อที่ต้องการวิจัย: ").strip()
    
    if not topic:
        print("❌ ไม่ได้ใส่หัวข้อ ใช้หัวข้อ default")
        topic = "The evolution of artificial intelligence"
    
    print(f"\n🚀 เริ่มการวิจัยหัวข้อ: '{topic}'")
    print("⏳ กรุณารอสักครู่... (อาจใช้เวลา 3-5 นาที)")
    print("\n" + "-" * 60)
    
    try:
        # รัน STORM pipeline
        runner.run(
            topic=topic,
            do_research=True,
            do_generate_outline=True,
            do_generate_article=True,
            do_polish_article=True,
        )
        
        # Post-processing
        runner.post_run()
        runner.summary()
        
        print("\n" + "=" * 60)
        print("✅ สำเร็จ! บทความสร้างเสร็จแล้ว")
        print("=" * 60)
        print(f"\n📁 ไฟล์ผลลัพธ์อยู่ที่: {output_dir}")
        print("\n📄 ไฟล์ที่สร้าง:")
        print("   • storm_gen_article_polished.txt  - บทความฉบับสมบูรณ์")
        print("   • storm_gen_article.txt           - บทความต้นฉบับ")
        print("   • storm_gen_outline.txt           - โครงร่าง")
        print("   • conversation_log.json           - บันทึกการวิจัย")
        print("   • url_to_info.json               - แหล่งอ้างอิง")
        
        # แสดงตัวอย่างบทความ
        article_file = output_dir / "storm_gen_article_polished.txt"
        if article_file.exists():
            print("\n" + "=" * 60)
            print("📖 ตัวอย่างบทความ (500 ตัวอักษรแรก):")
            print("=" * 60)
            with open(article_file, 'r', encoding='utf-8') as f:
                content = f.read()
                preview = content[:500]
                print(preview)
                if len(content) > 500:
                    print("\n... (ดูต่อในไฟล์)")
        
        print("\n💡 เปิดไฟล์เต็มได้ที่:")
        print(f"   {article_file}")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        print("=" * 60)
        print("\n💡 วิธีแก้ไข:")
        print("1. ตรวจสอบ API keys ใน secrets.toml")
        print("2. ตรวจสอบว่ามี credits ใน OpenAI account")
        print("3. ตรวจสอบ internet connection")
        print("4. ลองลด max_conv_turn หรือ max_perspective")
        return 1
    
    return 0

if __name__ == "__main__":
    # โหลด environment variables จาก secrets.toml
    try:
        import toml
        secrets_path = Path(__file__).parent / "secrets.toml"
        if secrets_path.exists():
            secrets = toml.load(secrets_path)
            for key, value in secrets.items():
                if not os.getenv(key):
                    os.environ[key] = str(value)
    except Exception as e:
        print(f"⚠️  ไม่สามารถโหลด secrets.toml: {e}")
        print("💡 ใช้ environment variables แทน")
    
    sys.exit(main())
