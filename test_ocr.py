# backend/test_ocr.py - Test OCR with an actual image
import os
from ocr_service import extract_medicines_from_prescription

# Path to a sample prescription image (create one or use any medical image)
# For testing, you can use any image with handwritten or printed text
sample_image = "test_prescription.jpg"  # Replace with your image path

if not os.path.exists(sample_image):
    print("⚠️ No test image found. Please add a prescription image to test.")
    print("   You can take a photo of any prescription or medical label.")
else:
    print("🔍 Testing OCR on:", sample_image)
    result = extract_medicines_from_prescription(sample_image)
    
    print("\n" + "="*50)
    print("📊 OCR Results:")
    print("="*50)
    print(f"Success: {result['success']}")
    
    if result['success']:
        print(f"\n💊 Medicines Found ({len(result['medicines'])}):")
        for med in result['medicines']:
            print(f"   - {med['name']} | Dosage: {med['dosage']}")
        
        if result['instructions']:
            print(f"\n📋 Instructions:")
            for inst in result['instructions']:
                print(f"   - {inst}")
        
        print(f"\n📝 Full Extracted Text:")
        print("-"*40)
        print(result['full_text'][:500])
    else:
        print(f"❌ Error: {result.get('error')}")