import pypdf
import os

pdf_path = r'D:\Sympl\Proposals\PIRS x Sympl - Bookkeeping Proposal - July 2025.pdf'

reader = pypdf.PdfReader(pdf_path)
print(f"Total pages: {len(reader.pages)}")

out_path = 'scratch/pirs_extracted.txt'
with open(out_path, 'w', encoding='utf-8') as f:
    for i, page in enumerate(reader.pages):
        f.write(f"\n{'='*30} PAGE {i+1} {'='*30}\n")
        text = page.extract_text()
        f.write(text if text else "[EMPTY PAGE]")
        f.write("\n")

print(f"Extracted full text to {out_path}")
