import os
import json
import psycopg

def step1_to_5():
    norm_dir = 'data/normalized'
    json_files = sorted([f for f in os.listdir(norm_dir) if f.endswith('.json')])
    expected_files = ['cahoots_2026.json', 'careof_2025.json', 'goodfoot_2026.json', 'rpff_2025.json', 'tact_2026.json', 'ypt_2026.json']
    print("STEP 1: Checking normalized files...")
    print("Files found:", json_files)
    assert json_files == expected_files, f"File mismatch: {json_files} != {expected_files}"
    print("PASS: Step 1 files match exactly.")

    print("\nSTEP 2: Verifying TACT approval...")
    with open(os.path.join(norm_dir, 'tact_2026.json'), 'r', encoding='utf-8') as f:
        tact = json.load(f)
    p = tact['proposal']
    chunks = tact['chunks']
    assert p['proposal_code'] == 'TACT_2026'
    assert p['organization_type'] == 'charity'
    assert p['sector'] == 'social_services'
    assert p['engagement_type'] == 'ongoing_plus_transformation'
    assert p['proposal_complexity'] == 'comprehensive'
    assert p['proposal_date'] is None
    assert p['metadata']['proposal_month'] == '2026-05'
    assert p['metadata']['source_page_count'] == 9
    assert p['metadata']['curation_status'] == 'approved_for_import'
    assert len(chunks) == 14
    for i, c in enumerate(chunks):
        assert c['section_order'] == i + 1
    assert chunks[4]['chunk_key'] == 'TACT_2026_COMPLIANCE'

    ret_en = [c for c in chunks if c['retrieval_enabled']]
    ret_dis = [c for c in chunks if not c['retrieval_enabled']]
    pricing = [c for c in chunks if c['pricing_content']]
    boilerplate = [c for c in chunks if c['boilerplate_content']]
    assert len(ret_en) == 9
    assert len(ret_dis) == 5
    assert len(pricing) == 3
    assert len(boilerplate) == 2
    print("PASS: Step 2 TACT approval verified.")

    print("\nSTEP 4 & 5: Pre-import DB check & Snapshot...")
    url = None
    with open('D:/Sympl/.env', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('DATABASE_URL='):
                url = line.strip().split('=', 1)[1].strip('"\'')

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT count(*) FROM proposal_documents')
            doc_count = cur.fetchone()[0]
            cur.execute('SELECT count(*) FROM proposal_chunks')
            chunk_count = cur.fetchone()[0]
            cur.execute('SELECT count(*) FROM dataset_imports')
            import_count = cur.fetchone()[0]
            cur.execute('SELECT count(*) FROM sympl_reference_blocks')
            ref_count = cur.fetchone()[0]
            cur.execute('SELECT count(*) FROM sympl_style_rules')
            style_count = cur.fetchone()[0]
            
            print(f"proposal_documents = {doc_count}")
            print(f"proposal_chunks = {chunk_count}")
            print(f"dataset_imports = {import_count}")
            print(f"sympl_reference_blocks = {ref_count}")
            print(f"sympl_style_rules = {style_count}")

            assert doc_count == 5
            assert chunk_count == 50
            assert import_count == 5
            assert ref_count == 0
            assert style_count == 0

            cur.execute('SELECT proposal_code, count(*) FROM proposal_documents GROUP BY proposal_code ORDER BY proposal_code')
            doc_codes = dict(cur.fetchall())
            print("Current document codes:", doc_codes)
            assert 'TACT_2026' not in doc_codes
            for code in ['CAREOF_2025', 'CAHOOTS_2026', 'RPFF_2025', 'YPT_2026', 'GOODFOOT_2026']:
                assert doc_codes.get(code) == 1

            # Snapshot existing data
            cur.execute('SELECT id, proposal_code, created_at, updated_at FROM proposal_documents ORDER BY proposal_code')
            existing_docs = {}
            for row in cur.fetchall():
                existing_docs[row[1]] = {
                    'id': str(row[0]),
                    'created_at': str(row[2]),
                    'updated_at': str(row[3])
                }

            cur.execute('''
                SELECT pc.id, pc.chunk_key, pd.proposal_code, pc.created_at, pc.updated_at
                FROM proposal_chunks pc
                JOIN proposal_documents pd ON pc.proposal_id = pd.id
                ORDER BY pc.chunk_key
            ''')
            existing_chunks = {}
            for row in cur.fetchall():
                existing_chunks[row[1]] = {
                    'id': str(row[0]),
                    'proposal_code': row[2],
                    'created_at': str(row[3]),
                    'updated_at': str(row[4])
                }

            print(f"Snapshotted {len(existing_docs)} docs and {len(existing_chunks)} chunks.")
            with open('scratch/preimport_tact_snapshot.json', 'w', encoding='utf-8') as sf:
                json.dump({'docs': existing_docs, 'chunks': existing_chunks}, sf, indent=2)

    print("PASS: Pre-import DB checks & Snapshot saved.")

if __name__ == '__main__':
    step1_to_5()
