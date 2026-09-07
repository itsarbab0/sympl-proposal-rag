import json
import glob

for f in sorted(glob.glob('data/normalized/*.json')):
    with open(f, 'r', encoding='utf-8') as fp:
        d = json.load(fp)
    c1 = d['chunks'][0]
    print(f"{d['proposal']['proposal_code']}: Chunk 1 key={c1['chunk_key']}, type={c1['section_type']}, pages={c1['metadata'].get('source_pages')}")
