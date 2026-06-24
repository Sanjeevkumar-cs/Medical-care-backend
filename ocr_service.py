# backend/ocr_service.py - Using OCR.space (Working!)
import requests
import re
from typing import Dict, List
import os

# OCR.space API Configuration
OCR_API_KEY = os.environ.get("OCR_SPACE_API_KEY", "helloworld")  # "helloworld" works for testing
OCR_API_URL = "https://api.ocr.space/parse/image"


def extract_text_from_image(image_path: str) -> str:
    """Extract text from prescription image using OCR.space API"""
    try:
        with open(image_path, 'rb') as f:
            response = requests.post(
                OCR_API_URL,
                files={'file': f},
                data={
                    'apikey': OCR_API_KEY,
                    'ocrengine': 3,  # Engine 3 = handwriting recognition
                    'language': 'eng'
                },
                timeout=30
            )
        
        result = response.json()
        
        if result.get('IsErroredOnProcessing'):
            print(f"OCR Error: {result.get('ErrorMessage')}")
            return ""
        
        if result.get('ParsedResults'):
            extracted_text = result['ParsedResults'][0]['ParsedText']
            return extracted_text.strip()
        
        return ""
        
    except Exception as e:
        print(f"OCR API Error: {e}")
        return ""


def parse_prescription_text(text: str) -> Dict:
    """Parse extracted text to identify medicines, dosages, and instructions"""
    medicines = []
    instructions = []
    
    medicine_patterns = [
        r'([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(\d+(?:\.\d+)?)\s*(mg|g|ml|tab|cap|tablet|capsule)',
        r'(Tab|Cap|Inj|Syrup)\.?\s*([A-Za-z]+)\s*(\d+(?:\.\d+)?)?\s*(mg|mcg|ml)?',
        r'([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(\d+(?:\.\d+)?)\s*(?:mg|g|ml)',
    ]
    
    instruction_keywords = [
        'take', 'with', 'before', 'after', 'meal', 'food', 'water',
        'empty stomach', 'bedtime', 'morning', 'evening', 'daily',
        'refrigerate', 'shake well', 'dissolve', 'times'
    ]
    
    lines = text.split('\n')
    
    # Extract medicines
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
            
        for pattern in medicine_patterns:
            matches = re.findall(pattern, line, re.IGNORECASE)
            for match in matches:
                if len(match) >= 2:
                    medicine_name = match[0] if len(match) > 0 else match[1] if len(match) > 1 else line
                    medicine_name = ' '.join(medicine_name.split()[:3])
                    
                    dosage = ""
                    if len(match) >= 2:
                        dosage_match = re.search(r'(\d+(?:\.\d+)?)\s*(mg|g|ml|tab|cap)', line, re.IGNORECASE)
                        if dosage_match:
                            dosage = f"{dosage_match.group(1)} {dosage_match.group(2)}"
                    
                    medicines.append({
                        'name': medicine_name.title(),
                        'dosage': dosage,
                        'raw_text': line[:100]
                    })
    
    # Remove duplicates
    unique_medicines = []
    seen_names = set()
    for med in medicines:
        name_lower = med['name'].lower()
        if name_lower not in seen_names and len(name_lower) > 2:
            seen_names.add(name_lower)
            unique_medicines.append(med)
    
    # Extract instructions
    for line in lines:
        line_lower = line.lower()
        for keyword in instruction_keywords:
            if keyword in line_lower:
                is_medicine = any(med['name'].lower() in line_lower for med in unique_medicines)
                if not is_medicine and len(line) > 10 and len(line) < 200:
                    instructions.append(line.strip())
                    break
    
    return {
        'medicines': unique_medicines[:15],
        'instructions': instructions[:5],
        'full_text': text[:2000]
    }


def extract_medicines_from_prescription(image_path: str) -> Dict:
    """Main function: Extract and parse prescription"""
    print(f"📄 Processing prescription: {image_path}")
    
    extracted_text = extract_text_from_image(image_path)
    
    if not extracted_text:
        return {
            'success': False,
            'error': 'Could not extract text from the prescription. Please ensure the image is clear and well-lit.',
            'medicines': [],
            'instructions': [],
            'full_text': ''
        }
    
    print(f"📝 Extracted text length: {len(extracted_text)} characters")
    
    parsed_data = parse_prescription_text(extracted_text)
    
    print(f"💊 Found {len(parsed_data['medicines'])} medicines")
    
    return {
        'success': True,
        'medicines': parsed_data['medicines'],
        'instructions': parsed_data['instructions'],
        'full_text': parsed_data['full_text']
    }