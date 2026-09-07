import json
import re

def run_checks():
    with open('data/normalized/tact_2026.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    proposal = data['proposal']
    chunks = data['chunks']

    print("=== CHECK 1: IDENTITY & PROPOSAL METADATA ===")
    assert proposal['proposal_code'] == 'TACT_2026'
    assert proposal['organization_type'] == 'charity'
    assert proposal['sector'] == 'social_services'
    assert proposal['engagement_type'] == 'ongoing_plus_transformation'
    assert proposal['proposal_complexity'] == 'comprehensive'
    assert proposal['proposal_date'] is None
    assert proposal['metadata']['proposal_month'] == '2026-05'
    assert proposal['metadata']['source_page_count'] == 9
    assert proposal['metadata']['curation_status'] == 'approved_for_import'
    print("PASS: Identity & Metadata")

    print("=== CHECK 2: ARCHITECTURE ===")
    assert len(chunks) == 14
    expected_keys = [
        'TACT_2026_CONTEXT_OBJECTIVES',
        'TACT_2026_BOOKKEEPING',
        'TACT_2026_PAYROLL',
        'TACT_2026_FINANCIAL_REPORTING',
        'TACT_2026_COMPLIANCE',
        'TACT_2026_TRANSFORMATION_AP_PLOOTO',
        'TACT_2026_TRANSFORMATION_PAYROLL_MIGRATION',
        'TACT_2026_TRANSFORMATION_AR_AUTOMATION',
        'TACT_2026_AUDIT_SUPPORT',
        'TACT_2026_MONTHLY_FEES',
        'TACT_2026_TRANSFORMATION_FEES',
        'TACT_2026_AUDIT_FEES',
        'TACT_2026_EXCLUSIONS',
        'TACT_2026_WHY_US'
    ]
    for i, c in enumerate(chunks):
        assert c['section_order'] == i + 1, f"order mismatch at {i}: {c['section_order']}"
        assert c['chunk_key'] == expected_keys[i], f"key mismatch at {i}: {c['chunk_key']} vs {expected_keys[i]}"
    print("PASS: 14 Chunks & Keys")

    retrieval_enabled = [c for c in chunks if c['retrieval_enabled']]
    retrieval_disabled = [c for c in chunks if not c['retrieval_enabled']]
    pricing_chunks = [c for c in chunks if c['pricing_content']]
    boilerplate_chunks = [c for c in chunks if c['boilerplate_content']]

    assert len(retrieval_enabled) == 9
    assert len(retrieval_disabled) == 5
    assert len(pricing_chunks) == 3
    assert len(boilerplate_chunks) == 2
    print("PASS: Chunk Counts (9 ret-enabled, 5 ret-disabled, 3 pricing, 2 boilerplate)")

    # Check 1: Context Objectives
    c1 = chunks[0]
    assert 'financial management' in c1['retrieval_text']
    assert 'financial_management' not in c1['service_modules']
    assert 'annual_audit_support' not in c1['special_requirements']
    assert 'year_end_audit_support' in c1['special_requirements']
    assert 'Part C (annual' not in c1['retrieval_text']
    assert 'Part C: annual' not in c1['retrieval_text']
    assert 'Part C (year-end and audit support)' in c1['retrieval_text']
    print("PASS: Context Objectives")

    # Check 2: Bookkeeping
    c2 = chunks[1]
    assert 'five_program_class_expense_coding' not in c2['special_requirements']
    assert 'program_class_expense_coding' in c2['special_requirements']
    assert 'five program classes' not in c2['retrieval_text']
    assert 'proper GL coding by program class' in c2['retrieval_text']
    assert 'payroll journal entries' not in c2['retrieval_text']
    assert 'reconcile payroll entries' in c2['retrieval_text']
    assert 'manage twice-monthly payment runs with the Executive Director' in c2['retrieval_text']
    print("PASS: Bookkeeping")

    # Check 3: Payroll
    c3 = chunks[2]
    for b in ['medical_deduction', 'dental_deduction', 'ltd_deduction', 'ad_and_d_deduction']:
        assert b not in c3['special_requirements']
    assert 'benefits_deductions' in c3['special_requirements']
    assert 'primarily full-time' not in c3['retrieval_text']
    assert '19 employees across full-time and part-time staff' in c3['retrieval_text']
    assert 'calculate accurate CPP' not in c3['retrieval_text']
    assert 'ensure accurate CPP, EI, and tax source deductions each cycle' in c3['retrieval_text']
    assert 'qbo_payroll_journal_reconciliation' not in c3['special_requirements']
    assert 'payroll_reconciliation_to_qbo' in c3['special_requirements']
    assert 'payroll audit documentation' not in c3['retrieval_text']
    assert 'complete payroll records for audit purposes' in c3['retrieval_text']
    print("PASS: Payroll")

    # Check 4: Reporting
    c4 = chunks[3]
    assert '3. FINANCIAL REPORTING & COMPLIANCE' not in c4['raw_text']
    assert 'full compliance management throughout the year' not in c4['raw_text']
    assert 'c.raw_text starts with Monthly & Board Reporting:'
    assert c4['raw_text'].strip().startswith('Monthly & Board Reporting:')
    assert 'analysis with narrative commentary' not in c4['retrieval_text']
    assert 'budget vs. actuals with commentary' in c4['retrieval_text']
    assert 'AGM) financial statement package' not in c4['retrieval_text']
    assert 'AGM) financial package' in c4['retrieval_text']
    assert 'and submitted by the Executive Director' not in c4['retrieval_text']
    assert 'submission compiled by the Executive Director' in c4['retrieval_text']
    print("PASS: Reporting")

    # Check 5: Compliance
    c5 = chunks[4]
    assert c5['chunk_key'] == 'TACT_2026_COMPLIANCE'
    assert 'year_end' not in c5['service_modules']
    assert c5['service_modules'] == ['compliance', 'audit']
    assert 'external_auditor_liaison' not in c5['special_requirements']
    assert 'auditor_liaison' in c5['special_requirements']
    assert 'prepare and file HST returns' not in c5['retrieval_text']
    assert 'file HST returns' in c5['retrieval_text']
    assert 'required financial schedules and inputs' not in c5['retrieval_text']
    assert 'coordinate and provide financial inputs' in c5['retrieval_text']
    assert 'external auditor' not in c5['retrieval_text']
    assert 'typically filed by the auditor' in c5['retrieval_text']
    assert "Sympl's scope in this section is auditor liaison and compliance support; the proposal does not present Sympl as the auditor." in c5['retrieval_text']
    print("PASS: Compliance")

    # Check 6: Plooto AP Transformation
    c6 = chunks[5]
    assert 'training' not in c6['service_modules']
    assert 'process_documentation' not in c6['service_modules']
    assert 'onboarding' in c6['service_modules']
    assert c6['service_modules'] == ['digital_transformation', 'systems_implementation', 'accounts_payable', 'onboarding']
    assert 'Microsoft OneDrive' not in c6['retrieval_text']
    assert 'direct integration' not in c6['retrieval_text']
    assert 'structured approval workflows' not in c6['retrieval_text']
    assert 'one-click digital approval' not in c6['retrieval_text']
    assert 'legacy manual OneDrive' not in c6['retrieval_text']
    assert 'centralized Plooto expense submission form' not in c6['retrieval_text']
    assert 'active operational support' not in c6['retrieval_text']
    assert 'first two live payment cycles' not in c6['retrieval_text']
    assert 'Setup and integration of Plooto with QuickBooks Online' in c6['retrieval_text']
    assert 'one-click approval (no direct bank access required)' in c6['retrieval_text']
    assert 'support through the first 2 payment cycles' in c6['retrieval_text']
    print("PASS: Plooto AP Transformation")

    # Check 7: Payroll Migration
    c7 = chunks[6]
    assert 'employee master records' not in c7['retrieval_text']
    assert 'employee records' in c7['retrieval_text']
    assert 'deduction profiles' not in c7['retrieval_text']
    assert 'deductions' in c7['retrieval_text']
    assert 'specialized benefits deductions' not in c7['retrieval_text']
    assert 'automated general ledger integration' not in c7['retrieval_text']
    assert 'direct integration between QBO Payroll and ledger' in c7['retrieval_text']
    assert 'validate calculation accuracy' not in c7['retrieval_text']
    assert 'validate accuracy' in c7['retrieval_text']
    assert 'prior to final cutover' not in c7['retrieval_text']
    assert 'before cutoff' in c7['retrieval_text']
    assert 'Staff training and documentation' in c7['retrieval_text']
    print("PASS: Payroll Migration")

    # Check 8: AR Automation
    c8 = chunks[7]
    assert 'five service programs' not in c8['retrieval_text']
    assert 'each service program' in c8['retrieval_text']
    assert 'feasible software tools' not in c8['retrieval_text']
    assert 'feasible tools' in c8['retrieval_text']
    assert 'automated recurring monthly invoicing' not in c8['retrieval_text']
    assert 'Set up recurring monthly invoices where applicable' in c8['retrieval_text']
    assert 'overdue payment reminder' not in c8['retrieval_text']
    assert 'automated invoice and payment reminder emails' in c8['retrieval_text']
    assert 'documented accounts receivable follow-up' not in c8['retrieval_text']
    assert 'Establish a clear AR follow-up workflow for outstanding balances' in c8['retrieval_text']
    assert 'where families consent' in c8['retrieval_text']
    print("PASS: AR Automation")

    # Check 9: Audit Support
    c9 = chunks[8]
    assert 'labeled an annual engagement' in c9['retrieval_text']
    assert 'standalone one-time engagement' in c9['retrieval_text']
    assert '2 business days' not in c9['retrieval_text']
    assert '2 days' in c9['retrieval_text']
    assert 'external auditor' not in c9['retrieval_text']
    assert 'the independent audit remains external' not in c9['retrieval_text']
    assert "Sympl is positioned as year-end review, audit-preparation, and auditor-liaison support; the proposal does not present Sympl as performing the audit." in c9['retrieval_text']
    print("PASS: Audit Support")

    # Check 10: Software Exclusion
    c13 = chunks[12]
    assert 'billed separately' not in c13['retrieval_text']
    assert 'paid directly' not in c13['retrieval_text']
    assert 'Software subscription fees, including QuickBooks Online and Plooto, are not included.' in c13['retrieval_text']
    print("PASS: Exclusion")

    # Check 11: Pricing isolation
    bad_price_patterns = [
        r'\$1,250', r'\$1250', r'\$1,000', r'\$1000', r'\$2,250', r'\$2250',
        r'\$2,000', r'\$2000', r'\$3,500', r'\$3500', r'\$1,800', r'\$1800',
        r'\$7,300', r'\$7300'
    ]
    contam_rows = 0
    for c in retrieval_enabled:
        text_to_check = f"{c['raw_text']} {c['cleaned_text']} {c['retrieval_text']}"
        for pat in bad_price_patterns:
            if re.search(pat, text_to_check):
                print(f"Price violation in {c['chunk_key']}: {pat}")
                contam_rows += 1
    assert contam_rows == 0, f"Found {contam_rows} price contamination rows!"
    print(f"PASS: Commercial Isolation (0 contaminated rows across 9 retrieval chunks)")

    # Check 12: Commercial wording in retrieval chunks
    bad_wording_patterns = [
        r'PROPOSED FEES', r'historical fee', r'retainer fee', r'priced at',
        r'TOTAL \$', r'service fee'
    ]
    wording_contam = 0
    for c in retrieval_enabled:
        text_to_check = f"{c['raw_text']} {c['cleaned_text']} {c['retrieval_text']}"
        for pat in bad_wording_patterns:
            if re.search(pat, text_to_check, re.IGNORECASE):
                print(f"Commercial wording violation in {c['chunk_key']}: {pat}")
                wording_contam += 1
    assert wording_contam == 0, f"Found {wording_contam} commercial wording rows!"
    print(f"PASS: Commercial Wording Scan (0 contaminated rows)")

    # Client facts allowed
    assert '$1.4M' in c1['retrieval_text']
    assert 'fee-for-service' in c1['retrieval_text']
    print("PASS: Client business facts preserved")

    print("\nALL 12 DETAILED AUDITS PASSED PERFECTLY!")

if __name__ == '__main__':
    run_checks()
