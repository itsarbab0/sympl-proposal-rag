import psycopg

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
        cur.execute('SELECT proposal_code FROM proposal_documents ORDER BY proposal_code')
        proposals = [r[0] for r in cur.fetchall()]

print(f'proposal_documents = {doc_count}')
print(f'proposal_chunks = {chunk_count}')
print(f'dataset_imports = {import_count}')
print(f'sympl_reference_blocks = {ref_count}')
print(f'sympl_style_rules = {style_count}')
print(f'imported proposals = {proposals}')
