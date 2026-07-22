"""
Gist Extractor
Extracts semantic meaning from verbatim input

Research Foundation:
- Fuzzy-Trace Theory: "Bottom-line understanding of meaning"
- "Forgetting details to grasp abstract concepts" (cognitive flexibility)
- Borges' "Funes": "To think is to forget differences, generalize, abstract"

Process:
1. Raw verbatim input → LLM compression
2. Extract semantic essence (1-2 sentences max)
3. Preserve meaning, discard noise

जय विदुराई! 🕉️
"""

import os
from typing import Optional, Dict


class GistExtractor:
    """
    Extract semantic gist from verbatim traces

    Research: "The brain is designed to forget details but retain meaning"

    Example:
    - Verbatim: "hmm... let me think... what was that auth file... ah yes, auth.py"
    - Gist: "User searching for authentication-related file"
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize gist extractor

        Args:
            model: LLM model for gist extraction
        """
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY required for gist extraction")

    def extract(self, verbatim: str, context: Optional[Dict] = None) -> str:
        """
        Extract semantic gist from verbatim input
        """
        # Build context string
        context_str = ""
        if context:
            context_str = f"\nContext: {context}"

        prompt = f"""Extract the core semantic meaning in ONE concise sentence.
Focus on WHAT was done and WHY, not the exact words used.
Be extremely concise - maximum 15 words.

Verbatim input: {verbatim}{context_str}

Semantic gist (one sentence, <15 words):"""

        gist = self._call_llm(prompt)
        return gist.strip()

    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM for gist extraction
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("This feature requires optional AI dependencies. Install them with: pip install \"vidurai[ai]\"")

        client = OpenAI(api_key=self.api_key)

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a semantic compression expert. Extract only the essential meaning."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.3
        )

        return response.choices[0].message.content

    def batch_extract(self, verbatim_list: list[str]) -> list[str]:
        """Extract gist from multiple inputs (batch processing)"""
        return [self.extract(v) for v in verbatim_list]
