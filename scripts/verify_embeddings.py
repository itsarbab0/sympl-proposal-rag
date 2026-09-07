import psycopg
from pathlib import Path

env = {}
for p in [Path('d:/Sympl/.env'), Path('.env'), Path('../.env')]:
    if p.exists():
        with open(p, 'r', encoding='utf-8') as f:
            for l in f:
                l = l.strip()
                if l and not l.startswith('#') and '=' in l:
                    k, v = l.split('=', 1)
                    env[k.strip()] = v.strip().strip("'\"")

conn = psycopg.connect(env['DATABASE_URL'])
with conn.cursor() as cur:
    cur.execute("SELECT count(*) FROM proposal_chunks WHERE embedding IS NOT NULL;")
    embedded_count = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM proposal_chunks WHERE retrieval_enabled = false AND embedding IS NOT NULL;")
    unsafe_embedded = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM proposal_chunks WHERE retrieval_enabled = true;")
    retrieval_enabled_count = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM proposal_documents;")
    docs_count = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM proposal_chunks;")
    chunks_count = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM dataset_imports;")
    imports_count = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM sympl_style_rules;")
    rules_count = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM sympl_reference_blocks;")
    refs_count = cur.fetchone()[0]

    # Sample vector check
    cur.execute("SELECT chunk_key, vector_dims(embedding), embedded_at FROM proposal_chunks WHERE embedding IS NOT NULL ORDER BY id LIMIT 3;")
    sample_rows = cur.fetchall()

    # Dimension consistency check across all 47
    cur.execute("SELECT DISTINCT vector_dims(embedding) FROM proposal_chunks WHERE embedding IS NOT NULL;")
    distinct_dims = [r[0] for r in cur.fetchall()]

print("============================================================")
print("DATABASE EMBEDDING VERIFICATION")
print("============================================================")
print(f"Total proposal_documents:            {docs_count} (expected: 7)")
print(f"Total proposal_chunks:               {chunks_count} (expected: 71)")
print(f"Total dataset_imports:               {imports_count} (expected: 7)")
print(f"Total sympl_style_rules:             {rules_count} (expected: 21)")
print(f"Total sympl_reference_blocks:        {refs_count} (expected: 13)")
print("------------------------------------------------------------")
print(f"Retrieval enabled chunks:            {retrieval_enabled_count} (expected: 47)")
print(f"Chunks with embedding IS NOT NULL:   {embedded_count} (expected: 47)")
print(f"Unsafe non-retrieval with embedding: {unsafe_embedded} (expected: 0)")
print(f"Distinct embedding dimensions in DB: {distinct_dims} (expected: [1024])")
print("------------------------------------------------------------")
print("Sample embedded rows:")
for r in sample_rows:
    print(f"  - Key: {r[0]}, Dims: {r[1]}, Embedded At: {r[2]}")
print("============================================================")

assert docs_count == 7, "Docs count mismatch"
assert chunks_count == 71, "Chunks count mismatch"
assert imports_count == 7, "Imports count mismatch"
assert rules_count == 21, "Rules count mismatch"
assert refs_count == 13, "Refs count mismatch"
assert retrieval_enabled_count == 47, "Retrieval enabled count mismatch"
assert embedded_count == 47, "Embedded count mismatch"
assert unsafe_embedded == 0, "Unsafe embedded must be 0"
assert distinct_dims == [1024], "Dimension must be [1024]"
print("ALL DATABASE ASSERTIONS PASSED!")
conn.close()
