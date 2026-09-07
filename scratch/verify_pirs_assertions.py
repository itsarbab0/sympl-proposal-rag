import json
import os
import re
import psycopg

def test_pirs():
    json_path = 'data/normalized/pirs_2025.json'
    assert os.path.exists(json_path), f"File {json_path} does not exist!"

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    p = data['proposal']
    chunks = data['chunks']

    print("=== CHECK 1: PROPOSAL IDENTITY ===")
    assert p['proposal_code'] == 'PIRS_2025'
    assert p['client_name'] == 'Pacific Immigrant Resources Society'
    assert p['proposal_title'] == 'Accounting Services Proposal'
    assert p['proposal_date'] == '2025-06-21'
    assert p['source_filename'] == 'PIRS x Sympl - Bookkeeping Proposal - July 2025.pdf'
    assert p['metadata']['proposal_month'] == '2025-06'
    assert p['organization_type'] == 'unknown'
    assert p['sector'] == 'unknown'
    assert p['engagement_type'] == 'ongoing_plus_transformation'
    assert p['proposal_complexity'] == 'comprehensive'
    assert p['core_bookkeeping'] is True
    assert p['metadata']['source_page_count'] == 7
    assert p['metadata']['curation_status'] == 'draft_review'
    assert p['metadata']['source_temporal_inconsistency'] == 'page_2_describes_previous_fiscal_year_ending_2025_07_31'
    assert len(p['raw_text']) > 0
    assert len(p['cleaned_text']) > 0
    print("PASS: Proposal Identity & Metadata")

    print("=== CHECK 2: CHUNK ARCHITECTURE & SAFETY ===")
    assert len(chunks) == 7
    expected_keys = [
        'PIRS_2025_AUDIT_PREPARATION',
        'PIRS_2025_BOOKKEEPING_OVERSIGHT_FINANCIAL_MANAGEMENT',
        'PIRS_2025_PAYROLL',
        'PIRS_2025_TRANSFORMATION_STRATEGY',
        'PIRS_2025_TRANSFORMATION_IMPLEMENTATION',
        'PIRS_2025_TRAINING_CHANGE_MANAGEMENT',
        'PIRS_2025_WHY_US'
    ]
    for i, c in enumerate(chunks):
        assert c['section_order'] == i + 1
        assert c['chunk_key'] == expected_keys[i]

    ret_en = [c for c in chunks if c['retrieval_enabled']]
    ret_dis = [c for c in chunks if not c['retrieval_enabled']]
    pricing = [c for c in chunks if c['pricing_content']]
    boiler = [c for c in chunks if c['boilerplate_content']]

    assert len(ret_en) == 6
    assert len(ret_dis) == 1
    assert len(pricing) == 0
    assert len(boiler) == 1
    print("PASS: Chunk counts: 7 total, 6 retrieval-enabled, 1 retrieval-disabled, 0 pricing, 1 boilerplate")

    print("=== CHECK 3: CHUNK-SPECIFIC FIDELITY ===")
    c1 = chunks[0]
    assert c1['section_type'] == 'audit'
    assert c1['service_modules'] == ['audit', 'year_end', 'reconciliations', 'transition']
    assert c1['accounting_systems'] == []
    assert c1['payroll_systems'] == []
    assert c1['cadence'] == ['one_time']
    assert 'external auditor' in c1['retrieval_text']
    assert 'outgoing Finance Director' in c1['retrieval_text']

    c2 = chunks[1]
    assert c2['section_type'] == 'financial_management'
    assert c2['accounting_systems'] == []
    assert c2['payroll_systems'] == []
    assert 'QuickBooks' not in str(c2['accounting_systems'])
    assert 'QuickBooks' not in c2['raw_text']
    assert 'QuickBooks' not in c2['cleaned_text']
    assert 'QuickBooks' not in c2['retrieval_text']
    assert c2['cadence'] == ['ongoing', 'monthly']
    assert 'internal junior bookkeeper' in c2['retrieval_text']
    assert 'takes full ownership' not in c2['retrieval_text']

    c3 = chunks[2]
    assert c3['section_type'] == 'payroll'
    assert c3['service_modules'] == ['payroll', 'compliance']
    assert c3['accounting_systems'] == ['QuickBooks']
    assert c3['payroll_systems'] == ['PayWorks', 'QuickBooks Online Payroll']
    assert c3['metadata']['system_state']['current'] == ['PayWorks']
    assert c3['metadata']['system_state']['proposed_or_under_evaluation'] == ['QuickBooks Online Payroll']
    assert 'We do not manage HR functions' in c3['cleaned_text']
    assert 'We do not manage HR functions' in c3['raw_text']

    c4 = chunks[3]
    assert c4['section_type'] == 'digital_transformation'
    assert c4['accounting_systems'] == []
    assert c4['payroll_systems'] == []
    assert 'QuickBooks' not in str(c4)
    assert 'PayWorks' not in str(c4)

    c5 = chunks[4]
    assert c5['section_type'] == 'digital_transformation'
    assert c5['accounting_systems'] == []
    assert c5['payroll_systems'] == []
    assert 'QuickBooks' not in str(c5)
    assert 'PayWorks' not in str(c5)
    assert 'Set up integrated cash flow projection tools to accounting data' in c5['raw_text']

    c6 = chunks[5]
    assert c6['section_type'] == 'training'
    assert c6['service_modules'] == ['training', 'process_documentation']
    assert c6['accounting_systems'] == []
    assert c6['payroll_systems'] == []

    c7 = chunks[6]
    assert c7['section_type'] == 'why_us'
    assert c7['retrieval_enabled'] is False
    assert c7['boilerplate_content'] is True

    print("PASS: Chunk-specific fidelity verified")

    print("=== CHECK 4: COMMERCIAL ISOLATION ===")
    price_patterns = [r'\$', r'fee', r'retainer', r'priced at', r'cost', r'TOTAL \$']
    for c in ret_en:
        for pat in [r'\$', r'priced at', r'TOTAL \$']:
            assert not re.search(pat, c['raw_text']), f"Found {pat} in raw of {c['chunk_key']}"
            assert not re.search(pat, c['cleaned_text']), f"Found {pat} in clean of {c['chunk_key']}"
            assert not re.search(pat, c['retrieval_text']), f"Found {pat} in ret of {c['chunk_key']}"
    print("PASS: Zero historical pricing in retrieval chunks")

    print("=== CHECK 5: DATABASE UNTOUCHED ===")
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

            print(f"DB docs={doc_count}, chunks={chunk_count}, imports={import_count}, refs={ref_count}, styles={style_count}")
            assert doc_count == 6
            assert chunk_count == 64
            assert import_count == 6
            assert ref_count == 0
            assert style_count == 0

    print("PASS: Railway database remains completely untouched!")
    print("\nALL ASSERTIONS PASSED!")

if __name__ == '__main__':
    test_pirs()
