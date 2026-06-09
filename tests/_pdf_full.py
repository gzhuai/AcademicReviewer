import sys
from PyPDF2 import PdfReader
sys.stdout.reconfigure(encoding='utf-8')

reader = PdfReader(r'C:\Users\JY\Downloads\写作讲座内容建议+素材.pdf')

with open(r'C:\Users\JY\Downloads\写作讲座_pdf_text.txt', 'w', encoding='utf-8') as out:
    for i in range(len(reader.pages)):
        text = reader.pages[i].extract_text() or ''
        out.write(f'\n========== PAGE {i+1} ==========\n')
        out.write(text)
        out.write('\n')

print("Done. Saved to 写作讲座_pdf_text.txt")
