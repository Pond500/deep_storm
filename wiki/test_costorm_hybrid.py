"""
Co-STORM Thai with Hybrid Retrieval (Vector + BM25 + Reranking)
เวอร์ชันที่ดีที่สุด!

⚠️  หมายเหตุ: Co-STORM ต้องใช้ OpenRouter API สำหรับ:
   1. LLM (gpt-4o-mini) - สำหรับสร้างเนื้อหา
   2. Encoder (text-embedding-3-small) - สำหรับจัด outline
   
   💰 ใช้ OpenRouter credit เท่านั้น ไม่ต้องใช้ OpenAI โดยตรง
"""

import os
import sys
from pathlib import Path

# Set required environment variables for OpenRouter
if "ENCODER_API_TYPE" not in os.environ:
    os.environ["ENCODER_API_TYPE"] = "openai"

# Check OPENROUTER_API_KEY
if "OPENROUTER_API_KEY" not in os.environ:
    print("\n" + "="*80)
    print("❌ Error: OPENROUTER_API_KEY environment variable not set")
    print("="*80)
    print("\n⚠️  Co-STORM requires OpenRouter API key")
    print("\n💡 How to fix:")
    print("   export OPENROUTER_API_KEY='your-api-key-here'")
    print("\n💰 Cost: Uses your OpenRouter credit")
    print("   - LLM: gpt-4o-mini")
    print("   - Embedding: text-embedding-3-small")
    print("\n📝 Get API key: https://openrouter.ai/keys")
    print("="*80)
    sys.exit(1)

# Set OPENAI_API_KEY to use OpenRouter (LiteLLM compatibility)
# LiteLLM looks for OPENAI_API_KEY when provider is 'openai'
os.environ["OPENAI_API_KEY"] = os.environ["OPENROUTER_API_KEY"]

# Set OpenRouter as base URL for OpenAI-compatible calls
if "OPENAI_API_BASE" not in os.environ:
    os.environ["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_storm.collaborative_storm.engine import (
    CollaborativeStormLMConfigs,
    RunnerArgument,
    CoStormRunner,
)
from knowledge_storm.lm import LitellmModel
from hybrid_wikipedia_rm import HybridWikipediaRM
from knowledge_storm.logging_wrapper import LoggingWrapper
from thai_llm_wrapper import ThaiLitellmModel


def setup_costorm_with_hybrid(topic: str):
    """Setup Co-STORM with Hybrid Retrieval"""
    
    print("="*80)
    print("🤝 Co-STORM Thai - Hybrid Retrieval (Best Quality)")
    print("="*80)
    print(f"📝 Topic: {topic}")
    print()
    print("🎯 Retrieval Strategy:")
    print("  1. Dense Search (Vector - Semantic)")
    print("  2. Sparse Search (BM25 - Keyword)")
    print("  3. RRF Fusion (Merge results)")
    print("  4. Cross-Encoder Reranking (Precision)")
    print()
    print("💡 Expected Quality:")
    print("  - Simple Vector: 72% → Hybrid + Rerank: 89% (+24%)")
    print("  - Better for keyword queries (names, specific terms)")
    print("  - Slower but higher quality")
    print()
    print("🤖 LLM: openai/gpt-4o-mini")
    print("🔍 Search: Hybrid (Wikipedia Thai - 52,572 documents)")
    print()
    
    # Setup LLM configs
    print("🔧 Setting up Thai LLM models...")
    
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", 
        "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")
    
    # Ensure environment variables are set for LiteLLM
    os.environ['OPENROUTER_API_KEY'] = openrouter_api_key
    os.environ['OPENAI_API_KEY'] = openrouter_api_key  # LiteLLM uses this
    
    # Create LM config (must init empty first)
    lm_config = CollaborativeStormLMConfigs()
    
    # Common kwargs for all models
    common_kwargs = {
        "api_base": "https://openrouter.ai/api/v1",
        "api_key": openrouter_api_key,
        "custom_llm_provider": "openai",  # Tell LiteLLM to use OpenAI format
    }
    
    # Set each LM with ThaiLitellmModel wrapper
    lm_config.question_answering_lm = ThaiLitellmModel(
        model="openai/gpt-4o-mini",
        max_tokens=1000,
        temperature=1.0,
        top_p=0.9,
        **common_kwargs,
    )
    
    lm_config.discourse_manage_lm = ThaiLitellmModel(
        model="openai/gpt-4o-mini",
        max_tokens=500,
        temperature=1.0,
        top_p=0.9,
        **common_kwargs,
    )
    
    lm_config.utterance_polishing_lm = ThaiLitellmModel(
        model="openai/gpt-4o-mini",
        max_tokens=2000,
        temperature=1.0,
        top_p=0.9,
        **common_kwargs,
    )
    
    lm_config.warmstart_outline_gen_lm = ThaiLitellmModel(
        model="openai/gpt-4o-mini",
        max_tokens=500,
        temperature=1.0,
        top_p=0.9,
        **common_kwargs,
    )
    
    lm_config.question_asking_lm = ThaiLitellmModel(
        model="openai/gpt-4o-mini",
        max_tokens=300,
        temperature=1.0,
        top_p=0.9,
        **common_kwargs,
    )
    
    lm_config.knowledge_base_lm = ThaiLitellmModel(
        model="openai/gpt-4o-mini",
        max_tokens=1000,
        temperature=1.0,
        top_p=0.9,
        **common_kwargs,
    )
    
    print("✅ LLM models configured")
    
    # Setup runner arguments
    runner_argument = RunnerArgument(
        topic=topic,
        retrieve_top_k=5,
        max_search_queries=3,
        total_conv_turn=20,  
        warmstart_max_num_experts=2,
        warmstart_max_turn_per_experts=2,
        max_num_round_table_experts=2,
    )
    
    print("✅ Runner arguments configured")
    print()
    
    # Setup Hybrid Retrieval Module
    print("🔧 Setting up Hybrid Retrieval...")
    print("  💡 This combines vector + keyword + reranking")
    print("  ⏱️  First query may be slower (loading models)")
    print()
    
    rm = HybridWikipediaRM(
        vector_store_path="./vector_store",
        collection_name="wikipedia_thai",
        embedding_model="BAAI/bge-m3",
        reranker_model="BAAI/bge-reranker-v2-m3",
        device="mps",
        k=runner_argument.retrieve_top_k,
        use_reranking=True,  # Enable reranking for best quality
        rerank_top_k=20,  # Rerank top-20 candidates
        alpha=0.5,  # 50% vector, 50% BM25
    )
    
    print(f"✅ Hybrid Retrieval initialized")
    print()
    
    # Setup logging
    output_dir = f"../output/costorm_hybrid_thai/{topic}"
    logging_wrapper = LoggingWrapper(lm_config)
    
    # Create Co-STORM runner
    print("🔧 Creating Co-STORM runner...")
    runner = CoStormRunner(
        lm_config=lm_config,
        runner_argument=runner_argument,
        logging_wrapper=logging_wrapper,
        rm=rm,
    )
    
    print("✅ Co-STORM runner ready!")
    print("="*80)
    print()
    
    return runner


def main():
    """Main function"""
    # Get topic from user
    print("="*80)
    print("🤝 Co-STORM Thai - Interactive Article Creation (Hybrid Retrieval)")
    print("="*80)
    print()
    print(" Best quality retrieval:")
    print("  ✅ Vector search (semantic understanding)")
    print("  ✅ BM25 search (keyword matching)")  
    print("  ✅ RRF fusion (best of both)")
    print("  ✅ Cross-encoder reranking (precision)")
    print()
    
    topic = input("📝 พิมพ์หัวข้อที่ต้องการสร้างบทความ: ").strip()
    
    if not topic:
        print("❌ Error: กรุณาระบุหัวข้อ")
        return
    
    # Setup runner
    runner = setup_costorm_with_hybrid(topic)
    
    # Warm start
    print("="*80)
    print("🔄 Starting warm start...")
    print("="*80)
    print("💡 กำลังสร้าง outline และ expert personas...")
    print()
    
    try:
        runner.warm_start()
        print()
        print("✅ Warm start completed!")
        print()
    except Exception as e:
        print(f"❌ Error during warm start: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Interactive conversation
    print("="*80)
    print("💬 เริ่มการสนทนา")
    print("="*80)
    print()
    print("📌 คำสั่ง:")
    print("   - พิมพ์คำตอบ / ถามคำถามใหม่")
    print("   - 'skip' = ให้ AI คุยต่อเอง")
    print("   - 'done' = สร้างบทความ")
    print()
    print()
    
    try:
        for turn_num in range(runner.runner_argument.total_conv_turn):
            print("="*80)
            print(f"🔄 Turn {turn_num + 1}/{runner.runner_argument.total_conv_turn}")
            print("="*80)
            print()
            
            # Get moderator question
            try:
                moderator_question = runner.step()
            except IndexError as e:
                print(f"⚠️  Warning: Conversation history is empty. Warm start may have failed.")
                print(f"   Error: {e}")
                print(f"   Skipping to article generation...")
                break
            
            if moderator_question:
                print(f"🤖 **Moderator:**")
                # Extract text from ConversationTurn object
                question_text = moderator_question.utterance if hasattr(moderator_question, 'utterance') else str(moderator_question)
                print(question_text)
                print()
                
                # Get user input
                try:
                    user_input = input("💬 คุณ: ").strip()
                except EOFError:
                    user_input = "skip"
                
                if user_input.lower() == 'done':
                    print()
                    print("✅ สิ้นสุดการสนทนา")
                    break
                elif user_input.lower() == 'skip' or not user_input:
                    print("⏭️  Skip - ให้ AI คุยต่อเอง")
                    runner.step(user_utterance="", simulate_user=True)
                else:
                    runner.step(user_utterance=user_input)
                
                print()
            else:
                print("✅ การสนทนาเสร็จสิ้น")
                break
        
    except KeyboardInterrupt:
        print()
        print("⚠️  Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Generate article
    print()
    print("="*80)
    print("📝 กำลังสร้างบทความ...")
    print("="*80)
    print()
    
    try:
        # Generate report (returns the article text)
        article = runner.generate_report()
        
        # Save to file
        output_dir = Path(f"../output/costorm_hybrid_thai/{topic}")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "costorm_article.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(article)
        
        print(f"✅ Saved: costorm_article.md ({len(article)} characters)")
        
        # Save additional files (Co-STORM format)
        import json
        
        # 1. Save conversation history (Co-STORM stores it in conversation_history)
        if hasattr(runner, 'conversation_history') and runner.conversation_history:
            conv_log = []
            for turn in runner.conversation_history:
                if hasattr(turn, 'to_dict'):
                    conv_log.append(turn.to_dict())
                else:
                    conv_log.append(str(turn))
            
            conv_file = output_dir / "conversation_log.json"
            with open(conv_file, 'w', encoding='utf-8') as f:
                json.dump(conv_log, f, ensure_ascii=False, indent=2)
            print(f"✅ Saved: conversation_log.json ({len(conv_log)} turns)")
        
        # 2. Save knowledge base (Co-STORM's version of outline)
        if hasattr(runner, 'knowledge_base'):
            kb_data = runner.knowledge_base.to_dict() if hasattr(runner.knowledge_base, 'to_dict') else str(runner.knowledge_base)
            kb_file = output_dir / "knowledge_base.json"
            with open(kb_file, 'w', encoding='utf-8') as f:
                json.dump(kb_data, f, ensure_ascii=False, indent=2)
            print(f"✅ Saved: knowledge_base.json")
        
        # 3. Save warm start conversations
        if hasattr(runner, 'warmstart_conv_archive') and runner.warmstart_conv_archive:
            warmstart_log = []
            for turn in runner.warmstart_conv_archive:
                if hasattr(turn, 'to_dict'):
                    warmstart_log.append(turn.to_dict())
                else:
                    warmstart_log.append(str(turn))
            
            warmstart_file = output_dir / "warmstart_conversations.json"
            with open(warmstart_file, 'w', encoding='utf-8') as f:
                json.dump(warmstart_log, f, ensure_ascii=False, indent=2)
            print(f"✅ Saved: warmstart_conversations.json ({len(warmstart_log)} conversations)")
        
        # 4. Save expert information
        if hasattr(runner, 'discourse_manager') and hasattr(runner.discourse_manager, 'serialize_experts'):
            experts_data = runner.discourse_manager.serialize_experts()
            experts_file = output_dir / "experts.json"
            with open(experts_file, 'w', encoding='utf-8') as f:
                json.dump(experts_data, f, ensure_ascii=False, indent=2)
            print(f"✅ Saved: experts.json")
        
        print()
        print("="*80)
        print("✅ บทความสร้างเสร็จแล้ว!")
        print("="*80)
        print(f"📁 บันทึกที่: {output_file}")
        print()
        print("📄 เนื้อหา:")
        print("="*80)
        print(article[:1000])  # Show first 1000 chars
        if len(article) > 1000:
            print("...")
            print(f"({len(article):,} characters total)")
        print("="*80)
        
    except Exception as e:
        print(f"❌ Error generating article: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
