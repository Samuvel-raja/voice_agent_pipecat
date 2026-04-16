"""
FunctionSchema definition for the submit_interview_result LLM tool.
Kept here so all prompt/schema definitions live in one place.
"""

from pipecat.adapters.schemas.function_schema import FunctionSchema

SUBMIT_INTERVIEW_RESULT_SCHEMA = FunctionSchema(
    name="submit_interview_result",
    description="Submit the final structured interview evaluation for this candidate.",
    properties={
        "interview_mode": {
            "type": "string",
            "description": "Interview mode for this session.",
            "enum": ["general", "technical", "final", "teach_coding"],
        },
        "candidate_name": {"type": "string"},
        "role_applied": {"type": "string"},
        "interview_duration_minutes": {"type": "number"},
        "questions_asked": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "candidate_answer_summary": {"type": "string"},
                    "score": {"type": "number"},
                    "category": {
                        "type": "string",
                        "enum": ["warmup", "technical", "behavioral", "problem_solving", "culture_fit"],
                    },
                },
                "required": ["question", "candidate_answer_summary", "score", "category"],
            },
        },
        "scores": {"type": "object"},
        "overall_score": {"type": "number"},
        "recommendation": {
            "type": "string",
            "enum": ["strong_hire", "hire", "maybe", "no_hire"],
        },
        "strengths": {"type": "array", "items": {"type": "string"}},
        "areas_of_concern": {"type": "array", "items": {"type": "string"}},
        "hiring_manager_summary": {"type": "string"},
        "next_steps": {"type": "string"},
    },
    required=[
        "candidate_name",
        "role_applied",
        "interview_duration_minutes",
        "questions_asked",
        "scores",
        "overall_score",
        "recommendation",
        "strengths",
        "areas_of_concern",
        "hiring_manager_summary",
        "next_steps",
    ],
)


PUBLISH_TEACHING_SNIPPET_SCHEMA = FunctionSchema(
    name="publish_teaching_snippet",
    description=(
        "Publish a coding-teaching snippet/event to the UI so the candidate can see the code and steps live."
    ),
    properties={
        "title": {"type": "string", "description": "Short title for this teaching step."},
        "language": {"type": "string", "description": "Programming language for the snippet."},
        "code": {"type": "string", "description": "Code snippet to show in the UI."},
        "explanation": {
            "type": "string",
            "description": "One short explanation for this step (keep concise; spoken separately).",
        },
        "step": {
            "type": "number",
            "description": "Step number in the teaching flow (1-based).",
        },
        "kind": {
            "type": "string",
            "description": "Type of snippet.",
            "enum": ["hint", "skeleton", "solution", "test", "note"],
        },
    },
    required=["language", "code"],
)
