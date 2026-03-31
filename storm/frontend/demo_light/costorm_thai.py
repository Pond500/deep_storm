"""
Co-STORM Thai - Streamlit Web UI
ระบบสร้างบทความแบบมีส่วนร่วม (Collaborative) ภาษาไทย
"""

import os
import sys
import streamlit as st
from pathlib import Path
import time
import json

# Add parent directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir.parent.parent))

from knowledge_storm.collaborative_storm.engine import (
    CollaborativeStormLMConfigs,
    RunnerArgument,
    CoStormRunner,
)
from knowledge_storm.lm import LitellmModel
from knowledge_storm.rm import TavilySearchRM
from knowledge_storm.logging_wrapper import LoggingWrapper
from thai_llm_wrapper import ThaiLitellmModel


def init_session_state():
    """Initialize Streamlit session state"""
    if "costorm_runner" not in st.session_state:
        st.session_state["costorm_runner"] = None
    if "conversation_history" not in st.session_state:
        st.session_state["conversation_history"] = []
    if "stage" not in st.session_state:
        st.session_state["stage"] = "topic_input"  # topic_input, warm_start, conversation, generating
    if "topic" not in st.session_state:
        st.session_state["topic"] = ""


def setup_costorm_runner(topic: str):
    """Setup Co-STORM runner with Thai support"""
    
    # Load API keys from secrets or environment
    llm_api_key = st.secrets.get("LLM__API_KEY") or os.getenv("LLM__API_KEY")
    llm_base_url = st.secrets.get("LLM__BASE_URL") or os.getenv("LLM__BASE_URL", "https://openrouter.ai/api/v1")
    llm_model_name = st.secrets.get("LLM__MODEL_NAME") or os.getenv("LLM__MODEL_NAME", "openai/gpt-4o-mini")
    tavily_key = st.secrets.get("TAVILY_API_KEY") or os.getenv("TAVILY_API_KEY")
    
    if not llm_api_key or not tavily_key:
        st.error("❌ ไม่พบ API keys! กรุณาตั้งค่าใน .streamlit/secrets.toml หรือ environment variables")
        st.info("""
        **วิธีตั้งค่า:**
        
        1. สร้างไฟล์ `.streamlit/secrets.toml` ในโฟลเดอร์นี้:
        ```toml
        LLM__API_KEY = "sk-or-v1-..."
        LLM__BASE_URL = "https://openrouter.ai/api/v1"
        LLM__MODEL_NAME = "openai/gpt-4o-mini"
        TAVILY_API_KEY = "tvly-dev-..."
        ```
        
        2. หรือตั้งค่า environment variables ก่อนรัน:
        ```bash
        export LLM__API_KEY="sk-or-v1-..."
        export TAVILY_API_KEY="tvly-dev-..."
        ```
        """)
        st.stop()
        return None
    
    # Set encoder environment variables
    os.environ["ENCODER_API_TYPE"] = "openai"
    os.environ["OPENAI_API_KEY"] = llm_api_key
    os.environ["OPENAI_API_BASE"] = llm_base_url
    
    # Configure LM configs
    lm_config = CollaborativeStormLMConfigs()
    
    llm_kwargs = {
        'api_key': llm_api_key,
        'api_base': llm_base_url,
        'temperature': 1.0,
        'top_p': 0.9,
    }
    
    # Setup all LMs with Thai wrapper
    question_answering_lm = ThaiLitellmModel(model=llm_model_name, max_tokens=2000, **llm_kwargs)
    discourse_manage_lm = ThaiLitellmModel(model=llm_model_name, max_tokens=500, **llm_kwargs)
    utterance_polishing_lm = ThaiLitellmModel(model=llm_model_name, max_tokens=2000, **llm_kwargs)
    warmstart_outline_gen_lm = ThaiLitellmModel(model=llm_model_name, max_tokens=1000, **llm_kwargs)
    question_asking_lm = ThaiLitellmModel(model=llm_model_name, max_tokens=500, **llm_kwargs)
    knowledge_base_lm = ThaiLitellmModel(model=llm_model_name, max_tokens=2000, **llm_kwargs)
    
    lm_config.set_question_answering_lm(question_answering_lm)
    lm_config.set_discourse_manage_lm(discourse_manage_lm)
    lm_config.set_utterance_polishing_lm(utterance_polishing_lm)
    lm_config.set_warmstart_outline_gen_lm(warmstart_outline_gen_lm)
    lm_config.set_question_asking_lm(question_asking_lm)
    lm_config.set_knowledge_base_lm(knowledge_base_lm)
    
    # Setup runner arguments
    runner_argument = RunnerArgument(
        topic=topic,
        retrieve_top_k=3,
        max_search_queries=2,
        total_conv_turn=10,
        max_search_thread=1,
        max_search_queries_per_turn=2,
        warmstart_max_num_experts=2,
        warmstart_max_turn_per_experts=1,
        warmstart_max_thread=1,
        max_thread_num=1,
        max_num_round_table_experts=3,
        moderator_override_N_consecutive_answering_turn=3,
        node_expansion_trigger_count=10,
    )
    
    # Setup retrieval module
    rm = TavilySearchRM(
        tavily_search_api_key=tavily_key,
        k=runner_argument.retrieve_top_k,
        include_raw_content=True,
    )
    
    logging_wrapper = LoggingWrapper(lm_config)
    
    # Create Co-STORM runner
    runner = CoStormRunner(
        lm_config=lm_config,
        runner_argument=runner_argument,
        logging_wrapper=logging_wrapper,
        rm=rm,
        callback_handler=None,
    )
    
    return runner


def main():
    st.set_page_config(
        page_title="Co-STORM Thai",
        page_icon="🤝",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .main-header {
            font-size: 3rem;
            font-weight: bold;
            text-align: center;
            margin-bottom: 1rem;
        }
        .chat-message {
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
        }
        .expert-message {
            background-color: #f0f2f6;
            border-left: 4px solid #1f77b4;
        }
        .user-message {
            background-color: #e8f4f8;
            border-left: 4px solid #2ca02c;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<p class="main-header">🤝 Co-STORM Thai</p>', unsafe_allow_html=True)
    st.markdown("### ระบบสร้างบทความแบบมีส่วนร่วม (ภาษาไทย)")
    
    init_session_state()
    
    # Sidebar
    with st.sidebar:
        st.header("📊 สถานะ")
        
        if st.session_state["stage"] == "topic_input":
            st.info("รอการระบุหัวข้อ...")
        elif st.session_state["stage"] == "warm_start":
            st.warning("กำลัง warm start...")
        elif st.session_state["stage"] == "conversation":
            st.success(f"กำลังสนทนา ({len(st.session_state['conversation_history'])} รอบ)")
        elif st.session_state["stage"] == "generating":
            st.info("กำลังสร้างบทความ...")
        
        st.divider()
        
        st.header("💡 คำแนะนำ")
        st.markdown("""
        **วิธีใช้งาน:**
        1. พิมพ์หัวข้อที่ต้องการ
        2. รอ warm start (~30-60 วินาที)
        3. สนทนากับ AI experts
        4. พิมพ์ "done" เมื่อต้องการสร้างบทความ
        
        **คำสั่งในการสนทนา:**
        - ตอบคำถาม / ถามคำถามใหม่
        - พิมพ์ "skip" = ให้ AI คุยต่อ
        - พิมพ์ "done" = สร้างบทความ
        """)
    
    # Main content
    if st.session_state["stage"] == "topic_input":
        show_topic_input()
    elif st.session_state["stage"] == "warm_start":
        show_warm_start()
    elif st.session_state["stage"] == "conversation":
        show_conversation()
    elif st.session_state["stage"] == "generating":
        show_generating()


def show_topic_input():
    """Show topic input form"""
    st.markdown("### 📝 พิมพ์หัวข้อที่ต้องการสร้างบทความ")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("topic_form"):
            topic = st.text_input(
                "หัวข้อ",
                placeholder="เช่น: ประวัติศาสตร์ Bitcoin, การทำงานของ Blockchain",
                help="พิมพ์หัวข้อที่คุณอยากเรียนรู้เชิงลึก"
            )
            
            st.markdown("**ตัวอย่างหัวข้อ:**")
            st.markdown("- Bitcoin และผลกระทบต่อระบบเศรษฐกิจ")
            st.markdown("- ประวัติและวิวัฒนาการของ AI")
            st.markdown("- การเปลี่ยนแปลงสภาพภูมิอากาศในประเทศไทย")
            
            submit = st.form_submit_button("🚀 เริ่มต้น", use_container_width=True)
            
            if submit:
                if not topic.strip():
                    st.error("กรุณาระบุหัวข้อ")
                else:
                    st.session_state["topic"] = topic
                    st.session_state["stage"] = "warm_start"
                    st.rerun()


def show_warm_start():
    """Show warm start progress"""
    st.markdown(f"### 🎯 หัวข้อ: {st.session_state['topic']}")
    
    with st.spinner("กำลังเตรียมข้อมูลเบื้องต้น... (อาจใช้เวลา 30-60 วินาที)"):
        try:
            # Setup runner
            runner = setup_costorm_runner(st.session_state["topic"])
            st.session_state["costorm_runner"] = runner
            
            # Warm start
            runner.warm_start()
            
            st.session_state["stage"] = "conversation"
            st.success("✅ เตรียมข้อมูลเสร็จสิ้น - พร้อมสนทนา!")
            time.sleep(2)
            st.rerun()
            
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")
            if st.button("ลองใหม่"):
                st.session_state["stage"] = "topic_input"
                st.rerun()


def show_conversation():
    """Show conversation interface"""
    st.markdown(f"### 💬 สนทนาเกี่ยวกับ: {st.session_state['topic']}")
    
    runner = st.session_state["costorm_runner"]
    
    # Display conversation history
    for msg in st.session_state["conversation_history"]:
        if msg["role"] == "expert":
            st.markdown(f"""
            <div class="chat-message expert-message">
                <strong>🤖 {msg['name']}:</strong><br>
                {msg['content']}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>👤 คุณ:</strong><br>
                {msg['content']}
            </div>
            """, unsafe_allow_html=True)
    
    # Get next AI turn
    if len(st.session_state["conversation_history"]) == 0 or \
       st.session_state["conversation_history"][-1]["role"] == "user":
        
        with st.spinner("กำลังคิด..."):
            try:
                conv_turn = runner.step()
                
                if conv_turn:
                    st.session_state["conversation_history"].append({
                        "role": "expert",
                        "name": conv_turn.role,
                        "content": conv_turn.utterance
                    })
                    st.rerun()
                    
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")
    
    # User input
    st.divider()
    user_input = st.text_input(
        "💬 ข้อความของคุณ:",
        placeholder="ตอบคำถาม / ถามคำถามใหม่ / พิมพ์ 'skip' หรือ 'done'",
        key=f"user_input_{len(st.session_state['conversation_history'])}"
    )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📨 ส่งข้อความ", use_container_width=True):
            if user_input.strip():
                handle_user_input(user_input)
    
    with col2:
        if st.button("⏩ ข้าม (Skip)", use_container_width=True):
            handle_user_input("skip")
    
    with col3:
        if st.button("✅ สร้างบทความ (Done)", use_container_width=True):
            handle_user_input("done")


def handle_user_input(user_input: str):
    """Handle user input"""
    runner = st.session_state["costorm_runner"]
    
    if user_input.lower() == "done":
        st.session_state["stage"] = "generating"
        st.rerun()
        return
    
    if user_input.lower() == "skip":
        st.session_state["conversation_history"].append({
            "role": "user",
            "name": "คุณ",
            "content": "[ข้าม - ให้ AI คุยต่อ]"
        })
        st.rerun()
        return
    
    # Send user utterance to Co-STORM
    runner.step(user_utterance=user_input)
    
    st.session_state["conversation_history"].append({
        "role": "user",
        "name": "คุณ",
        "content": user_input
    })
    
    st.rerun()


def show_generating():
    """Show article generation"""
    st.markdown(f"### 📝 กำลังสร้างบทความ: {st.session_state['topic']}")
    
    runner = st.session_state["costorm_runner"]
    
    with st.spinner("กำลังประมวลผลและเขียนบทความ... (อาจใช้เวลา 2-3 นาที)"):
        try:
            # Reorganize knowledge base
            runner.knowledge_base.reorganize()
            
            # Generate article
            article = runner.generate_report()
            
            # Save article
            output_dir = Path("output/costorm_thai_articles") / st.session_state["topic"].replace(" ", "_")[:50]
            output_dir.mkdir(parents=True, exist_ok=True)
            
            article_path = output_dir / "costorm_article.md"
            with open(article_path, "w", encoding="utf-8") as f:
                f.write(article)
            
            # Display article
            st.success("✅ สร้างบทความสำเร็จ!")
            st.divider()
            st.markdown(article)
            
            st.divider()
            st.info(f"📁 บทความถูกบันทึกที่: `{article_path}`")
            
            # Reset button
            if st.button("🔄 เริ่มต้นใหม่"):
                st.session_state.clear()
                st.rerun()
                
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")
            if st.button("ลองใหม่"):
                st.session_state["stage"] = "conversation"
                st.rerun()


if __name__ == "__main__":
    main()
