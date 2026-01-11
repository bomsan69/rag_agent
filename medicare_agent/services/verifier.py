"""Answer verification service for citation validation and safety."""

import re
from typing import List, Tuple, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from medicare_agent.config import settings
from medicare_agent.models.schemas import Citation, Chunk
import logging

logger = logging.getLogger(__name__)


class VerifierService:
    """Service for verifying answer accuracy and citation alignment."""

    VERIFICATION_PROMPT = """You are a Medicare policy verification expert. Your job is to verify that answers are:
1. Fully supported by the provided evidence
2. Do not contain unsupported claims, especially numbers/dates
3. Use conservative, non-definitive language for conditional rules
4. Properly cite sources
5. Clearly distinguish between handbook information and general knowledge

Review the draft answer and identify any issues:
- UNSUPPORTED_CLAIM: Claims not in evidence
- MISSING_CITATION: Claims without proper citations
- MISSING_SOURCE_ATTRIBUTION: Uses general knowledge without stating "not in your handbook" or similar
- DEFINITIVE_LANGUAGE: Too definitive when rules are conditional
- NUMERIC_ERROR: Numbers/dates not in evidence or misquoted
- SAFE: No issues found

IMPORTANT: If the answer uses general Medicare knowledge (not from evidence), it MUST explicitly state that.
Examples of proper attribution:
✓ "Based on general Medicare information (not in your handbook)..."
✓ "While your handbook doesn't cover this, generally Medicare..."
✗ Stating information without indicating whether it's from handbook or general knowledge

Be strict and cautious."""

    def __init__(self):
        """Initialize verifier service."""
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0,
            openai_api_key=settings.openai_api_key
        )

    def verify(
        self,
        draft_answer: str,
        citations: List[Citation],
        evidence_chunks: List[Chunk]
    ) -> Tuple[bool, str, List[str], Literal["high", "medium", "low"]]:
        """Verify answer against evidence.

        Args:
            draft_answer: Generated answer to verify
            citations: Citations used in answer
            evidence_chunks: Original evidence chunks

        Returns:
            Tuple of (approved, revised_answer_or_original, issues, confidence)
        """
        logger.info("Verifying answer...")

        # Check for basic issues
        issues = []
        issues.extend(self._check_numeric_claims(draft_answer, evidence_chunks))
        issues.extend(self._check_definitive_language(draft_answer))
        issues.extend(self._check_citations(draft_answer))

        # LLM-based verification
        llm_issues = self._llm_verify(draft_answer, evidence_chunks)
        issues.extend(llm_issues)

        # Determine if approved
        critical_issues = [
            issue for issue in issues
            if "NUMERIC_ERROR" in issue or "UNSUPPORTED_CLAIM" in issue
        ]

        approved = len(critical_issues) == 0

        # Determine confidence
        if not issues:
            confidence = "high"
        elif len(critical_issues) == 0 and len(issues) <= 2:
            confidence = "medium"
        else:
            confidence = "low"

        # Revise if needed
        if not approved:
            logger.warning(f"Answer not approved. Issues: {issues}")
            revised = self._revise_answer(draft_answer, evidence_chunks, issues)
            return False, revised, issues, confidence
        elif issues:
            logger.info(f"Answer approved with minor issues: {issues}")
            revised = self._revise_answer(draft_answer, evidence_chunks, issues)
            return True, revised, issues, confidence
        else:
            logger.info("Answer approved without issues")
            return True, draft_answer, [], confidence

    def _check_numeric_claims(
        self,
        answer: str,
        evidence_chunks: List[Chunk]
    ) -> List[str]:
        """Check for numeric claims not in evidence.

        Args:
            answer: Answer text
            evidence_chunks: Evidence chunks

        Returns:
            List of issues found
        """
        issues = []

        # Extract numbers from answer
        numbers_in_answer = re.findall(r'\$?\d+(?:,\d{3})*(?:\.\d{2})?%?', answer)

        if numbers_in_answer:
            # Get all numbers from evidence
            evidence_text = " ".join(chunk.content for chunk in evidence_chunks)
            numbers_in_evidence = set(re.findall(r'\$?\d+(?:,\d{3})*(?:\.\d{2})?%?', evidence_text))

            # Check if answer numbers are in evidence
            for num in numbers_in_answer:
                if num not in numbers_in_evidence:
                    issues.append(f"NUMERIC_ERROR: '{num}' not found in evidence")

        return issues

    def _check_definitive_language(self, answer: str) -> List[str]:
        """Check for overly definitive language.

        Args:
            answer: Answer text

        Returns:
            List of issues found
        """
        issues = []

        # Definitive phrases that should be avoided
        definitive_patterns = [
            r'\b(you will|you must|always|never|definitely|certainly)\b',
            r'\b(guaranteed|required to|have to)\b'
        ]

        for pattern in definitive_patterns:
            matches = re.findall(pattern, answer, re.IGNORECASE)
            if matches:
                issues.append(
                    f"DEFINITIVE_LANGUAGE: Found '{matches[0]}'. "
                    f"Consider using 'may', 'generally', 'typically' instead"
                )
                break  # Only report once

        return issues

    def _check_citations(self, answer: str) -> List[str]:
        """Check for proper citations in answer.

        Args:
            answer: Answer text

        Returns:
            List of issues found
        """
        issues = []

        # Look for citation markers
        citation_pattern = r'\[.+?(?:Page|p\.|pg\.)\s*\d+.*?\]'
        citations = re.findall(citation_pattern, answer, re.IGNORECASE)

        # Check if answer has substantive content without citations
        # Remove common phrases and check length
        content = answer.lower()
        if len(content) > 200 and len(citations) == 0:
            issues.append("MISSING_CITATION: Long answer without citations")

        return issues

    def _llm_verify(
        self,
        draft_answer: str,
        evidence_chunks: List[Chunk]
    ) -> List[str]:
        """Use LLM to verify answer against evidence.

        Args:
            draft_answer: Answer to verify
            evidence_chunks: Evidence chunks

        Returns:
            List of issues found
        """
        evidence_text = "\n\n".join(
            f"[Evidence {i+1}]: {chunk.content}"
            for i, chunk in enumerate(evidence_chunks)
        )

        verification_request = f"""Draft Answer:
{draft_answer}

Evidence:
{evidence_text}

List any issues found (one per line). If no issues, respond with "SAFE"."""

        messages = [
            SystemMessage(content=self.VERIFICATION_PROMPT),
            HumanMessage(content=verification_request)
        ]

        response = self.llm.invoke(messages)
        result = response.content.strip()

        if result == "SAFE":
            return []

        # Parse issues
        issues = [line.strip() for line in result.split('\n') if line.strip()]
        return issues

    def _revise_answer(
        self,
        draft_answer: str,
        evidence_chunks: List[Chunk],
        issues: List[str]
    ) -> str:
        """Revise answer to address issues.

        Args:
            draft_answer: Original answer
            evidence_chunks: Evidence chunks
            issues: Issues to fix

        Returns:
            Revised answer
        """
        evidence_text = "\n\n".join(
            f"[Evidence {i+1}]: {chunk.content}"
            for i, chunk in enumerate(evidence_chunks)
        )

        revision_prompt = f"""Revise this answer to fix the following issues:

Issues:
{chr(10).join(f"- {issue}" for issue in issues)}

Original Answer:
{draft_answer}

Evidence:
{evidence_text}

Revised Answer (fix issues while keeping accurate information and citations):"""

        messages = [
            SystemMessage(content=self.VERIFICATION_PROMPT),
            HumanMessage(content=revision_prompt)
        ]

        response = self.llm.invoke(messages)
        revised = response.content.strip()

        logger.info("Answer revised to address issues")
        return revised

    def calculate_confidence(
        self,
        answer: str,
        evidence_chunks: List[Chunk],
        issues: List[str]
    ) -> Literal["high", "medium", "low"]:
        """Calculate confidence level for answer.

        Args:
            answer: Generated answer
            evidence_chunks: Evidence chunks used
            issues: Issues found during verification

        Returns:
            Confidence level
        """
        # Start with high confidence
        score = 100

        # Deduct for issues
        for issue in issues:
            if "NUMERIC_ERROR" in issue or "UNSUPPORTED_CLAIM" in issue:
                score -= 30
            elif "MISSING_CITATION" in issue or "MISSING_SOURCE_ATTRIBUTION" in issue:
                score -= 20
            elif "DEFINITIVE_LANGUAGE" in issue:
                score -= 10

        # Deduct for weak evidence
        if len(evidence_chunks) < 2:
            score -= 20

        # Bonus for multiple citations
        citations = re.findall(r'\[.+?Page\s*\d+.*?\]', answer, re.IGNORECASE)
        if len(citations) >= 3:
            score += 10

        # Determine level
        if score >= 80:
            return "high"
        elif score >= 50:
            return "medium"
        else:
            return "low"
