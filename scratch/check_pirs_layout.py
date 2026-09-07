import pypdf

reader = pypdf.PdfReader(r'D:\Sympl\Proposals\PIRS x Sympl - Bookkeeping Proposal - July 2025.pdf')

for i, page in enumerate(reader.pages):
    print(f"=== PAGE {i+1} ===")
    def visitor(text, cm, tm, font_dict, font_size):
        if text.strip():
            print(f"[{tm[4]:.1f}, {tm[5]:.1f}] (size {font_size:.1f}): {text.strip()}")
    page.extract_text(visitor_text=visitor)
