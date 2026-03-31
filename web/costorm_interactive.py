"""
Interactive Co-STORM implementation for web UI
"""
import asyncio
import json
from pathlib import Path


async def run_costorm_interactive(topic: str, client_id: str, send_progress, send_question, settings: dict = None):
    """
    Run Co-STORM in interactive mode
    
    Args:
        topic: Article topic
        client_id: WebSocket client ID
        send_progress: Async function to send progress updates
        send_question: Async function to send questions and wait for responses
        settings: Optional dict with research parameters
    """
    try:
        # Use default settings if not provided
        if settings is None:
            settings = {
                "total_conv_turn": 20,
                "retrieve_top_k": 5,
                "max_search_queries": 3,
                "warmstart_max_num_experts": 2,
                "warmstart_max_turn_per_experts": 2,
                "max_num_round_table_experts": 2
            }
        
        print(f"⚙️ Co-STORM Settings: {settings}")
        
        # Import Co-STORM modules
        from knowledge_storm.collaborative_storm.engine import (
            RunnerArgument,
            CoStormRunner,
            LMConfigs,
        )
        from hybrid_wikipedia_rm import get_shared_instance as get_shared_rm
        from knowledge_storm.logging_wrapper import LoggingWrapper
        from thai_llm_wrapper import ThaiLitellmModel
        
        # Step 1: Setup (5-25%)
        await send_progress(client_id, "setup", 5, "เตรียมระบบ Co-STORM...")
        
        # Set environment variables (same as STORM)
        import os
        import sys
        
        # Env vars (OPENAI_API_KEY, OPENAI_API_BASE) are set globally in app.py at startup.
        # No per-request setup needed.
        
        await send_progress(client_id, "setup", 10, "กำหนดค่า AI models...")
        
        # Get API key — validate format to skip placeholder values like YOUR_NEW_KEY_HERE
        _fallback = "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"
        _env_key = os.environ.get("OPENROUTER_API_KEY", "")
        _api_key = _env_key if _env_key.startswith("sk-or-") else _fallback
        os.environ["OPENROUTER_API_KEY"] = _api_key  # ensure always set correctly
        
        # Setup LM configs
        lm_config = LMConfigs()
        common_kwargs = {"api_key": _api_key}
        
        # Configure all LMs
        lm_config.discourse_manage_lm = ThaiLitellmModel(
            model="openrouter/openai/gpt-4o-mini",
            max_tokens=500,
            temperature=1.0,
            top_p=0.9,
            **common_kwargs,
        )
        
        lm_config.utterance_polishing_lm = ThaiLitellmModel(
            model="openrouter/openai/gpt-4o-mini",
            max_tokens=2000,
            temperature=1.0,
            top_p=0.9,
            **common_kwargs,
        )
        
        lm_config.warmstart_outline_gen_lm = ThaiLitellmModel(
            model="openrouter/openai/gpt-4o-mini",
            max_tokens=500,
            temperature=1.0,
            top_p=0.9,
            **common_kwargs,
        )
        
        lm_config.question_asking_lm = ThaiLitellmModel(
            model="openrouter/openai/gpt-4o-mini",
            max_tokens=300,
            temperature=1.0,
            top_p=0.9,
            **common_kwargs,
        )
        
        lm_config.knowledge_base_lm = ThaiLitellmModel(
            model="openrouter/openai/gpt-4o-mini",
            max_tokens=1000,
            temperature=1.0,
            top_p=0.9,
            **common_kwargs,
        )
        
        lm_config.question_answering_lm = ThaiLitellmModel(
            model="openrouter/openai/gpt-4o-mini",
            max_tokens=1000,
            temperature=1.0,
            top_p=0.9,
            **common_kwargs,
        )
        
        await send_progress(client_id, "retrieval", 20, "เชื่อมต่อกับฐานข้อมูล Wikipedia...")
        
        # Setup runner arguments with user settings
        runner_argument = RunnerArgument(
            topic=topic,
            retrieve_top_k=settings.get("retrieve_top_k", 5),
            max_search_queries=settings.get("max_search_queries", 3),
            total_conv_turn=settings.get("total_conv_turn", 20),
            warmstart_max_num_experts=settings.get("warmstart_max_num_experts", 2),
            warmstart_max_turn_per_experts=settings.get("warmstart_max_turn_per_experts", 2),
            max_num_round_table_experts=settings.get("max_num_round_table_experts", 2),
        )
        
        # Setup Hybrid Retrieval
        rm = get_shared_rm(
            vector_store_path=str(Path(__file__).parent.parent / "storm" / "wiki" / "vector_store"),
            collection_name="wikipedia_thai",
            embedding_model="BAAI/bge-m3",
            reranker_model="BAAI/bge-reranker-v2-m3",
            device="mps",
            k=5,
            use_reranking=True,
            rerank_top_k=20,
            alpha=0.5,
        )
        
        logging_wrapper = LoggingWrapper(lm_config)
        
        await send_progress(client_id, "init", 25, "ระบบพร้อมแล้ว เริ่มการสนทนา...")
        
        # Create runner
        runner = CoStormRunner(
            lm_config=lm_config,
            runner_argument=runner_argument,
            logging_wrapper=logging_wrapper,
            rm=rm,
        )
        
        # Step 2: Warmstart (25-40%)
        await send_progress(client_id, "warmstart", 30, "กำลังเตรียมข้อมูลเบื้องต้น...")
        
        loop = asyncio.get_event_loop()
        
        # Warmstart
        await loop.run_in_executor(None, runner.warm_start)
        await send_progress(client_id, "warmstart", 40, "ระบบพร้อมสำหรับการสนทนา!")
        
        # Step 3: Interactive conversation (40-85%)
        max_turns = runner_argument.total_conv_turn
        current_turn = 0
        
        await send_progress(client_id, "conversation", 40, "เริ่มการสนทนาเพื่อรวบรวมข้อมูล...")
        
        while current_turn < max_turns:
            # Calculate progress (40% to 85% over max_turns)
            progress = 40 + int((current_turn / max_turns) * 45)
            
            # Get user input
            try:
                # Get moderator's question (this is the actual Co-STORM question!)
                await send_progress(client_id, "conversation", progress, f"รอบที่ {current_turn + 1}/{max_turns}: กำลังสร้างคำถาม...")
                
                moderator_question = await loop.run_in_executor(None, runner.step)
                
                if not moderator_question:
                    print(f"   ✅ No more questions from moderator - conversation complete")
                    break
                
                # Extract question text
                question_text = moderator_question.utterance if hasattr(moderator_question, 'utterance') else str(moderator_question)
                
                print(f"\n🤖 Moderator (Turn {current_turn + 1}): {question_text[:100]}...")
                
                # Send question to user
                await send_progress(client_id, "conversation", progress + 1, f"รอบที่ {current_turn + 1}/{max_turns}: รอคำตอบจากคุณ...")
                
                user_utterance = await send_question(
                    client_id,
                    question_text,
                    f"รอบที่ {current_turn + 1}/{max_turns} - พิมพ์คำตอบ, SKIP (ให้ AI ตอบ), หรือ DONE (สิ้นสุด)"
                )
                
                if user_utterance == "DONE":
                    print(f"   ✅ User requested DONE at turn {current_turn}")
                    break
                    
                if user_utterance == "SKIP" or not user_utterance:
                    print(f"   ⏭️  User SKIPped - AI will simulate user response")
                    user_utterance = ""
                
                # Process the turn
                await send_progress(client_id, "conversation", progress + 2, f"รอบที่ {current_turn + 1}: กำลังประมวลผลคำตอบ...")
                
                await loop.run_in_executor(
                    None,
                    lambda u=user_utterance: runner.step(user_utterance=u if u else "", simulate_user=(not u))
                )
                
                current_turn += 1
                
            except IndexError as e:
                print(f"   ⚠️  Conversation history empty - warm start may have failed")
                print(f"   Error: {e}")
                break
            except Exception as e:
                print(f"   ❌ Error in conversation turn {current_turn}: {e}")
                import traceback
                traceback.print_exc()
                break
        
        await send_progress(client_id, "conversation", 85, "การสนทนาเสร็จสิ้น!")
        
        # Step 4: Generate report (85-95%)
        await send_progress(client_id, "writing", 90, "กำลังเขียนบทความจากผลการสนทนา...")
        
        article = await loop.run_in_executor(None, runner.generate_report)
        
        # Step 5: Save files (95-100%)
        await send_progress(client_id, "saving", 95, "กำลังบันทึกไฟล์...")
        
        # Create output directory
        import json
        output_dir = Path("../storm/output/web_api") / topic
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save article
        article_file = output_dir / "costorm_article.txt"
        with open(article_file, 'w', encoding='utf-8') as f:
            f.write(article)
        print(f"   ✅ Saved: {article_file} ({len(article):,} chars)")
        
        # Save conversation log
        if hasattr(runner, 'conversation_history') and runner.conversation_history:
            conv_log = []
            for turn in runner.conversation_history:
                if hasattr(turn, 'to_dict'):
                    conv_log.append(turn.to_dict())
                else:
                    conv_log.append({
                        "utterance": turn.utterance if hasattr(turn, 'utterance') else str(turn),
                        "role": turn.role if hasattr(turn, 'role') else "unknown"
                    })
            
            conv_file = output_dir / "conversation_log.json"
            with open(conv_file, 'w', encoding='utf-8') as f:
                json.dump(conv_log, f, ensure_ascii=False, indent=2)
            print(f"   ✅ Saved: {conv_file} ({len(conv_log)} turns)")
        
        # Save knowledge base
        if hasattr(runner, 'knowledge_base'):
            try:
                kb_data = runner.knowledge_base.to_dict() if hasattr(runner.knowledge_base, 'to_dict') else str(runner.knowledge_base)
                kb_file = output_dir / "knowledge_base.json"
                with open(kb_file, 'w', encoding='utf-8') as f:
                    json.dump(kb_data, f, ensure_ascii=False, indent=2)
                print(f"   ✅ Saved: {kb_file}")
            except Exception as e:
                print(f"   ⚠️  Could not save knowledge base: {e}")
                import traceback
                traceback.print_exc()
        
        # Extract references from knowledge_base
        references = {}
        
        if hasattr(runner, 'knowledge_base'):
            try:
                # Access info_uuid_to_info_dict from knowledge_base
                info_dict = runner.knowledge_base.info_uuid_to_info_dict
                
                for citation_uuid, info in info_dict.items():
                    # Extract URL and convert wiki:// format to https://
                    url = info.url
                    if url.startswith("wiki://th/"):
                        url = url.replace("wiki://th/", "https://th.wikipedia.org/wiki/")
                    
                    # Get snippet (use first one if multiple)
                    snippet = info.snippets[0] if info.snippets else ""
                    
                    # Store reference
                    references[str(citation_uuid)] = {
                        "title": info.title,
                        "url": url,
                        "snippet": snippet[:200] + ("..." if len(snippet) > 200 else "")  # Limit snippet length
                    }
                
                if references:
                    print(f"   ✅ Extracted {len(references)} real references from knowledge base")
                else:
                    print(f"   ⚠️  No references found in knowledge base")
                    
            except Exception as e:
                print(f"   ⚠️  Could not extract references from knowledge_base: {e}")
                import traceback
                traceback.print_exc()
        
        await send_progress(client_id, "complete", 100, f"สร้างบทความเสร็จสมบูรณ์! บันทึกที่ {output_dir}")
        
        metadata = {
            "mode": "costorm",
            "turns": current_turn,
            "length": len(article),
            "output_dir": str(output_dir),
            "references": references  # Add references
        }
        
        return article, metadata
        
    except Exception as e:
        print(f"Co-STORM Error: {e}")
        raise
