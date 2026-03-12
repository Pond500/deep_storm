"""
แปลง Wikipedia LMDB → CSV สำหรับ VectorRM
รองรับ Thai Wikipedia corpus (237,290 บทความ)
"""

import lmdb
import csv
import os
from tqdm import tqdm


def lmdb_to_csv(lmdb_path: str, output_csv: str, max_entries: int = None):
    """
    แปลง LMDB database เป็น CSV format สำหรับ VectorRM
    
    CSV Format ที่ VectorRM ต้องการ:
    content | title | url | description
    
    Args:
        lmdb_path: path to LMDB database folder
        output_csv: output CSV file path
        max_entries: จำกัดจำนวน entries (None = ทั้งหมด)
    """
    
    print("="*70)
    print("🔄 Converting Wikipedia LMDB → CSV for VectorRM")
    print("="*70)
    
    # เปิด LMDB
    print(f"📂 Opening LMDB: {lmdb_path}")
    env = lmdb.open(lmdb_path, readonly=True, max_dbs=0)
    
    # นับจำนวน entries
    with env.begin() as txn:
        stat = env.stat()
        total_entries = stat["entries"]
        
    if max_entries:
        total_entries = min(total_entries, max_entries)
    
    print(f"📊 Total entries to process: {total_entries:,}")
    print(f"📝 Output CSV: {output_csv}")
    print()
    
    # เขียนลง CSV
    processed = 0
    skipped = 0
    
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(['content', 'title', 'url', 'description'])
        
        with env.begin() as txn:
            cursor = txn.cursor()
            
            for i, (key, value) in enumerate(tqdm(cursor, total=total_entries, desc="Converting")):
                if max_entries and i >= max_entries:
                    break
                
                try:
                    # Decode key-value
                    title = key.decode('utf-8', errors='ignore').strip()
                    content = value.decode('utf-8', errors='ignore').strip()
                    
                    # Skip empty or too short content
                    if not content or len(content) < 50:
                        skipped += 1
                        continue
                    
                    # สร้าง unique URL
                    url = f"wiki://{title.replace(' ', '_')}"
                    
                    # Description = 150 ตัวอักษรแรก
                    description = content[:150].replace('\n', ' ').strip()
                    if len(content) > 150:
                        description += "..."
                    
                    # เขียน row
                    writer.writerow([content, title, url, description])
                    processed += 1
                    
                except Exception as e:
                    print(f"\n⚠️  Error at entry {i}: {e}")
                    skipped += 1
                    continue
    
    env.close()
    
    # Summary
    file_size = os.path.getsize(output_csv) / 1024 / 1024
    
    print()
    print("="*70)
    print("✅ Conversion completed!")
    print("="*70)
    print(f"📦 Output file: {output_csv}")
    print(f"📏 File size: {file_size:.2f} MB")
    print(f"✅ Processed: {processed:,} entries")
    print(f"⏭️  Skipped: {skipped:,} entries")
    print("="*70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="แปลง Wikipedia LMDB → CSV สำหรับ VectorRM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
ตัวอย่างการใช้งาน:
  # แปลงทั้งหมด (~237K entries)
  python lmdb_to_csv.py
  
  # แปลงเฉพาะ 10,000 entries (สำหรับทดสอบ)
  python lmdb_to_csv.py --max-entries 10000
  
  # กำหนด output path
  python lmdb_to_csv.py --output-csv data/wikipedia_thai.csv
        """
    )
    
    parser.add_argument(
        "--lmdb-path",
        type=str,
        default="redirects.lmdb",
        help="Path to LMDB database folder (default: redirects.lmdb)"
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="wikipedia_thai.csv",
        help="Output CSV file path (default: wikipedia_thai.csv)"
    )
    parser.add_argument(
        "--max-entries",
        type=int,
        default=None,
        help="Maximum entries to convert (default: None = ทั้งหมด)"
    )
    
    args = parser.parse_args()
    
    # Validate LMDB path
    if not os.path.exists(args.lmdb_path):
        print(f"❌ Error: LMDB path not found: {args.lmdb_path}")
        exit(1)
    
    # Run conversion
    lmdb_to_csv(args.lmdb_path, args.output_csv, args.max_entries)
    
    print()
    print("🎯 Next steps:")
    print("  1. สร้าง Vector Store:")
    print(f"     python create_vector_store.py --csv-file {args.output_csv}")
    print()
    print("  2. ทดสอบ Vector Search:")
    print("     python test_vector_search.py")
    print()
    print("  3. ใช้กับ Co-STORM:")
    print("     python test_costorm_vector.py")
