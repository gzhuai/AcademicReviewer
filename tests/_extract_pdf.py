from PyPDF2 import PdfReader
import sys
sys.stdout.reconfigure(encoding='utf-8')

reader = PdfReader(r'C:\Users\JY\Downloads\写作讲座内容建议+素材.pdf')

for i in [2,3,4,5,6,7,9,11,12,13,14,16,17,18,19,21,22]:
    text = reader.pages[i-1].extract_text() or ''
    print(f'\n========== PAGE {i} ==========')
    print(text[:1200])
