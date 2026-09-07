import json
import glob

for f in sorted(glob.glob('data/normalized/*.json')):
    with open(f, 'r', encoding='utf-8') as fp:
        d = json.load(fp)
    p = d['proposal']
    print(f"{p['proposal_code']}: sector={p['sector']}, org={p['organization_type']}, eng={p['engagement_type']}, comp={p['proposal_complexity']}")
