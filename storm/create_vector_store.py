"""
สร้าง Qdrant Vector Store จาก Wikipedia CSV
รองรับ offline mode (local storage) - ไม่ต้อง Qdrant server
"""

import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from knowledge_storm.utils import QdrantVectorStoreManager


def create_vector_store(
    csv_file: str,
    vector_store_path: str = "./vector_store",
    collection_name: str = "wikipedia_thai",
    embedding_model: str = "BAAI/bge-m3",
    device: str = "mps",
    batch_size: int = 32,
):
    """
    สร้าง Qdrant Vector Store แบบ offline (local)
    
    Parameters:
    -----------
    csv_file: CSV file path (จาก lmdb_to_csv.py)
    vector_store_path: โฟลเดอร์เก็บ vector store
    collection_name: ชื่อ collection
    embedding_model: HuggingFace model สำหรับ embeddings
        - BAAI/bge-m3: multilingual, ดีสำหรับภาษาไทย (แนะนำ)
        - intfloat/multilingual-e5-base: เล็กกว่า เร็วกว่า
        - sentence-transformers/paraphrase-multilingual-mpnet-base-v2
    device: "mps" (Mac M1/M2), "cuda" (NVIDIA GPU), "cpu"
    batch_size: ขนาด batch สำหรับ embedding (ลดถ้า out of memory)
    
    Returns:
    --------
    None (สร้าง vector store ใน vector_store_path)
    """
    
    print("="*80)
    print("🚀 Creating Qdrant Vector Store (Offline Mode)")
    print("="*80)
    print(f"📁 CSV file: {csv_file}")
    print(f"📂 Vector store path: {vector_store_path}")
    print(f"🤖 Embedding model: {embedding_model}")
    print(f"💻 Device: {device}")
    print(f"📦 Collection name: {collection_name}")
    print(f"🔢 Batch size: {batch_size}")
    print("="*80)
    print()
    
    # ตรวจสอบ CSV file
    if not os.path.exists(csv_file):
        print(f"❌ Error: CSV file not found: {csv_file}")
        print("💡 กรุณารัน: python lmdb_to_csv.py ก่อน")
        exit(1)
    
    file_size = os.path.getsize(csv_file) / 1024 / 1024
    print(f"📊 CSV file size: {file_size:.2f} MB")
    print()
    
    # นับจำนวน rows
    import csv
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        total_rows = sum(1 for row in reader) - 1  # -1 for header
    print(f"📈 Total documents: {total_rows:,}")
    print()
    
    # สร้าง vector store
    print("🔄 Creating vector store... (อาจใช้เวลา 30-60 นาที)")
    print("💡 Tips:")
    print("   - ขนาด corpus: ~237K docs → ใช้เวลา ~45-60 นาที")
    print("   - ถ้าต้องการทดสอบก่อน: ใช้ --max-entries 1000 ใน lmdb_to_csv.py")
    print("   - ถ้า out of memory: ลด --batch-size")
    print()
    
    try:
        QdrantVectorStoreManager.create_or_update_vector_store(
            vector_store_path=vector_store_path,
            file_path=csv_file,
            content_column="content",
            title_column="title",
            url_column="url",
            desc_column="description",
            batch_size=batch_size,
            vector_db_mode="offline",
            collection_name=collection_name,
            embedding_model=embedding_model,
            device=device,
        )
        
        print()
        print("="*80)
        print("✅ Vector store created successfully!")
        print("="*80)
        print(f"📍 Location: {vector_store_path}")
        print(f"📦 Collection: {collection_name}")
        print(f"📊 Documents: {total_rows:,}")
        print("="*80)
        
    except Exception as e:
        print()
        print("="*80)
        print("❌ Error creating vector store:")
        print("="*80)
        print(f"{e}")
        print()
        print("💡 Troubleshooting:")
        print("   1. Out of memory → ลด --batch-size (เช่น 16 หรือ 8)")
        print("   2. Model download error → ตรวจสอบ internet connection")
        print("   3. Device error → เปลี่ยน --device (mps → cpu)")
        exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="สร้าง Qdrant Vector Store จาก Wikipedia CSV (Offline Mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
ตัวอย่างการใช้งาน:
  # สร้าง vector store แบบ default
  python create_vector_store.py --csv-file wikipedia_thai.csv
  
  # กำหนด path และ model
  python create_vector_store.py \\
    --csv-file wikipedia_thai.csv \\
    --vector-store-path ./my_vector_db \\
    --embedding-model intfloat/multilingual-e5-base
  
  # สำหรับ CPU (ไม่มี GPU/MPS)
  python create_vector_store.py \\
    --csv-file wikipedia_thai.csv \\
    --device cpu \\
    --batch-size 16
  
  # สำหรับ NVIDIA GPU
  python create_vector_store.py \\
    --csv-file wikipedia_thai.csv \\
    --device cuda \\
    --batch-size 64

⚠️ หมายเหตุ:
  - ครั้งแรกจะ download embedding model (~500MB-1GB)
  - Vector store size ≈ 2-3x ของ CSV file
  - Mac M1/M2: ใช้ device=mps (เร็วกว่า cpu มาก)
        """
    )
    
    parser.add_argument(
        "--csv-file",
        type=str,
        required=True,
        help="Path to Wikipedia CSV file (จาก lmdb_to_csv.py)"
    )
    parser.add_argument(
        "--vector-store-path",
        type=str,
        default="./vector_store",
        help="Directory to store vector database (default: ./vector_store)"
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default="wikipedia_thai",
        help="Collection name in vector store (default: wikipedia_thai)"
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default="BAAI/bge-m3",
        help="HuggingFace embedding model (default: BAAI/bge-m3)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="mps",
        choices=["mps", "cuda", "cpu"],
        help="Device for embedding model (default: mps for Mac M1/M2)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for embedding (default: 32, ลดถ้า OOM)"
    )
    
    args = parser.parse_args()
    
    # Run
    create_vector_store(
        csv_file=args.csv_file,
        vector_store_path=args.vector_store_path,
        collection_name=args.collection_name,
        embedding_model=args.embedding_model,
        device=args.device,
        batch_size=args.batch_size,
    )
    
    print()
    print("🎯 Next steps:")
    print("  1. ทดสอบ Vector Search:")
    print("     python test_vector_search.py")
    print()
    print("  2. ใช้กับ Co-STORM:")
    print("     python test_costorm_vector.py")
    print()
    print("  3. ใช้กับ Web UI:")
    print("     streamlit run frontend/demo_light/costorm_vector_thai.py")
