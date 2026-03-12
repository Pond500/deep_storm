"""
รวม Wikipedia CSV batches และแปลงเป็น format ที่ VectorRM ต้องการ
Input: batch_001.csv, batch_002.csv, ... (10 files)
Output: wikipedia_thai_vectorrm.csv (format: content, title, url, description)
"""

import pandas as pd
import os
from pathlib import Path
from tqdm import tqdm


def prepare_wikipedia_data(
    input_dir: str = "./extracted_data",
    output_file: str = "./wikipedia_thai_vectorrm.csv",
    max_content_length: int = 5000,
    min_content_length: int = 100,
):
    """
    รวมและแปลง CSV batches เป็น format สำหรับ VectorRM
    
    Args:
        input_dir: โฟลเดอร์ที่มี batch_*.csv
        output_file: ไฟล์ output
        max_content_length: ความยาวสูงสุดของ content (ตัด overhead)
        min_content_length: ความยาวต่ำสุด (กรองบทความสั้นเกินไป)
    """
    
    print("="*80)
    print("🔄 Preparing Wikipedia Thai Data for VectorRM")
    print("="*80)
    print(f"📂 Input directory: {input_dir}")
    print(f"📝 Output file: {output_file}")
    print()
    
    # หา batch files
    batch_files = sorted(Path(input_dir).glob("batch_*.csv"))
    print(f"📊 Found {len(batch_files)} batch files:")
    for f in batch_files:
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"   - {f.name} ({size_mb:.2f} MB)")
    print()
    
    # เตรียม output
    output_rows = []
    total_processed = 0
    total_skipped = 0
    
    # Process แต่ละ batch
    for batch_file in batch_files:
        print(f"🔄 Processing {batch_file.name}...")
        
        try:
            # อ่าน CSV
            df = pd.read_csv(batch_file)
            print(f"   Rows: {len(df):,}")
            
            # กรอง namespace = "(Main)" (main article namespace)
            if 'namespace' in df.columns:
                df = df[df['namespace'] == '(Main)']
                print(f"   After namespace filter: {len(df):,}")
            
            # กรอง redirects
            if 'is_redirect' in df.columns:
                df = df[df['is_redirect'] == False]
                print(f"   After redirect filter: {len(df):,}")
            
            # Process แต่ละ row
            for _, row in df.iterrows():
                try:
                    title = str(row.get('title', '')).strip()
                    text = str(row.get('text', '')).strip()
                    
                    # Skip empty or too short
                    if not title or not text or len(text) < min_content_length:
                        total_skipped += 1
                        continue
                    
                    # Truncate long content
                    if len(text) > max_content_length:
                        text = text[:max_content_length] + "..."
                    
                    # สร้าง URL
                    url = f"wiki://th/{title.replace(' ', '_')}"
                    
                    # สร้าง description (200 chars)
                    description = text[:200].replace('\n', ' ').strip()
                    if len(text) > 200:
                        description += "..."
                    
                    # เพิ่ม row
                    output_rows.append({
                        'content': text,
                        'title': title,
                        'url': url,
                        'description': description,
                    })
                    
                    total_processed += 1
                    
                except Exception as e:
                    total_skipped += 1
                    continue
            
            print(f"   ✅ Processed: {len(df):,} rows")
            print()
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    # สร้าง output DataFrame
    print("📦 Creating output CSV...")
    output_df = pd.DataFrame(output_rows)
    
    # บันทึก
    output_df.to_csv(output_file, index=False, encoding='utf-8')
    
    # Summary
    output_size = Path(output_file).stat().st_size / 1024 / 1024
    
    print()
    print("="*80)
    print("✅ Data preparation completed!")
    print("="*80)
    print(f"📦 Output file: {output_file}")
    print(f"📏 File size: {output_size:.2f} MB")
    print(f"✅ Total articles: {total_processed:,}")
    print(f"⏭️  Skipped: {total_skipped:,}")
    print(f"📊 Columns: {list(output_df.columns)}")
    print("="*80)
    
    # แสดงตัวอย่าง
    print()
    print("📄 Sample data:")
    print(output_df.head(3).to_string())
    
    return output_file


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="รวมและแปลง Wikipedia CSV batches สำหรับ VectorRM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
ตัวอย่างการใช้งาน:
  # แปลงทั้งหมด (default)
  python prepare_wikipedia_data.py
  
  # กำหนด output path
  python prepare_wikipedia_data.py --output-file ../wikipedia_thai.csv
  
  # ปรับ content length
  python prepare_wikipedia_data.py --max-content 10000 --min-content 50

Output format (VectorRM compatible):
  content     | title      | url                  | description
  บทความเต็ม  | หัวข้อ      | wiki://th/หัวข้อ      | สรุป 200 ตัวอักษร
        """
    )
    
    parser.add_argument(
        "--input-dir",
        type=str,
        default="./extracted_data",
        help="Directory containing batch_*.csv files"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="./wikipedia_thai_vectorrm.csv",
        help="Output CSV file path"
    )
    parser.add_argument(
        "--max-content",
        type=int,
        default=5000,
        help="Maximum content length (default: 5000)"
    )
    parser.add_argument(
        "--min-content",
        type=int,
        default=100,
        help="Minimum content length (default: 100)"
    )
    
    args = parser.parse_args()
    
    output_file = prepare_wikipedia_data(
        input_dir=args.input_dir,
        output_file=args.output_file,
        max_content_length=args.max_content,
        min_content_length=args.min_content,
    )
    
    print()
    print("🎯 Next steps:")
    print("  1. สร้าง Vector Store:")
    print(f"     python create_vector_store.py --csv-file {output_file}")
    print()
    print("  2. ทดสอบ Vector Search:")
    print("     python test_vector_search.py")
    print()
    print("  3. ใช้กับ Co-STORM:")
    print("     python test_costorm_vector.py")
