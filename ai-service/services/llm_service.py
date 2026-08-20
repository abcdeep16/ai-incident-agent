import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from models.investigation import InvestigationResponse


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


SYSTEM_PROMPT = """
You are an AI software engineering assistant.

Your job is to analyze software engineering problems
carefully and provide practical, evidence-based answers.

Rules:
1. Do not invent logs, metrics, files, or facts.
2. Clearly distinguish evidence from assumptions.
3. If the available information is insufficient, say so.
4. Keep responses concise and technically useful.
5. Return your answer using the requested structured format.
"""


def generate_response(prompt: str, evidence: list[str]) -> InvestigationResponse:
    evidence_text = "\n".join(
        f"- {item}" for item in evidence
    )

    full_prompt = f"""
Incident:
{prompt}

Relevant engineering evidence:
{evidence_text}

Analyze the incident using the evidence above.

Important:
- Base your conclusions on the provided evidence.
- Do not invent logs, metrics, deployments, or other facts.
- If the evidence is insufficient, clearly say so.
- Distinguish confirmed evidence from possible explanations.
"""
  


    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=full_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=InvestigationResponse,
        ),
    )

    return InvestigationResponse.model_validate_json(response.text)