#!/usr/bin/env python3
"""
ทดสอบ Custom LLM (ptm-oss-120b) ก่อนใช้กับ STORM
"""

import os
import sys
from pathlib import Path

# โหลด environment variables
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

from knowledge_storm.lm import LitellmModel

def test_llm():
    print("=" * 60)
    print("🧪 ทดสอบ Custom LLM (ptm-oss-120b)")
    print("=" * 60)
    
    # ตรวจสอบ API keys
    llm_api_key = os.getenv("LLM__API_KEY")
    llm_base_url = os.getenv("LLM__BASE_URL")
    llm_model_name = os.getenv("LLM__MODEL_NAME", "ptm-oss-120b")
    
    if not llm_api_key or not llm_base_url:
        print("❌ ไม่พบ LLM configuration ใน secrets.toml")
        return 1
    
    print(f"\n✅ Configuration:")
    print(f"   • Model: {llm_model_name}")
    print(f"   • Endpoint: {llm_base_url}")
    print(f"   • API Key: {llm_api_key[:20]}...")
    
    # สร้าง LLM instance
    print("\n📦 กำลังสร้าง LLM instance...")
    llm_kwargs = {
        'api_key': llm_api_key,
        'api_base': llm_base_url,
        'temperature': 0.7,
        'top_p': 0.9,
    }
    
    try:
        model = LitellmModel(
            model=f'openai/{llm_model_name}',
            max_tokens=100,
            **llm_kwargs
        )
        print("✅ LLM instance สร้างเรียบร้อย")
    except Exception as e:
        print(f"❌ ไม่สามารถสร้าง LLM instance: {e}")
        return 1
    
    # ทดสอบ 1: Simple question
    print("\n" + "=" * 60)
    print("Test 1: Simple Question")
    print("=" * 60)
    
    test_prompt = "What is the capital of Thailand? Answer in one sentence."
    print(f"\n📝 Prompt: {test_prompt}")
    
    try:
        response = model(test_prompt)
        print(f"\n✅ Response type: {type(response)}")
        print(f"✅ Response: {response}")
        
        if response is None:
            print("⚠️  WARNING: Response is None!")
        elif not isinstance(response, str):
            print(f"⚠️  WARNING: Response is not string, it's {type(response)}")
        elif response.strip() == "":
            print("⚠️  WARNING: Response is empty string!")
        else:
            print(f"✅ Response length: {len(response)} characters")
            
    except Exception as e:
        print(f"❌ Error calling LLM: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # ทดสอบ 2: JSON format (STORM ใช้บ่อย)
    print("\n" + "=" * 60)
    print("Test 2: Structured Output")
    print("=" * 60)
    
    test_prompt2 = """List 3 perspectives about AI safety. 
Format as JSON array like: ["perspective 1", "perspective 2", "perspective 3"]"""
    
    print(f"\n📝 Prompt: {test_prompt2}")
    
    try:
        response2 = model(test_prompt2)
        print(f"\n✅ Response: {response2}")
        
        if response2 is None or (isinstance(response2, str) and not response2.strip()):
            print("⚠️  WARNING: Model returning empty/None responses!")
            print("💡 Suggestion: Model อาจต้องการ system message หรือ format พิเศษ")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # ทดสอบ 3: Longer generation
    print("\n" + "=" * 60)
    print("Test 3: Longer Generation (300 tokens)")
    print("=" * 60)
    
    try:
        model_long = LitellmModel(
            model=f'openai/{llm_model_name}',
            max_tokens=300,
            **llm_kwargs
        )
        
        test_prompt3 = "Explain what NECTEC is in 2-3 sentences."
        print(f"\n📝 Prompt: {test_prompt3}")
        
        response3 = model_long(test_prompt3)
        print(f"\n✅ Response: {response3}")
        print(f"✅ Length: {len(response3) if response3 else 0} characters")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ การทดสอบเสร็จสิ้น")
    print("=" * 60)
    
    # สรุป
    print("\n📋 สรุปผลการทดสอบ:")
    print("   • ถ้าทุก test ผ่าน → LLM พร้อมใช้กับ STORM")
    print("   • ถ้ามี WARNING → อาจต้องปรับ configuration")
    print("   • ถ้ามี Error → ตรวจสอบ API key หรือ endpoint")
    
    return 0

if __name__ == "__main__":
    sys.exit(test_llm())
