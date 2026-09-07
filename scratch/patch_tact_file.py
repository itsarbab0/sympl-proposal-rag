import json

def patch_tact():
    filepath = 'data/normalized/tact_2026.json'
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chunks = data['chunks']

    # Patch 1: Chunk 1 TACT_2026_CONTEXT_OBJECTIVES
    c1 = chunks[0]
    assert c1['chunk_key'] == 'TACT_2026_CONTEXT_OBJECTIVES'
    c1['special_requirements'] = [
        'year_end_audit_support' if x == 'annual_audit_support' else x
        for x in c1['special_requirements']
    ]
    c1['retrieval_text'] = (
        "Section: Context & Objectives\n"
        "Service modules: bookkeeping, payroll, financial reporting, digital transformation, audit\n"
        "Accounting systems: QuickBooks Online\n"
        "Payroll systems: ADP\n"
        "Cadence: monthly, bi-weekly\n"
        "Special requirements: approximately $1.4M operating budget, April–March fiscal year, recent charitable status, fee-for-service revenue model, grant revenue, donation revenue, five program classes, 19 employees, maternity leave transition, three-part engagement structure, ongoing services, one-time process transformation, year-end audit support\n"
        "Content:\n"
        "Context & Objectives\n\n"
        "• Autism Centre of Toronto provides fee-based therapeutic services to children and families with autism (early intervention, applied behaviour analysis, speech, occupational therapy).\n"
        "• Annual operating budget is approximately $1.4M with an April–March fiscal year.\n"
        "• The organization recently achieved charitable status and is growing grant and donation revenue alongside its core fee income.\n"
        "• Revenue breakdown: approximately 80% fee-for-service, 15% grants, 5% donations.\n"
        "• Baseline systems: solid QuickBooks Online foundation with five service program classes (Early Intervention, Developmental Classroom, School Readiness, School Support, Home-Based Services); 19 employees paid bi-weekly via ADP; current on CRA filings.\n"
        "• Immediate engagement trigger: replace current bookkeeping and payroll function as the administrator prepares for maternity leave.\n"
        "• Engagement architecture: Part A (ongoing bookkeeping, payroll, financial management), Part B (one-time process and digital transformation to modernize key workflows), Part C (year-end and audit support)."
    )

    # Patch 2: Chunk 2 TACT_2026_BOOKKEEPING
    c2 = chunks[1]
    assert c2['chunk_key'] == 'TACT_2026_BOOKKEEPING'
    c2['special_requirements'] = [
        'program_class_expense_coding' if x == 'five_program_class_expense_coding' else x
        for x in c2['special_requirements']
    ]
    c2['retrieval_text'] = (
        "Section: Bookkeeping & Reconciliations\n"
        "Service modules: bookkeeping, reconciliations, accounts payable, accounts receivable\n"
        "Accounting systems: QuickBooks Online\n"
        "Cadence: monthly, twice-monthly (bi-monthly AP payment runs)\n"
        "Special requirements: monthly program fee invoicing, accounts receivable tracking, overdue account follow-up, incoming payment reconciliation, fee income recording, grant income recording, donation income recording, program class expense coding, restricted and unrestricted tracking, vendor invoice processing, employee reimbursements, twice-monthly payment runs with ED, bank reconciliations, credit card reconciliations, trial balance reconciliations, payroll entry reconciliation, QBO chart of accounts maintenance, budget vs actual tracking, annual budget entry support\n"
        "Content:\n"
        "Bookkeeping & Reconciliations\n\n"
        "• Invoicing & Accounts Receivable: Sympl generates and issues monthly fee invoices across service programs, tracks outstanding AR, conducts overdue account follow-up, records and reconciles incoming payments against invoices, and works toward automated delivery and collection.\n"
        "• Income & Expense Recording: Record fee payments, grants, and donations; allocate grant revenue across program classes; categorize all expenses with proper GL coding by program class; manage restricted versus unrestricted funds.\n"
        "• Accounts Payable: Process vendor invoices and employee reimbursements; manage twice-monthly payment runs with the Executive Director; maintain complete AP documentation in QuickBooks Online.\n"
        "• Reconciliations: Complete monthly bank, credit card, and trial balance reconciliations; reconcile payroll entries to QBO each pay cycle (ADP initially, and QBO Payroll post-migration).\n"
        "• QBO Maintenance: Maintain Chart of Accounts and class structures across service programs; configure budget vs. actuals tracking; support annual budget entry at the start of each fiscal year."
    )

    # Patch 3: Chunk 3 TACT_2026_PAYROLL
    c3 = chunks[2]
    assert c3['chunk_key'] == 'TACT_2026_PAYROLL'
    # Remove benefit types, replace journal with payroll_reconciliation_to_qbo
    remove_reqs = {'medical_deduction', 'dental_deduction', 'ltd_deduction', 'ad_and_d_deduction'}
    new_reqs = []
    for x in c3['special_requirements']:
        if x in remove_reqs:
            continue
        if x == 'qbo_payroll_journal_reconciliation':
            new_reqs.append('payroll_reconciliation_to_qbo')
        else:
            new_reqs.append(x)
    c3['special_requirements'] = new_reqs
    c3['retrieval_text'] = (
        "Section: Payroll Administration & Compliance\n"
        "Service modules: payroll, compliance\n"
        "Accounting systems: QuickBooks Online\n"
        "Payroll systems: ADP, QuickBooks Online Payroll\n"
        "Cadence: bi-weekly\n"
        "Special requirements: 19 employees, full-time and part-time payroll, employee updates, new hires, terminations, benefits deductions, CPP source deductions, EI source deductions, income tax source deductions, payroll remittances, ADP remittance oversight, payroll reconciliation to QBO, T4 preparation and filing, T4A preparation and filing, ROE issuance, complete payroll records for audit purposes, initial ADP period before QBO Payroll migration\n"
        "Content:\n"
        "Payroll Administration & Compliance\n\n"
        "• Manage bi-weekly payroll administration for 19 employees across full-time and part-time staff, initially operated within ADP for the first 1–2 months prior to QBO Payroll migration.\n"
        "• Payroll Processing: manage bi-weekly payroll cycles, employee updates, new hires, terminations, employee benefits deductions, and employee system records.\n"
        "• CRA Compliance & Remittances: ensure accurate CPP, EI, and tax source deductions each cycle; submit federal and provincial remittances on time; oversee ADP remittance processing and reconcile entries to QuickBooks Online.\n"
        "• Year-End Payroll Filings: prepare and file T4 slips for employees and T4A slips for contractors; issue Records of Employment (ROEs) as required; maintain complete payroll records for audit purposes."
    )

    # Patch 4: Chunk 4 TACT_2026_FINANCIAL_REPORTING
    c4 = chunks[3]
    assert c4['chunk_key'] == 'TACT_2026_FINANCIAL_REPORTING'
    c4['raw_text'] = (
        "Monthly & Board Reporting:\n"
        "Monthly financial statements: P&L (program-level), Balance Sheet,\n"
        "Cash Flow, AR/AP Aging\n"
        "Monthly budget vs. actuals for ED review\n"
        "Quarterly board reporting package: Balance Sheet, Statement of\n"
        "Operations, budget vs. actuals with commentary\n"
        "Annual General Meeting (AGM) financial package\n"
        "Help pull any financial inputs for bi-annual government grant\n"
        "report (submission will be compiled by ED)"
    )
    c4['cleaned_text'] = (
        "Monthly & Board Reporting:\n"
        "- Monthly financial statements: P&L (program-level), Balance Sheet, Cash Flow, AR/AP Aging\n"
        "- Monthly budget vs. actuals for ED review\n"
        "- Quarterly board reporting package: Balance Sheet, Statement of Operations, budget vs. actuals with commentary\n"
        "- Annual General Meeting (AGM) financial package\n"
        "- Help pull any financial inputs for bi-annual government grant report (submission will be compiled by ED)"
    )
    c4['retrieval_text'] = (
        "Section: Monthly & Board Reporting\n"
        "Service modules: financial reporting, funder reporting\n"
        "Cadence: monthly, quarterly, semi-annual (bi-annual), annual\n"
        "Special requirements: program-level profit and loss, balance sheet, cash flow statement, accounts receivable aging, accounts payable aging, monthly budget vs actual, executive director review, quarterly board reporting, board commentary, AGM financial package, government grant reporting inputs\n"
        "Content:\n"
        "Monthly & Board Reporting\n\n"
        "• Ongoing financial reporting packages for Executive Director and Board:\n"
        "  - Monthly financial statements: P&L (with program-level breakdowns), Balance Sheet, Cash Flow statement, and AR/AP aging reports.\n"
        "  - Monthly budget vs. actuals review with the Executive Director.\n"
        "  - Quarterly board reporting package: Balance Sheet, Statement of Operations, and budget vs. actuals with commentary.\n"
        "  - Annual General Meeting (AGM) financial package.\n"
        "• Grant Reporting: Help pull financial inputs for bi-annual government grant report (submission compiled by the Executive Director)."
    )

    # Patch 5: Chunk 5 Rename to TACT_2026_COMPLIANCE
    c5 = chunks[4]
    assert c5['chunk_key'] in ('TACT_2026_COMPLIANCE_YEAR_END', 'TACT_2026_COMPLIANCE')
    c5['chunk_key'] = 'TACT_2026_COMPLIANCE'
    c5['service_modules'] = ['compliance', 'audit']
    c5['special_requirements'] = [
        'auditor_liaison' if x == 'external_auditor_liaison' else x
        for x in c5['special_requirements']
    ]
    c5['retrieval_text'] = (
        "Section: Statutory Compliance & CRA Requirements\n"
        "Service modules: compliance, audit\n"
        "Cadence: ongoing statutory filings, annual audit coordination\n"
        "Special requirements: HST-exempt status confirmation, PSB rebate eligibility assessment, HST returns, PSB rebate claims, registered charity CRA compliance, auditor liaison, fiscal 2026–2027 audit coordination, T3010 financial inputs, T3010 auditor coordination\n"
        "Content:\n"
        "Statutory Compliance & CRA Requirements\n\n"
        "• HST & PSB Rebate: Confirm HST-exempt status and assess Public Service Bodies (PSB) rebate eligibility (reclaiming a portion of HST paid on purchases as a registered charity); file HST returns and manage PSB rebate claims once confirmed.\n"
        "• CRA & Charity Compliance: Ensure ongoing CRA compliance for registered charities throughout the year.\n"
        "• T3010 Registered Charity Information Return: coordinate and provide financial inputs (typically filed by the auditor).\n"
        "• Auditor Liaison: Liaise with the auditor for the yearly financial audit starting in fiscal 2026–2027.\n"
        "• Scope boundary: Sympl's scope in this section is auditor liaison and compliance support; the proposal does not present Sympl as the auditor."
    )

    # Patch 6: Chunk 6 TACT_2026_TRANSFORMATION_AP_PLOOTO
    c6 = chunks[5]
    assert c6['chunk_key'] == 'TACT_2026_TRANSFORMATION_AP_PLOOTO'
    c6['service_modules'] = ['digital_transformation', 'systems_implementation', 'accounts_payable', 'onboarding']
    c6['metadata']['operational_tools'] = ['OneDrive']
    c6['retrieval_text'] = (
        "Section: AP Automation via Plooto\n"
        "Service modules: digital transformation, systems implementation, accounts payable, onboarding\n"
        "Accounting systems: QuickBooks Online\n"
        "Workflow systems: Plooto\n"
        "Operational tools: OneDrive\n"
        "Cadence: one-time digital transformation project (part of 8–10 week transformation engagement)\n"
        "Special requirements: Plooto QBO integration, Executive Director one-click approval, no direct bank access required, payment workflow configuration, expense submission form, replace manual OneDrive expense tracking, support first two payment cycles, staff onboarding\n"
        "Content:\n"
        "Initiative 1: Accounts Payable Automation via Plooto\n\n"
        "• Setup and integration of Plooto with QuickBooks Online.\n"
        "• Configure approval workflows so all payables are routed to the Executive Director for one-click approval (no direct bank access required).\n"
        "• Set up bi-monthly AP payment runs aligned to bookkeeping cadence.\n"
        "• Replace current manual OneDrive-based expense reimbursement tracking with a Plooto expense submission form.\n"
        "• Staff onboarding and support through the first 2 payment cycles."
    )

    # Patch 7: Chunk 7 TACT_2026_TRANSFORMATION_PAYROLL_MIGRATION
    c7 = chunks[6]
    assert c7['chunk_key'] == 'TACT_2026_TRANSFORMATION_PAYROLL_MIGRATION'
    c7['retrieval_text'] = (
        "Section: Payroll Migration – ADP to QBO Payroll\n"
        "Service modules: digital transformation, systems implementation, payroll, training, process documentation\n"
        "Accounting systems: QuickBooks Online\n"
        "Payroll systems: ADP, QuickBooks Online Payroll\n"
        "Cadence: one-time digital transformation project (part of 8–10 week transformation engagement)\n"
        "Special requirements: 19 employee migration, ADP to QBO Payroll, YTD balance transfer, employee record transfer, benefit deduction transfer, medical benefits setup, dental benefits setup, LTD setup, AD&D setup, general ledger integration, one pay cycle parallel run, staff training, process documentation\n"
        "Content:\n"
        "Initiative 2: Payroll Migration – ADP to QBO Payroll\n\n"
        "• Migrate all 19 employees from ADP to QuickBooks Online Payroll.\n"
        "• Transfer YTD payroll balances, employee records, and deductions.\n"
        "• Set up benefits deductions: medical, dental, LTD, and AD&D in QBO.\n"
        "• Configure direct integration between QBO Payroll and ledger.\n"
        "• Parallel run for one pay cycle to validate accuracy before cutoff.\n"
        "• Staff training and documentation."
    )

    # Patch 8: Chunk 8 TACT_2026_TRANSFORMATION_AR_AUTOMATION
    c8 = chunks[7]
    assert c8['chunk_key'] == 'TACT_2026_TRANSFORMATION_AR_AUTOMATION'
    c8['retrieval_text'] = (
        "Section: Invoicing & AR Automation\n"
        "Service modules: digital transformation, systems implementation, accounts receivable, process documentation\n"
        "Workflow systems: Pre-Authorized Debit (PAD)\n"
        "Cadence: one-time digital transformation project (part of 8–10 week transformation engagement)\n"
        "Special requirements: standardized program invoice templates, recurring monthly invoices, pre-authorized debit where families consent, automated payment collection where consented, payment reminder emails, accounts receivable follow-up workflow, tool assessment\n"
        "Content:\n"
        "Initiative 3: Invoicing & AR Automation\n\n"
        "• Assess current invoicing setup and identify feasible tools.\n"
        "• Build standardized invoice templates for each service program.\n"
        "• Set up recurring monthly invoices where applicable.\n"
        "• Configure pre-authorized debit (PAD) or automated payment collection where families consent.\n"
        "• Set up automated invoice and payment reminder emails.\n"
        "• Establish a clear AR follow-up workflow for outstanding balances."
    )

    # Patch 9: Chunk 9 TACT_2026_AUDIT_SUPPORT
    c9 = chunks[8]
    assert c9['chunk_key'] == 'TACT_2026_AUDIT_SUPPORT'
    c9['retrieval_text'] = (
        "Section: Year-End Audit Support (Annual Engagement)\n"
        "Service modules: audit, year-end, reconciliations\n"
        "Accounting systems: QuickBooks Online\n"
        "Payroll systems: ADP\n"
        "Cadence: annual engagement (April–March fiscal year)\n"
        "Special requirements: full fiscal year book review, April–March review, year-end clean-up, adjusting entries, accrual review, revenue coding review, balance sheet validation, full-year ADP reconciliation, year-end financial statements, audit working papers, audit schedules, PBC list, Executive Director document coordination, auditor liaison, auditor query response within 2 days, auditor meeting attendance, post-audit adjusting entries\n"
        "Content:\n"
        "Part C – Year-End Audit Support\n\n"
        "• Part C is labeled an annual engagement; the 2025–2026 year-end scope is described as a standalone one-time engagement independent of the ongoing monthly retainer:\n"
        "  - Step 1 (Book Review & Clean-Up): Conduct deep review of the full fiscal year (April–March); resolve adjustments, reclassifications, accruals, and reconciling items; ensure accurate coding across fee, grant, and donation revenue streams; validate deferred revenue and prepaid expenses; reconcile ADP payroll records to QBO for the full year.\n"
        "  - Step 2 (Audit Preparation & Working Papers): Prepare year-end financial statements, audit schedules, account reconciliations, and supporting documentation; build the PBC (Prepared By Client) list; coordinate board minutes, grant agreements, and signed contracts from the Executive Director.\n"
        "  - Step 3 (Auditor Liaison & Management): Serve as primary point of contact with the auditor; respond to auditor queries and information requests in 2 days; attend auditor meetings; implement any post-audit adjustments and journal entries recommended by the auditor.\n"
        "• Scope boundary: Sympl is positioned as year-end review, audit-preparation, and auditor-liaison support; the proposal does not present Sympl as performing the audit."
    )

    # Patch 10: Chunk 13 TACT_2026_EXCLUSIONS
    c13 = chunks[12]
    assert c13['chunk_key'] == 'TACT_2026_EXCLUSIONS'
    c13['retrieval_text'] = (
        "Section: Software Subscription Exclusion\n"
        "Content:\n"
        "Software subscription fees, including QuickBooks Online and Plooto, are not included."
    )

    # Curation status
    data['proposal']['metadata']['curation_status'] = 'approved_for_import'

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')

    print("Successfully patched tact_2026.json!")

if __name__ == '__main__':
    patch_tact()
