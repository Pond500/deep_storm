"""
Co-STORM Thai - ระบบสร้างบทความภาษาไทยแบบมีส่วนร่วม
ใช้ OpenRouter + Tavily Search

Co-STORM = Collaborative STORM
- ระบบจะถามคำถามให้คุณ
- คุณสามารถตอบและถามเพิ่มได้
- ระบบจะค้นหาข้อมูลและสรุปให้
- สร้างบทความจากการสนทนาร่วมกัน
"""

import os
import sys
import toml
import json
from pathlib import Path
from datetime import datetime

# Import Co-STORM
from knowledge_storm.collaborative_storm.engine import (
    CollaborativeStormLMConfigs,
    RunnerArgument,
    CoStormRunner,
)
from knowledge_storm.collaborative_storm.modules.callback import (
    LocalConsolePrintCallBackHandler,
)
from knowledge_storm.lm import LitellmModel
from knowledge_storm.rm import TavilySearchRM
from knowledge_storm.logging_wrapper import LoggingWrapper
from thai_llm_wrapper import ThaiLitellmModel  # Thai language wrapper


def main():
    # โหลด secrets
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
    
    # ตั้งค่า encoder สำหรับ Co-STORM (ใช้ OpenRouter)
    os.environ["ENCODER_API_TYPE"] = "openai"
    os.environ["OPENAI_API_KEY"] = os.getenv("LLM__API_KEY")  # ใช้ OpenRouter key
    os.environ["OPENAI_API_BASE"] = os.getenv("LLM__BASE_URL", "https://openrouter.ai/api/v1")
    
    print("=" * 70)
    print("🤝 Co-STORM Thai - ระบบสร้างบทความแบบร่วมมือ (ภาษาไทย)")
    print("=" * 70)
    
    # ตรวจสอบ API keys
    llm_api_key = os.getenv("LLM__API_KEY")
    llm_base_url = os.getenv("LLM__BASE_URL")
    llm_model_name = os.getenv("LLM__MODEL_NAME", "openai/gpt-4o-mini")
    tavily_key = os.getenv("TAVILY_API_KEY")
    
    if not llm_api_key or not tavily_key:
        print("\n❌ ต้องมี LLM__API_KEY และ TAVILY_API_KEY")
        return 1
    
    print(f"\n✅ API Keys พร้อม")
    print(f"   • Model: {llm_model_name}")
    print(f"   • Provider: OpenRouter")
    print(f"   • Search: Tavily")
    
    # ตั้งค่า Language Models
    print("\n📦 กำลังตั้งค่า Co-STORM Models...")
    lm_config = CollaborativeStormLMConfigs()
    
    llm_kwargs = {
        'api_key': llm_api_key,
        'api_base': llm_base_url,
        'temperature': 1.0,
        'top_p': 0.9,
    }
    
    # ตั้งค่า models สำหรับ Co-STORM components (ใช้ Thai wrapper)
    question_answering_lm = ThaiLitellmModel(
        model=llm_model_name,
        max_tokens=2000,
        **llm_kwargs
    )
    
    discourse_manage_lm = ThaiLitellmModel(
        model=llm_model_name,
        max_tokens=500,
        **llm_kwargs
    )
    
    utterance_polishing_lm = ThaiLitellmModel(
        model=llm_model_name,
        max_tokens=2000,
        **llm_kwargs
    )
    
    warmstart_outline_gen_lm = ThaiLitellmModel(
        model=llm_model_name,
        max_tokens=1000,
        **llm_kwargs
    )
    
    question_asking_lm = ThaiLitellmModel(
        model=llm_model_name,
        max_tokens=500,
        **llm_kwargs
    )
    
    knowledge_base_lm = ThaiLitellmModel(
        model=llm_model_name,
        max_tokens=2000,
        **llm_kwargs
    )
    
    lm_config.set_question_answering_lm(question_answering_lm)
    lm_config.set_discourse_manage_lm(discourse_manage_lm)
    lm_config.set_utterance_polishing_lm(utterance_polishing_lm)
    lm_config.set_warmstart_outline_gen_lm(warmstart_outline_gen_lm)
    lm_config.set_question_asking_lm(question_asking_lm)
    lm_config.set_knowledge_base_lm(knowledge_base_lm)
    
    print("✅ Models พร้อมแล้ว")
    
    # รับ topic จากผู้ใช้
    print("\n" + "=" * 70)
    print("💡 ตัวอย่างหัวข้อ:")
    print("   - Bitcoin และผลกระทบต่อระบบเศรษฐกิจ")
    print("   - ประวัติและวิวัฒนาการของ AI")
    print("   - การเปลี่ยนแปลงสภาพภูมิอากาศในประเทศไทย")
    print("=" * 70)
    
    topic = input("\n📝 พิมพ์หัวข้อที่ต้องการ: ").strip()
    
    if not topic:
        print("❌ กรุณาระบุหัวข้อ")
        return 1
    
    print(f"\n🎯 หัวข้อ: {topic}")
    
    # ตั้งค่า Runner Arguments (ปรับให้เหมาะกับ Tavily free tier)
    runner_argument = RunnerArgument(
        topic=topic,
        retrieve_top_k=3,                    # จำนวน search results
        max_search_queries=2,                # จำนวน queries per turn
        total_conv_turn=10,                  # จำนวนรอบสนทนาทั้งหมด
        max_search_thread=1,                 # single thread เพื่อหลีก rate limit
        max_search_queries_per_turn=2,
        warmstart_max_num_experts=2,         # จำนวน experts ตอน warm start
        warmstart_max_turn_per_experts=1,    # รอบต่อ expert
        warmstart_max_thread=1,
        max_thread_num=1,
        max_num_round_table_experts=3,       # จำนวน experts ใน discussion
        moderator_override_N_consecutive_answering_turn=3,
        node_expansion_trigger_count=10,
    )
    
    # ตั้งค่า Tavily Search
    rm = TavilySearchRM(
        tavily_search_api_key=tavily_key,
        k=runner_argument.retrieve_top_k,
        include_raw_content=True,
    )
    
    logging_wrapper = LoggingWrapper(lm_config)
    callback_handler = LocalConsolePrintCallBackHandler()
    
    print("\n⚙️  กำลังสร้าง Co-STORM Runner...")
    costorm_runner = CoStormRunner(
        lm_config=lm_config,
        runner_argument=runner_argument,
        logging_wrapper=logging_wrapper,
        rm=rm,
        callback_handler=callback_handler,
    )
    
    print("✅ Runner พร้อมใช้งาน\n")
    print("=" * 70)
    print("🚀 เริ่มต้นการสนทนา - Co-STORM กำลังเตรียมข้อมูล...")
    print("=" * 70)
    
    # Warm start - ระบบเตรียมข้อมูลเบื้องต้น
    try:
        costorm_runner.warm_start()
        print("\n✅ Warm start เสร็จสิ้น - พร้อมสนทนา!\n")
    except Exception as e:
        print(f"\n❌ Error during warm start: {e}")
        return 1
    
    # Interactive conversation loop
    print("=" * 70)
    print("💬 โหมดสนทนาเริ่มต้น")
    print("=" * 70)
    print("📌 คำแนะนำ:")
    print("   • พิมพ์ 'skip' เพื่อให้ AI คุยต่อเอง")
    print("   • พิมพ์ 'done' เพื่อสร้างบทความ")
    print("   • หรือตอบคำถาม/ถามคำถามเพิ่มเติมได้เลย")
    print("=" * 70)
    print()
    
    user_turns_count = 0
    max_auto_turns = 5  # จำนวนรอบที่ให้ AI คุยเอง
    
    try:
        while True:
            # ให้ Co-STORM generate turn ถัดไป
            conv_turn = costorm_runner.step()
            
            if conv_turn is None:
                print("\n✅ การสนทนาเสร็จสิ้น")
                break
            
            print(f"\n🤖 **{conv_turn.role}**: {conv_turn.utterance}\n")
            print("-" * 70)
            
            # ถามว่าผู้ใช้อยากตอบหรือไม่
            user_input = input("\n💬 คุณ: ").strip()
            
            if user_input.lower() == 'done':
                print("\n✅ สิ้นสุดการสนทนา - กำลังสร้างบทความ...")
                break
            elif user_input.lower() == 'skip' or user_input == '':
                # ให้ AI คุยต่อเอง
                print("   ⏩ ข้าม - ให้ AI คุยต่อ...")
                if user_turns_count < max_auto_turns:
                    user_turns_count += 1
                    continue
                else:
                    print("\n   ⚠️  ถึงจำนวนรอบสูงสุดแล้ว - กำลังสร้างบทความ...")
                    break
            else:
                # ผู้ใช้ตอบ/ถาม
                costorm_runner.step(user_utterance=user_input)
                user_turns_count = 0  # reset counter
                print("   ✅ บันทึกคำตอบแล้ว")
            
            print()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  ยกเลิกการสนทนา - กำลังสร้างบทความจากข้อมูลที่มี...")
    except Exception as e:
        print(f"\n❌ Error during conversation: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # สร้างบทความจากการสนทนา
    print("\n" + "=" * 70)
    print("📝 กำลังสร้างบทความจากการสนทนา...")
    print("=" * 70)
    
    try:
        # Reorganize knowledge base
        costorm_runner.knowledge_base.reorganize()
        
        # Generate article
        article = costorm_runner.generate_report()
        
        # บันทึกผลลัพธ์
        output_dir = Path("output/costorm_thai_articles") / topic.replace(" ", "_")[:50]
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save article
        article_path = output_dir / "costorm_article.md"
        with open(article_path, "w", encoding="utf-8") as f:
            f.write(article)
        
        # Save conversation log
        log_dump = costorm_runner.dump_logging_and_reset()
        log_path = output_dir / "conversation_log.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_dump, f, indent=2, ensure_ascii=False)
        
        # Save instance dump
        instance_copy = costorm_runner.to_dict()
        instance_path = output_dir / "instance_dump.json"
        with open(instance_path, "w", encoding="utf-8") as f:
            json.dump(instance_copy, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 70)
        print("✅ สำเร็จ! บทความ Co-STORM สร้างเสร็จแล้ว")
        print("=" * 70)
        print(f"\n📁 ไฟล์ผลลัพธ์อยู่ที่: {output_dir}")
        print(f"\n📄 ไฟล์ที่สร้าง:")
        print(f"   • costorm_article.md      - บทความฉบับสมบูรณ์")
        print(f"   • conversation_log.json   - บันทึกการสนทนา")
        print(f"   • instance_dump.json      - ข้อมูล session")
        
        # แสดงตัวอย่างบทความ
        print("\n" + "=" * 70)
        print("📖 ตัวอย่างบทความ (100 บรรทัดแรก):")
        print("=" * 70)
        lines = article.split('\n')[:100]
        print('\n'.join(lines))
        if len(article.split('\n')) > 100:
            print("\n... (ดูเพิ่มเติมในไฟล์)")
        
        print("\n" + "=" * 70)
        print(f"💡 เปิดไฟล์เต็มได้ที่: {article_path}")
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error generating article: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
