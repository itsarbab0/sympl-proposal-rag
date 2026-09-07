import json

def generate_pirs_json():
    # Page 1
    p1_raw = (
        "ACCOUNTING SERVICES\n"
        "PROPOSAL\n"
        "P R O P O S E D  B Y\n"
        "PACIFIC IMMIGRANT RESOURCES SOCIETY  \n"
        "21 JUNE, 2025"
    )
    p1_clean = (
        "ACCOUNTING SERVICES PROPOSAL\n"
        "PROPOSED BY: PACIFIC IMMIGRANT RESOURCES SOCIETY\n"
        "21 JUNE, 2025"
    )

    # Page 2
    p2_raw = (
        "1. AUDIT PREPARATION & LIAISON \n"
        "Objective:\n"
        "Ensure a smooth and compliant audit process for the previous\n"
        "fiscal year (ending July 31 2025), including liaisoning with the\n"
        "auditor.\n"
        "Scope of Work:\n"
        "Act as primary liaison with external auditor\n"
        "Prepare financial statements and documentation for FY audit,\n"
        "alongside outgoing Finance Director\n"
        "Conduct a deep-dive review of prior year financials, including\n"
        "time with the Finance Director to clarify key entries and resolve\n"
        "outstanding questions\n"
        "Review and reconcile entries and resolve discrepancies\n"
        "Coordinate with bookkeeper to compile and validate backup\n"
        "documentation\n"
        "Respond to auditor questions within 1–2 business days\n"
        "Join auditor meetings and coordinate all follow-up items\n"
        "Prepare PBC (Prepared By Client) list items and ensure timely\n"
        "delivery\n"
        "Provide summary audit report and handover notes post-audit\n"
        "Note: It is ideal to maintain access to the outgoing Finance Director\n"
        "for 4 weeks for audit preparation purposes. \n"
        "Timeline: Approx 8-10 weeks - based on audit timeline"
    )
    p2_clean = (
        "1. AUDIT PREPARATION & LIAISON\n"
        "Objective:\n"
        "Ensure a smooth and compliant audit process for the previous fiscal year (ending July 31 2025), including liaising with the auditor.\n"
        "Scope of Work:\n"
        "- Act as primary liaison with external auditor\n"
        "- Prepare financial statements and documentation for FY audit, alongside outgoing Finance Director\n"
        "- Conduct a deep-dive review of prior year financials, including time with the Finance Director to clarify key entries and resolve outstanding questions\n"
        "- Review and reconcile entries and resolve discrepancies\n"
        "- Coordinate with bookkeeper to compile and validate backup documentation\n"
        "- Respond to auditor questions within 1–2 business days\n"
        "- Join auditor meetings and coordinate all follow-up items\n"
        "- Prepare PBC (Prepared By Client) list items and ensure timely delivery\n"
        "- Provide summary audit report and handover notes post-audit\n"
        "Note: It is ideal to maintain access to the outgoing Finance Director for 4 weeks for audit preparation purposes.\n"
        "Timeline: Approx 8-10 weeks - based on audit timeline"
    )

    # Page 3
    p3_raw = (
        "2. BOOKKEEPING OVERSIGHT &\n"
        "FINANCIAL MANAGEMENT\n"
        "Objective:\n"
        "Ensure accurate, timely, and funder-compliant bookkeeping through\n"
        "hands-on oversight, quality control, and support for PIRS’s internal\n"
        "bookkeeper, while gradually introducing process improvements and\n"
        "clearer financial reporting systems.\n"
        "Scope of Work:\n"
        "Manage all AP/AR and monthly reconciliations to ensure accuracy\n"
        "Oversee day-to-day tasks of junior bookkeeper with regular\n"
        "check-ins and support especially for accounts payable\n"
        "Evaluate bookkeeper’s performance over a 2–3 month period and\n"
        "recommend future staffing model\n"
        "Manage accounts receivable, including invoicing, grant\n"
        "management and donations\n"
        "Develop and implement GL coding standards aligned with\n"
        "internal, funder, audit requirements\n"
        "Conduct monthly financial reviews and trial balance checks for\n"
        "accuracy\n"
        "Assist with cash flow tracking and monthly budget variance\n"
        "analysis tied to project-based reporting needs\n"
        "Prepare monthly financial summary reports for EDs and\n"
        "leadership\n"
        "Develop a bookkeeping calendar and approval workflow \n"
        "Timeline: Ongoing"
    )
    p3_clean = (
        "2. BOOKKEEPING OVERSIGHT & FINANCIAL MANAGEMENT\n"
        "Objective:\n"
        "Ensure accurate, timely, and funder-compliant bookkeeping through hands-on oversight, quality control, and support for PIRS’s internal bookkeeper, while gradually introducing process improvements and clearer financial reporting systems.\n"
        "Scope of Work:\n"
        "- Manage all AP/AR and monthly reconciliations to ensure accuracy\n"
        "- Oversee day-to-day tasks of junior bookkeeper with regular check-ins and support especially for accounts payable\n"
        "- Evaluate bookkeeper’s performance over a 2–3 month period and recommend future staffing model\n"
        "- Manage accounts receivable, including invoicing, grant management and donations\n"
        "- Develop and implement GL coding standards aligned with internal, funder, audit requirements\n"
        "- Conduct monthly financial reviews and trial balance checks for accuracy\n"
        "- Assist with cash flow tracking and monthly budget variance analysis tied to project-based reporting needs\n"
        "- Prepare monthly financial summary reports for EDs and leadership\n"
        "- Develop a bookkeeping calendar and approval workflow\n"
        "Timeline: Ongoing"
    )

    # Page 4
    p4_raw = (
        "3. PAYROLL MANAGEMENT \n"
        "Objective:\n"
        "To manage end-to-end payroll processing and accounting w/ system\n"
        "integration and compliance, while evaluating platform options. \n"
        "Scope of Work:\n"
        "Manage payroll cycles (weekly, bi-weekly, semi-monthly, or\n"
        "monthly) for full-time, part-time, seasonal, and contract staff\n"
        "Process hourly staff and contractor payments, including\n"
        "government-funded programs like Canada Summer Jobs\n"
        "Handle employee changes, new hires, terminations, and vacation\n"
        "tracking within payroll software\n"
        "Reconcile payroll data with QuickBooks each cycle; implement\n"
        "workarounds to reduce manual spreadsheet use\n"
        "Ensure accurate source deductions (CPP, EI, income tax) and\n"
        "submit federal/provincial remittances\n"
        "Track payroll liabilities such as vacation pay, statutory\n"
        "deductions, and year-end accruals\n"
        "Prepare and file T4, T4A, and ROE forms in line with CRA and\n"
        "provincial requirements\n"
        "Maintain and update employee records in payroll system\n"
        "Develop a payroll calendar and approval workflow with manager\n"
        "cutoffs and review steps\n"
        "Evaluate whether to continue with PayWorks or transition to\n"
        "QBO Payroll for better integration and efficiency\n"
        "Note: While we manage all payroll accounting and processing,\n"
        "managers must provide timely payroll data (e.g., timesheets, new\n"
        "hires, exits). We do not manage HR functions.\n"
        "Timeline: Ongoing"
    )
    p4_clean = (
        "3. PAYROLL MANAGEMENT\n"
        "Objective:\n"
        "To manage end-to-end payroll processing and accounting with system integration and compliance, while evaluating platform options.\n"
        "Scope of Work:\n"
        "- Manage payroll cycles (weekly, bi-weekly, semi-monthly, or monthly) for full-time, part-time, seasonal, and contract staff\n"
        "- Process hourly staff and contractor payments, including government-funded programs like Canada Summer Jobs\n"
        "- Handle employee changes, new hires, terminations, and vacation tracking within payroll software\n"
        "- Reconcile payroll data with QuickBooks each cycle; implement workarounds to reduce manual spreadsheet use\n"
        "- Ensure accurate source deductions (CPP, EI, income tax) and submit federal/provincial remittances\n"
        "- Track payroll liabilities such as vacation pay, statutory deductions, and year-end accruals\n"
        "- Prepare and file T4, T4A, and ROE forms in line with CRA and provincial requirements\n"
        "- Maintain and update employee records in payroll system\n"
        "- Develop a payroll calendar and approval workflow with manager cutoffs and review steps\n"
        "- Evaluate whether to continue with PayWorks or transition to QBO Payroll for better integration and efficiency\n"
        "Note: While we manage all payroll accounting and processing, managers must provide timely payroll data (e.g., timesheets, new hires, exits). We do not manage HR functions.\n"
        "Timeline: Ongoing"
    )

    # Page 5
    p5_raw = (
        "4. DIGITAL TRANSFORMATION &\n"
        "STAFF TRAINING\n"
        "Objective:\n"
        "Conduct a full digital systems audit to identify integration gaps,\n"
        "inefficiencies, and implement inclusive, user-friendly processes that\n"
        "improve funder reporting and reduce manual work.\n"
        "Scope of Work:\n"
        "1. Audit & Strategy Development\n"
        "Conduct a deep-dive review of current financial systems,\n"
        "processes, and overall tech stack\n"
        "Hold meetings with the outgoing Finance Director and current\n"
        "team to understand existing workflows, strengths, and\n"
        "challenges\n"
        "Assess the current chart of accounts, class structure, and GL\n"
        "setup to identify gaps and areas for improvement\n"
        "Evaluate existing budget templates at both the organizational\n"
        "and departmental levels\n"
        "Review project and funder reporting templates and compare\n"
        "them to internal financial reporting tools\n"
        "Map current workflows and process flows; identify inefficiencies,\n"
        "redundancies, and compliance risks\n"
        "Assess digital literacy levels across staff and review system\n"
        "integration points between teams\n"
        "Recommend updated workflows, approval processes, and\n"
        "internal controls to improve efficiency and compliance\n"
        "Propose refinements to the tech stack to reduce manual work\n"
        "and improve automation and reporting\n"
        "Develop and deliver future-state process maps and a clear\n"
        "transformation roadmap"
    )
    p5_clean = (
        "4. DIGITAL TRANSFORMATION & STAFF TRAINING\n"
        "Objective:\n"
        "Conduct a full digital systems audit to identify integration gaps, inefficiencies, and implement inclusive, user-friendly processes that improve funder reporting and reduce manual work.\n"
        "Scope of Work:\n"
        "1. Audit & Strategy Development\n"
        "- Conduct a deep-dive review of current financial systems, processes, and overall tech stack\n"
        "- Hold meetings with the outgoing Finance Director and current team to understand existing workflows, strengths, and challenges\n"
        "- Assess the current chart of accounts, class structure, and GL setup to identify gaps and areas for improvement\n"
        "- Evaluate existing budget templates at both the organizational and departmental levels\n"
        "- Review project and funder reporting templates and compare them to internal financial reporting tools\n"
        "- Map current workflows and process flows; identify inefficiencies, redundancies, and compliance risks\n"
        "- Assess digital literacy levels across staff and review system integration points between teams\n"
        "- Recommend updated workflows, approval processes, and internal controls to improve efficiency and compliance\n"
        "- Propose refinements to the tech stack to reduce manual work and improve automation and reporting\n"
        "- Develop and deliver future-state process maps and a clear transformation roadmap"
    )

    # Page 6
    p6_part2_raw = (
        "2. Implementation of Improved Tools and Processes\n"
        "Configure the chart of accounts and GL structure to align with\n"
        "funder and internal management reporting needs\n"
        "Develop project-level accounting structures for tracking actuals\n"
        "and generating program-specific reports\n"
        "Create standardized reporting templates aligned with key funder\n"
        "compliance and reporting requirements\n"
        "Integrate payroll, expense management, and payment systems\n"
        "with the central accounting platform\n"
        "Establish internal workflows for expense submission, approval,\n"
        "and GL coding\n"
        "Implement budget tracking tools and reporting mechanisms to\n"
        "support monthly and quarterly reviews\n"
        "Set up integrated cash flow projection tools to accounting data\n"
        "Test all system integrations and validate the accuracy \n"
        "Coordinate with internal leads and external vendors to ensure\n"
        "smooth setup and configuration"
    )
    p6_part2_clean = (
        "2. Implementation of Improved Tools and Processes\n"
        "- Configure the chart of accounts and GL structure to align with funder and internal management reporting needs\n"
        "- Develop project-level accounting structures for tracking actuals and generating program-specific reports\n"
        "- Create standardized reporting templates aligned with key funder compliance and reporting requirements\n"
        "- Integrate payroll, expense management, and payment systems with the central accounting platform\n"
        "- Establish internal workflows for expense submission, approval, and GL coding\n"
        "- Implement budget tracking tools and reporting mechanisms to support monthly and quarterly reviews\n"
        "- Set up integrated cash flow projection tools to accounting data\n"
        "- Test all system integrations and validate the accuracy\n"
        "- Coordinate with internal leads and external vendors to ensure smooth setup and configuration"
    )

    p6_part3_raw = (
        "3. Staff Training and Change Management\n"
        "Deliver role-specific training sessions tailored to tools and\n"
        "processes\n"
        "Develop SOPs, quick guides, and workflow documentation\n"
        "Offer 2 months of ongoing post-training support for adoption\n"
        "and troubleshooting\n"
        "Conduct post-training survey to gather employee feedback on\n"
        "new processes\n"
        "Timeline: Approx 12-18 weeks (based on final scope)"
    )
    p6_part3_clean = (
        "3. Staff Training and Change Management\n"
        "- Deliver role-specific training sessions tailored to tools and processes\n"
        "- Develop SOPs, quick guides, and workflow documentation\n"
        "- Offer 2 months of ongoing post-training support for adoption and troubleshooting\n"
        "- Conduct post-training survey to gather employee feedback on new processes\n"
        "Timeline: Approx 12-18 weeks (based on final scope)"
    )

    p6_raw = (
        "4. DIGITAL TRANSFORMATION &\n"
        "STAFF TRAINING\n"
        f"{p6_part2_raw}\n"
        f"{p6_part3_raw}"
    )
    p6_clean = (
        "4. DIGITAL TRANSFORMATION & STAFF TRAINING (Continued)\n"
        f"{p6_part2_clean}\n\n"
        f"{p6_part3_clean}"
    )

    # Page 7
    p7_raw = (
        "WHY US?\n"
        "Sympl Solutions is committed to ensuring a high standard of financial\n"
        "clarity and timely support. We bring:\n"
        "A responsive, detail-oriented team\n"
        "Decade-long expertise in nonprofit finance\n"
        "Streamlined tech integration and clear process flows\n"
        "BIPOC and immigrant-led leadership with lived experiences in\n"
        "community, social service and arts & culture\n"
        "We value thoughtful system design, clarity in reporting, and\n"
        "building long-term trusted partnerships\n"
        "Any new requirements or adjustments can be discussed and\n"
        "integrated as needed. We work with transparency, flexibility, and a\n"
        "commitment to helping our partners thrive."
    )
    p7_clean = (
        "WHY US?\n"
        "Sympl Solutions is committed to ensuring a high standard of financial clarity and timely support. We bring:\n"
        "- A responsive, detail-oriented team\n"
        "- Decade-long expertise in nonprofit finance\n"
        "- Streamlined tech integration and clear process flows\n"
        "- BIPOC and immigrant-led leadership with lived experiences in community, social service and arts & culture\n"
        "- We value thoughtful system design, clarity in reporting, and building long-term trusted partnerships\n"
        "Any new requirements or adjustments can be discussed and integrated as needed. We work with transparency, flexibility, and a commitment to helping our partners thrive."
    )

    full_proposal_raw = f"{p1_raw}\n\n{p2_raw}\n\n{p3_raw}\n\n{p4_raw}\n\n{p5_raw}\n\n{p6_raw}\n\n{p7_raw}"
    full_proposal_clean = f"{p1_clean}\n\n{p2_clean}\n\n{p3_clean}\n\n{p4_clean}\n\n{p5_clean}\n\n{p6_clean}\n\n{p7_clean}"

    # Chunks
    # Chunk 1: AUDIT
    c1 = {
        "chunk_key": "PIRS_2025_AUDIT_PREPARATION",
        "section_order": 1,
        "section_type": "audit",
        "section_title": "1. AUDIT PREPARATION & LIAISON",
        "service_modules": [
            "audit",
            "year_end",
            "reconciliations",
            "transition"
        ],
        "organization_type": "unknown",
        "sector": "unknown",
        "engagement_type": "ongoing_plus_transformation",
        "core_bookkeeping": False,
        "accounting_systems": [],
        "payroll_systems": [],
        "cadence": [
            "one_time"
        ],
        "special_requirements": [
            "previous_fiscal_year_audit_preparation",
            "outgoing_finance_director_collaboration",
            "primary_external_auditor_liaison",
            "financial_statement_preparation",
            "audit_documentation",
            "deep_dive_prior_year_financial_review",
            "entry_reconciliation",
            "discrepancy_resolution",
            "bookkeeper_backup_documentation_coordination",
            "auditor_query_response_1_to_2_business_days",
            "auditor_meeting_participation",
            "audit_follow_up_coordination",
            "pbc_list_preparation",
            "timely_pbc_delivery",
            "post_audit_summary_report",
            "handover_notes"
        ],
        "raw_text": p2_raw,
        "cleaned_text": p2_clean,
        "retrieval_text": (
            "Section: Audit Preparation & Liaison\n"
            "Service modules: audit, year_end, reconciliations, transition\n"
            "Cadence: one-time audit support engagement (approx 8–10 weeks based on audit timeline)\n"
            "Special requirements: previous fiscal year audit preparation, outgoing finance director collaboration, primary external auditor liaison, financial statement preparation, audit documentation, deep-dive prior year financial review, entry reconciliation, discrepancy resolution, bookkeeper backup documentation coordination, auditor query response within 1–2 business days, auditor meeting participation, audit follow-up coordination, PBC list preparation, timely PBC delivery, post-audit summary report, handover notes\n"
            "Content:\n"
            "Audit Preparation & Liaison\n\n"
            "• Objective: Ensure a smooth and compliant audit process for the previous fiscal year (ending July 31 2025), including liaising with the auditor.\n"
            "• Act as primary liaison with external auditor.\n"
            "• Prepare financial statements and documentation for fiscal year audit, working alongside outgoing Finance Director.\n"
            "• Conduct a deep-dive review of prior year financials, including dedicated time with the Finance Director to clarify key entries and resolve outstanding questions.\n"
            "• Review and reconcile entries and resolve discrepancies.\n"
            "• Coordinate with bookkeeper to compile and validate backup documentation.\n"
            "• Respond to auditor questions within 1–2 business days.\n"
            "• Join auditor meetings and coordinate all follow-up items.\n"
            "• Prepare Prepared By Client (PBC) list items and ensure timely delivery.\n"
            "• Provide summary audit report and handover notes post-audit.\n"
            "• Operational assumption: It is ideal to maintain access to the outgoing Finance Director for 4 weeks for audit preparation purposes.\n"
            "• Scope boundary: Sympl is positioned as audit preparation, financial statement compilation, working paper preparation, and auditor liaison; Sympl does not perform the independent audit."
        ),
        "metadata": {
            "source_pages": [2],
            "timeline": "approximately_8_to_10_weeks",
            "outgoing_finance_director_access": "ideally_4_weeks"
        },
        "retrieval_enabled": True,
        "commercial_reference_only": False,
        "pricing_content": False,
        "boilerplate_content": False
    }

    # Chunk 2: BOOKKEEPING OVERSIGHT & FINANCIAL MANAGEMENT
    c2 = {
        "chunk_key": "PIRS_2025_BOOKKEEPING_OVERSIGHT_FINANCIAL_MANAGEMENT",
        "section_order": 2,
        "section_type": "financial_management",
        "section_title": "2. BOOKKEEPING OVERSIGHT & FINANCIAL MANAGEMENT",
        "service_modules": [
            "bookkeeping",
            "financial_management",
            "reconciliations",
            "accounts_payable",
            "accounts_receivable",
            "financial_reporting",
            "budgeting",
            "cash_flow",
            "funder_reporting"
        ],
        "organization_type": "unknown",
        "sector": "unknown",
        "engagement_type": "ongoing_plus_transformation",
        "core_bookkeeping": True,
        "accounting_systems": [],
        "payroll_systems": [],
        "cadence": [
            "ongoing",
            "monthly"
        ],
        "special_requirements": [
            "internal_junior_bookkeeper",
            "bookkeeping_oversight",
            "quality_control",
            "junior_bookkeeper_regular_check_ins",
            "accounts_payable_support",
            "bookkeeper_performance_evaluation",
            "future_staffing_model_recommendation",
            "ap_ar_management",
            "monthly_reconciliations",
            "accounts_receivable_invoicing",
            "grant_management",
            "donations",
            "gl_coding_standards",
            "internal_funder_audit_alignment",
            "monthly_financial_reviews",
            "trial_balance_checks",
            "cash_flow_tracking",
            "monthly_budget_variance_analysis",
            "project_based_reporting",
            "monthly_financial_summary_reports",
            "executive_director_and_leadership_reporting",
            "bookkeeping_calendar",
            "approval_workflow"
        ],
        "raw_text": p3_raw,
        "cleaned_text": p3_clean,
        "retrieval_text": (
            "Section: Bookkeeping Oversight & Financial Management\n"
            "Service modules: bookkeeping, financial management, reconciliations, accounts payable, accounts receivable, financial reporting, budgeting, cash flow, funder reporting\n"
            "Cadence: ongoing, monthly\n"
            "Special requirements: internal junior bookkeeper, bookkeeping oversight, quality control, junior bookkeeper regular check-ins, accounts payable support, bookkeeper performance evaluation, future staffing model recommendation, AP/AR management, monthly reconciliations, accounts receivable invoicing, grant management, donations, GL coding standards, internal funder audit alignment, monthly financial reviews, trial balance checks, cash flow tracking, monthly budget variance analysis, project-based reporting, monthly financial summary reports, executive director and leadership reporting, bookkeeping calendar, approval workflow\n"
            "Content:\n"
            "Bookkeeping Oversight & Financial Management\n\n"
            "• Objective: Ensure accurate, timely, and funder-compliant bookkeeping through hands-on oversight, quality control, and support for PIRS's internal bookkeeper, while gradually introducing process improvements and clearer financial reporting systems.\n"
            "• Bookkeeper Oversight & Support: Oversee day-to-day tasks of internal junior bookkeeper with regular check-ins and support, especially for accounts payable.\n"
            "• Staffing Model Evaluation: Evaluate the junior bookkeeper's performance over a 2–3 month period and recommend future staffing model.\n"
            "• Reconciliations & Operations: Manage all AP/AR and monthly reconciliations to ensure accuracy.\n"
            "• Accounts Receivable & Revenue: Manage accounts receivable, including invoicing, grant management, and donations.\n"
            "• Accounting Standards & Controls: Develop and implement GL coding standards aligned with internal, funder, and audit requirements; develop a bookkeeping calendar and approval workflow.\n"
            "• Reviews & Financial Analysis: Conduct monthly financial reviews and trial balance checks for accuracy; assist with cash flow tracking and monthly budget variance analysis tied to project-based reporting needs.\n"
            "• Leadership Reporting: Prepare monthly financial summary reports for Executive Directors and leadership.\n"
            "• Operating Model Boundary: The internal junior bookkeeper performs day-to-day bookkeeping tasks under Sympl's hands-on oversight and support; Sympl develops the bookkeeping calendar and approval workflow."
        ),
        "metadata": {
            "source_pages": [3],
            "bookkeeper_evaluation_period": "2_to_3_months"
        },
        "retrieval_enabled": True,
        "commercial_reference_only": False,
        "pricing_content": False,
        "boilerplate_content": False
    }

    # Chunk 3: PAYROLL MANAGEMENT
    c3 = {
        "chunk_key": "PIRS_2025_PAYROLL",
        "section_order": 3,
        "section_type": "payroll",
        "section_title": "3. PAYROLL MANAGEMENT",
        "service_modules": [
            "payroll",
            "compliance"
        ],
        "organization_type": "unknown",
        "sector": "unknown",
        "engagement_type": "ongoing_plus_transformation",
        "core_bookkeeping": False,
        "accounting_systems": [
            "QuickBooks"
        ],
        "payroll_systems": [
            "PayWorks",
            "QuickBooks Online Payroll"
        ],
        "cadence": [
            "weekly",
            "biweekly",
            "semi_monthly",
            "monthly",
            "ongoing"
        ],
        "special_requirements": [
            "full_time_staff",
            "part_time_staff",
            "seasonal_staff",
            "contract_staff",
            "hourly_staff",
            "canada_summer_jobs",
            "employee_changes",
            "new_hires",
            "terminations",
            "vacation_tracking",
            "payroll_reconciliation_to_quickbooks",
            "reduce_manual_spreadsheet_use",
            "cpp_source_deductions",
            "ei_source_deductions",
            "income_tax_source_deductions",
            "federal_provincial_remittances",
            "vacation_pay_liability",
            "statutory_deduction_liability",
            "year_end_accruals",
            "t4_filing",
            "t4a_filing",
            "roe_filing",
            "employee_payroll_records",
            "payroll_calendar",
            "approval_workflow",
            "manager_cutoffs",
            "review_steps",
            "payworks_vs_qbo_payroll_evaluation",
            "manager_payroll_data_dependency",
            "hr_functions_excluded"
        ],
        "raw_text": p4_raw,
        "cleaned_text": p4_clean,
        "retrieval_text": (
            "Section: Payroll Management\n"
            "Service modules: payroll, compliance\n"
            "Accounting systems: QuickBooks\n"
            "Payroll systems: PayWorks (current), QuickBooks Online Payroll (under evaluation)\n"
            "Cadence: weekly, bi-weekly, semi-monthly, monthly, ongoing\n"
            "Special requirements: full-time staff, part-time staff, seasonal staff, contract staff, hourly staff, Canada Summer Jobs, employee changes, new hires, terminations, vacation tracking, payroll reconciliation to QuickBooks, reduce manual spreadsheet use, CPP source deductions, EI source deductions, income tax source deductions, federal provincial remittances, vacation pay liability, statutory deduction liability, year-end accruals, T4 filing, T4A filing, ROE filing, employee payroll records, payroll calendar, approval workflow, manager cutoffs, review steps, PayWorks vs QBO Payroll evaluation, manager payroll data dependency, HR functions excluded\n"
            "Content:\n"
            "Payroll Management\n\n"
            "• Objective: Manage end-to-end payroll processing and accounting with system integration and compliance, while evaluating platform options.\n"
            "• Payroll Processing: Manage payroll cycles (weekly, bi-weekly, semi-monthly, or monthly) for full-time, part-time, seasonal, and contract staff.\n"
            "• Hourly Staff & Grants: Process hourly staff and contractor payments, including government-funded programs like Canada Summer Jobs.\n"
            "• Employee Records & Changes: Handle employee changes, new hires, terminations, and vacation tracking within payroll software; maintain and update employee records in payroll system.\n"
            "• Accounting & Reconciliations: Reconcile payroll data with QuickBooks each cycle; implement workarounds to reduce manual spreadsheet use.\n"
            "• Statutory Compliance & Remittances: Ensure accurate source deductions (CPP, EI, income tax) and submit federal and provincial remittances; track payroll liabilities such as vacation pay, statutory deductions, and year-end accruals.\n"
            "• Year-End Filings: Prepare and file T4, T4A, and ROE forms in line with CRA and provincial requirements.\n"
            "• Workflows & Calendars: Develop a payroll calendar and approval workflow with manager cutoffs and review steps.\n"
            "• Platform Evaluation: Evaluate whether to continue with current PayWorks software or transition to QuickBooks Online Payroll (QBO Payroll) for better integration and efficiency.\n"
            "• Responsibility & HR Boundary: Sympl manages all payroll accounting and processing; managers must provide timely payroll data (e.g., timesheets, new hires, exits); Sympl does not manage HR functions."
        ),
        "metadata": {
            "source_pages": [4],
            "system_state": {
                "current": ["PayWorks"],
                "proposed_or_under_evaluation": ["QuickBooks Online Payroll"]
            }
        },
        "retrieval_enabled": True,
        "commercial_reference_only": False,
        "pricing_content": False,
        "boilerplate_content": False
    }

    # Chunk 4: TRANSFORMATION STRATEGY
    c4 = {
        "chunk_key": "PIRS_2025_TRANSFORMATION_STRATEGY",
        "section_order": 4,
        "section_type": "digital_transformation",
        "section_title": "1. Audit & Strategy Development",
        "service_modules": [
            "digital_transformation",
            "systems_implementation",
            "funder_reporting",
            "process_documentation"
        ],
        "organization_type": "unknown",
        "sector": "unknown",
        "engagement_type": "ongoing_plus_transformation",
        "core_bookkeeping": False,
        "accounting_systems": [],
        "payroll_systems": [],
        "cadence": [
            "one_time"
        ],
        "special_requirements": [
            "financial_systems_review",
            "process_review",
            "technology_stack_review",
            "outgoing_finance_director_meetings",
            "current_team_workflow_discovery",
            "chart_of_accounts_assessment",
            "class_structure_assessment",
            "general_ledger_setup_assessment",
            "organizational_budget_template_review",
            "departmental_budget_template_review",
            "project_reporting_template_review",
            "funder_reporting_template_review",
            "internal_financial_reporting_tool_comparison",
            "current_workflow_mapping",
            "inefficiency_identification",
            "redundancy_identification",
            "compliance_risk_identification",
            "staff_digital_literacy_assessment",
            "system_integration_point_review",
            "workflow_recommendations",
            "approval_process_recommendations",
            "internal_control_recommendations",
            "technology_stack_refinement",
            "manual_work_reduction",
            "automation_improvement",
            "reporting_improvement",
            "future_state_process_maps",
            "transformation_roadmap"
        ],
        "raw_text": p5_raw,
        "cleaned_text": p5_clean,
        "retrieval_text": (
            "Section: Digital Transformation — Audit & Strategy Development\n"
            "Service modules: digital transformation, systems implementation, funder reporting, process documentation\n"
            "Cadence: one-time project phase (part of overall 12–18 week digital transformation engagement)\n"
            "Special requirements: financial systems review, process review, technology stack review, outgoing finance director meetings, current team workflow discovery, chart of accounts assessment, class structure assessment, general ledger setup assessment, organizational budget template review, departmental budget template review, project reporting template review, funder reporting template review, internal financial reporting tool comparison, current workflow mapping, inefficiency identification, redundancy identification, compliance risk identification, staff digital literacy assessment, system integration point review, workflow recommendations, approval process recommendations, internal control recommendations, technology stack refinement, manual work reduction, automation improvement, reporting improvement, future state process maps, transformation roadmap\n"
            "Content:\n"
            "Digital Transformation — Audit & Strategy Development\n\n"
            "• Objective: Conduct a full digital systems audit to identify integration gaps, inefficiencies, and implement inclusive, user-friendly processes that improve funder reporting and reduce manual work.\n"
            "• Systems & Tech Stack Review: Conduct a deep-dive review of current financial systems, processes, and overall tech stack.\n"
            "• Stakeholder Discovery: Hold meetings with the outgoing Finance Director and current team to understand existing workflows, strengths, and challenges.\n"
            "• Accounting Structure Assessment: Assess the current chart of accounts, class structure, and GL setup to identify gaps and areas for improvement.\n"
            "• Budget & Reporting Templates: Evaluate existing budget templates at both the organizational and departmental levels; review project and funder reporting templates and compare them to internal financial reporting tools.\n"
            "• Workflow Mapping & Risk Analysis: Map current workflows and process flows; identify inefficiencies, redundancies, and compliance risks.\n"
            "• Digital Literacy & Integration: Assess digital literacy levels across staff and review system integration points between teams.\n"
            "• Recommendations: Recommend updated workflows, approval processes, and internal controls to improve efficiency and compliance; propose refinements to the tech stack to reduce manual work and improve automation and reporting.\n"
            "• Deliverables: Develop and deliver future-state process maps and a clear transformation roadmap.\n"
            "• Context boundary: The proposal defines an audit and assessment process to identify potential gaps and inefficiencies, rather than asserting pre-existing confirmed findings."
        ),
        "metadata": {
            "source_pages": [5],
            "parent_section": "4. DIGITAL TRANSFORMATION & STAFF TRAINING",
            "overall_transformation_timeline": "approximately_12_to_18_weeks_based_on_final_scope"
        },
        "retrieval_enabled": True,
        "commercial_reference_only": False,
        "pricing_content": False,
        "boilerplate_content": False
    }

    # Chunk 5: TRANSFORMATION IMPLEMENTATION
    c5 = {
        "chunk_key": "PIRS_2025_TRANSFORMATION_IMPLEMENTATION",
        "section_order": 5,
        "section_type": "digital_transformation",
        "section_title": "2. Implementation of Improved Tools and Processes",
        "service_modules": [
            "digital_transformation",
            "systems_implementation",
            "funder_reporting",
            "budgeting",
            "cash_flow"
        ],
        "organization_type": "unknown",
        "sector": "unknown",
        "engagement_type": "ongoing_plus_transformation",
        "core_bookkeeping": False,
        "accounting_systems": [],
        "payroll_systems": [],
        "cadence": [
            "one_time"
        ],
        "special_requirements": [
            "chart_of_accounts_configuration",
            "general_ledger_structure_configuration",
            "funder_reporting_alignment",
            "internal_management_reporting_alignment",
            "project_level_accounting_structures",
            "actuals_tracking",
            "program_specific_reporting",
            "standardized_funder_reporting_templates",
            "payroll_system_integration",
            "expense_management_system_integration",
            "payment_system_integration",
            "central_accounting_platform_integration",
            "expense_submission_workflow",
            "expense_approval_workflow",
            "gl_coding_workflow",
            "budget_tracking_tools",
            "monthly_quarterly_review_support",
            "cash_flow_projection_tools",
            "system_integration_testing",
            "accuracy_validation",
            "internal_lead_coordination",
            "external_vendor_coordination",
            "setup_and_configuration"
        ],
        "raw_text": p6_part2_raw,
        "cleaned_text": p6_part2_clean,
        "retrieval_text": (
            "Section: Digital Transformation — Implementation of Improved Tools and Processes\n"
            "Service modules: digital transformation, systems implementation, funder reporting, budgeting, cash flow\n"
            "Cadence: one-time project phase (part of overall 12–18 week digital transformation engagement)\n"
            "Integration categories: central accounting platform, payroll, expense management, payment systems, cash flow projection tools\n"
            "Special requirements: chart of accounts configuration, general ledger structure configuration, funder reporting alignment, internal management reporting alignment, project-level accounting structures, actuals tracking, program-specific reporting, standardized funder reporting templates, payroll system integration, expense management system integration, payment system integration, central accounting platform integration, expense submission workflow, expense approval workflow, GL coding workflow, budget tracking tools, monthly quarterly review support, cash flow projection tools, system integration testing, accuracy validation, internal lead coordination, external vendor coordination, setup and configuration\n"
            "Content:\n"
            "Digital Transformation — Implementation of Improved Tools and Processes\n\n"
            "• COA & GL Configuration: Configure the chart of accounts and GL structure to align with funder and internal management reporting needs.\n"
            "• Project-Level Accounting: Develop project-level accounting structures for tracking actuals and generating program-specific reports.\n"
            "• Standardized Funder Templates: Create standardized reporting templates aligned with key funder compliance and reporting requirements.\n"
            "• Systems Integration: Integrate payroll, expense management, and payment systems with the central accounting platform.\n"
            "• Expense Workflows: Establish internal workflows for expense submission, approval, and GL coding.\n"
            "• Budget & Cash Flow Tools: Implement budget tracking tools and reporting mechanisms to support monthly and quarterly reviews; set up integrated cash flow projection tools connected to accounting data.\n"
            "• Testing & Validation: Test all system integrations and validate accuracy.\n"
            "• Coordination: Coordinate with internal leads and external vendors to ensure smooth setup and configuration.\n"
            "• Generic Systems Note: Integration targets represent functional system categories (central accounting platform, payroll, expense management, payment systems) rather than pre-specified third-party vendor products."
        ),
        "metadata": {
            "source_pages": [6],
            "integration_categories": [
                "payroll",
                "expense_management",
                "payment_systems"
            ],
            "overall_transformation_timeline": "approximately_12_to_18_weeks_based_on_final_scope"
        },
        "retrieval_enabled": True,
        "commercial_reference_only": False,
        "pricing_content": False,
        "boilerplate_content": False
    }

    # Chunk 6: TRAINING & CHANGE MANAGEMENT
    c6 = {
        "chunk_key": "PIRS_2025_TRAINING_CHANGE_MANAGEMENT",
        "section_order": 6,
        "section_type": "training",
        "section_title": "3. Staff Training and Change Management",
        "service_modules": [
            "training",
            "process_documentation"
        ],
        "organization_type": "unknown",
        "sector": "unknown",
        "engagement_type": "ongoing_plus_transformation",
        "core_bookkeeping": False,
        "accounting_systems": [],
        "payroll_systems": [],
        "cadence": [
            "one_time"
        ],
        "special_requirements": [
            "role_specific_training",
            "tools_and_process_training",
            "sop_development",
            "quick_guides",
            "workflow_documentation",
            "two_month_post_training_support",
            "adoption_support",
            "troubleshooting_support",
            "post_training_employee_feedback_survey"
        ],
        "raw_text": p6_part3_raw,
        "cleaned_text": p6_part3_clean,
        "retrieval_text": (
            "Section: Digital Transformation — Staff Training and Change Management\n"
            "Service modules: training, process documentation\n"
            "Cadence: one-time training delivery with 2 months ongoing post-training support\n"
            "Special requirements: role-specific training, tools and process training, SOP development, quick guides, workflow documentation, two-month post-training support, adoption support, troubleshooting support, post-training employee feedback survey\n"
            "Content:\n"
            "Staff Training and Change Management\n\n"
            "• Role-Specific Training: Deliver role-specific training sessions tailored to newly implemented tools and processes.\n"
            "• Documentation & Guides: Develop Standard Operating Procedures (SOPs), quick guides, and workflow documentation to support staff execution.\n"
            "• Post-Training Support: Offer 2 months of ongoing post-training support for user adoption and troubleshooting.\n"
            "• Feedback & Evaluation: Conduct post-training survey to gather employee feedback on new processes.\n"
            "• Training Audience: Training sessions and documentation are role-specific for staff using the updated systems and workflows."
        ),
        "metadata": {
            "source_pages": [6],
            "post_training_support": "2_months",
            "overall_transformation_timeline": "approximately_12_to_18_weeks_based_on_final_scope"
        },
        "retrieval_enabled": True,
        "commercial_reference_only": False,
        "pricing_content": False,
        "boilerplate_content": False
    }

    # Chunk 7: WHY US
    c7 = {
        "chunk_key": "PIRS_2025_WHY_US",
        "section_order": 7,
        "section_type": "why_us",
        "section_title": "WHY US?",
        "service_modules": [],
        "organization_type": "unknown",
        "sector": "unknown",
        "engagement_type": "ongoing_plus_transformation",
        "core_bookkeeping": False,
        "accounting_systems": [],
        "payroll_systems": [],
        "cadence": [],
        "special_requirements": [],
        "raw_text": p7_raw,
        "cleaned_text": p7_clean,
        "retrieval_text": (
            "Section: Why Us?\n"
            "Content:\n"
            "Sympl Solutions is committed to ensuring a high standard of financial clarity and timely support. We bring:\n"
            "• A responsive, detail-oriented team\n"
            "• Decade-long expertise in nonprofit finance\n"
            "• Streamlined tech integration and clear process flows\n"
            "• BIPOC and immigrant-led leadership with lived experiences in community, social service and arts & culture\n"
            "• We value thoughtful system design, clarity in reporting, and building long-term trusted partnerships\n"
            "Any new requirements or adjustments can be discussed and integrated as needed. We work with transparency, flexibility, and a commitment to helping our partners thrive."
        ),
        "metadata": {
            "source_pages": [7]
        },
        "retrieval_enabled": False,
        "commercial_reference_only": False,
        "pricing_content": False,
        "boilerplate_content": True
    }

    data = {
        "proposal": {
            "proposal_code": "PIRS_2025",
            "client_name": "Pacific Immigrant Resources Society",
            "proposal_title": "Accounting Services Proposal",
            "proposal_date": "2025-06-21",
            "source_filename": "PIRS x Sympl - Bookkeeping Proposal - July 2025.pdf",
            "organization_type": "unknown",
            "sector": "unknown",
            "engagement_type": "ongoing_plus_transformation",
            "proposal_complexity": "comprehensive",
            "core_bookkeeping": True,
            "raw_text": full_proposal_raw,
            "cleaned_text": full_proposal_clean,
            "metadata": {
                "source_page_count": 7,
                "proposal_month": "2025-06",
                "curation_method": "manual_ai_assisted",
                "curation_status": "draft_review",
                "source_temporal_inconsistency": "page_2_describes_previous_fiscal_year_ending_2025_07_31"
            }
        },
        "chunks": [c1, c2, c3, c4, c5, c6, c7]
    }

    out_file = 'data/normalized/pirs_2025.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')

    print(f"Successfully generated {out_file} with {len(data['chunks'])} chunks.")

if __name__ == '__main__':
    generate_pirs_json()
