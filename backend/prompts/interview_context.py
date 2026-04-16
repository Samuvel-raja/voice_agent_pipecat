"""
Mode-specific session configuration builders.
Each function returns a session details string embedded into the system prompt.
"""

from models import InterviewMode, InterviewSessionConfig


def build_ai_context(config: InterviewSessionConfig) -> str:
    """Dispatch to the correct context builder based on interview mode."""
    builders = {
        InterviewMode.general: _general_context,
        InterviewMode.technical: _technical_context,
        InterviewMode.final: _final_context,
        InterviewMode.teach_coding: _teach_coding_context,
    }
    return builders.get(config.mode, _general_context)(config)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _duration_line(config: InterviewSessionConfig) -> str:
    minutes = config.metadata.get("duration_minutes")
    return f"This session is about {minutes} minutes." if minutes else "Do not mention an exact duration."


def _question_lines(questions: list[str], fallback: list[str]) -> str:
    items = questions if questions else fallback
    return "\n".join(f"- {q}" for q in items)


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------

def _general_context(config: InterviewSessionConfig) -> str:
    c = config.candidate
    q_lines = _question_lines(
        config.questions,
        ["Ask 6–8 general interview questions covering motivation, collaboration, and role-fit."],
    )
    return f"""Session type: General interview
Candidate: {c.name}
Role applied: {c.role_applied or 'N/A'}
Duration: {_duration_line(config)}
Goal: Assess communication, motivation, role-fit, and collaboration patterns.

Interview phases:
Phase 1 — Opening and check-in as described in the opening rules.
Phase 2 — Warm-up: 2 questions about current work and motivation.
Phase 3 — General questions (ask in order as written):
{q_lines}
Phase 4 — Candidate questions.
Phase 5 — Closing and evaluation submission.

Scoring: Rate communication, clarity, ownership, and collaboration on a 1–10 scale per question with an overall recommendation.

At the end, submit the evaluation using submit_interview_result.
"""


def _technical_context(config: InterviewSessionConfig) -> str:
    c = config.candidate
    co = config.company
    company_name = co.name if co else "the company"
    role_title = (co.role_title if co else None) or c.role_applied or "the role"
    industry = co.industry if co else "N/A"
    jd = co.jd_summary if co else "N/A"
    focus = ", ".join(co.focus_areas) if co and co.focus_areas else "backend systems, APIs, reliability"
    stack = ", ".join(co.tech_stack) if co and co.tech_stack else "Python, databases, distributed systems"

    default_questions = [
        "Walk me through a backend system you designed end-to-end for scale and reliability.",
        "How do you design idempotency and retries for payment or order APIs?",
        "Tell me about a production incident you handled — what happened and what changed afterward?",
        "How do you approach database schema changes with zero downtime?",
        "How do you debug latency spikes in a distributed system?",
    ]
    q_lines = _question_lines(config.questions, default_questions)

    return f"""Session type: Technical interview
Candidate: {c.name}
Role: {role_title} at {company_name}
Industry: {industry}
Job summary: {jd}
Focus areas: {focus}
Tech stack: {stack}
Duration: {_duration_line(config)}
Goal: Assess technical depth, systems thinking, and incident/debug maturity.

Interview phases:
Phase 1 — Opening and check-in as described in the opening rules.
Phase 2 — Warm-up: 1 short question about current work, then move on.
Phase 3 — Technical questions (one per turn, in order):
{q_lines}
Phase 4 — Candidate questions.
Phase 5 — Closing and evaluation submission.

Scoring: Rate technical_competency, problem_solving, communication. Use evidence from answers.

At the end, submit the evaluation using submit_interview_result.
"""


def _final_context(config: InterviewSessionConfig) -> str:
    c = config.candidate
    co = config.company
    company_name = co.name if co else "the company"
    q_lines = _question_lines(
        config.questions,
        ["Ask 4–6 high-signal questions covering leadership decisions, execution under pressure, trade-offs, and long-term thinking."],
    )
    return f"""Session type: Final interview
Candidate: {c.name}
Company: {company_name}
Duration: {_duration_line(config)}
Goal: Validate seniority, judgment, leadership, and risk areas. This round is higher-bar than earlier ones.

Interview phases:
Phase 1 — Opening and check-in as described in the opening rules.
Phase 2 — Validate motivations, role expectations, and values.
Phase 3 — Deep-dive questions:
{q_lines}
Phase 4 — Candidate questions.
Phase 5 — Closing and evaluation submission.

Scoring: Weight leadership, judgment, and strategic thinking. Use evidence from answers.

At the end, submit the evaluation using submit_interview_result.
"""


def _teach_coding_context(config: InterviewSessionConfig) -> str:
    c = config.candidate
    topic = config.metadata.get("topic") or "a small coding task"
    language = config.metadata.get("language") or "Python"
    return f"""Session type: Guided coding session
Candidate: {c.name}
Language: {language}
Topic: {topic}
Duration: {_duration_line(config)}
Goal: Teach and assess coding fundamentals through a guided exercise.

Session approach:
- Teach in small steps. Ask the candidate to explain their thinking.
- Provide hints rather than full solutions when they get stuck.
- Run a single guided exercise. Ask for incremental solutions and test cases.

At the end, submit a coding evaluation using submit_interview_result.
"""
