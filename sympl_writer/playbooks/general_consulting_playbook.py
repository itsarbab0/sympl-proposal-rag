"""
Sympl Solutions Proposal RAG — General Consulting Fallback Playbook

Contains Sympl's core consulting methodologies, discovery frameworks, implementation phasing,
and change management patterns. Used ONLY when a proposal's service category is unknown or
represents a new domain without a dedicated operational playbook.
"""

from typing import List

GENERAL_CONSULTING_PLAYBOOK_SYSTEM = """SYMPL GENERAL CONSULTING PLAYBOOK (CORE OPERATING PATTERNS):
When relevant to approved scope, incorporate Sympl's core consulting methodologies:
1. Discovery & Diagnostic Phase:
   - Conduct structured stakeholder discovery interviews and review current-state operational workflows.
   - Perform gap analysis against industry best practices and document critical organizational requirements.
   - Establish baseline metrics, project objectives, and formal success criteria before execution begins.
2. Solution Design & Implementation Methodology:
   - Design fit-for-purpose operational frameworks and workflows tailored to the client's organizational capacity.
   - Execute implementation in structured, milestone-based increments with regular weekly status checkpoints.
   - Validate intermediate deliverables through practical pilot testing and collaborative stakeholder reviews.
3. Phased Delivery Roadmap & Governance:
   - Structure engagements across clear phases: Discovery & Assessment, Solution Architecture, Execution/Testing, and Final Rollout.
   - Establish formal milestone sign-off gates so nothing advances without explicit client approval.
   - Manage operational risk through proactive dependency tracking and transparent communication.
4. Change Management & Operational Handover:
   - Deliver clear, plain-language operating guides tailored specifically to the client's internal team.
   - Conduct interactive walkthrough sessions to build internal ownership and sustained autonomy.
   - Conclude with an executive readout and structured post-project transition support.
IMPORTANT: Only use these workflows when relevant to approved scope. Do not hallucinate routine bookkeeping, website platforms, or specialized data pipelines unless explicitly specified in approved scope."""

GENERAL_CONSULTING_PLAYBOOK_USER_LINES: List[str] = [
    "1. SYMPL GENERAL CONSULTING PLAYBOOK (CORE OPERATING PATTERNS):",
    "   When relevant to approved scope, incorporate Sympl's proven consulting methodologies:",
    "   * Discovery & Diagnostic:",
    "     - Current-state operational assessment, stakeholder interviews, and gap analysis",
    "     - Objective setting and baseline metric definition",
    "   * Solution Design & Execution:",
    "     - Practical workflow architecture tailored to organizational capacity",
    "     - Milestone-based iterative implementation and regular progress check-ins",
    "   * Phased Delivery Roadmap:",
    "     - Structured phasing (Diagnostic -> Solution Architecture -> Implementation -> Handover)",
    "     - Explicit milestone sign-offs before proceeding across phases",
    "   * Change Management & Handover:",
    "     - Plain-language process guides and interactive team walkthroughs",
    "     - Executive debrief and dedicated post-rollout support window",
    "   IMPORTANT: Only use these workflows when relevant to approved scope. Do not hallucinate unapproved services or tools."
]

# -----------------------------------------------------------------------------
# Phase 2C Domain Decoupling Metadata
# -----------------------------------------------------------------------------
BENCHMARK_REFERENCES: List[str] = ["Sympl Advisory Engagements"]

JSON_EXAMPLE_SUBHEADING: str = "Operational Assessment & Milestone Roadmap"

EXECUTIVE_SUMMARY_GUIDANCE: str = """EXECUTIVE SUMMARY NARRATIVE GUIDANCE (GENERAL CONSULTING):
Problem:
Client faces operational workflow bottlenecks, organizational transition, and a lack of standardized operating procedures.
Approach:
Sympl delivers a structured consulting methodology spanning diagnostic assessment, architecture design, milestone execution, and team change management.
Outcome:
Documented standard operating procedures, verified milestone sign-offs, and operational stability."""

DOMAIN_VOCABULARY: List[str] = [
    "Operational Assessment", "Diagnostic Audit", "Implementation Roadmap",
    "Milestone Sign-off", "Standard Operating Procedures", "Change Management"
]

