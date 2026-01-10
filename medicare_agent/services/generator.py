"""Answer generation service with citation enforcement."""

from typing import List, Tuple, AsyncIterator, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from medicare_agent.config import settings
from medicare_agent.models.schemas import Chunk, Citation
import logging

logger = logging.getLogger(__name__)


class GeneratorService:
    """Service for generating citation-based answers from evidence chunks."""

    SYSTEM_PROMPT = """You are a friendly Medicare expert helping elderly people (60+) understand Medicare. Use simple, clear language.

ANSWERING RULES:

1. **Check the Medicare Manual FIRST** - Use the evidence chunks provided
   - If information IS in the manual: Answer using the manual and cite it clearly
   - If information is NOT in the manual: Use your general knowledge and state it's not from the manual

2. **Use EASY language** - Remember your audience is 60+ years old
   - Avoid jargon and complex terms
   - Use short sentences
   - Explain like talking to a family member
   - Break down complex topics into simple steps

3. **Clearly show your SOURCE**:
   - From manual: "According to the Medicare Handbook [Page X]..."
   - From general knowledge: "Based on general Medicare information (not in your handbook)..."
   - Mixed: Show which parts are from where

4. **Be helpful and complete**:
   - Answer fully, don't say "I don't have information" unless truly unable to help
   - If manual has partial info, use it and add general knowledge for complete answer
   - Always try to be helpful

5. **LANGUAGE**: Respond in the SAME LANGUAGE as the user's question
   - English question → English answer
   - Korean (한국어) question → Korean (한국어) answer

EXAMPLE GOOD ANSWER (English):
"According to your Medicare Handbook [Page 27], if you sign up for Part B late, you'll pay an extra 10% for each year you waited. This extra cost continues as long as you have Part B.

For example (general information, not in handbook): if you waited 2 years, you'd pay 20% more than the regular price. So if the regular price is $100, you'd pay $120."

EXAMPLE GOOD ANSWER (Korean):
"메디케어 핸드북에 따르면 [27페이지], Part B에 늦게 가입하시면 늦은 해마다 10%씩 더 내셔야 합니다. 이 추가 비용은 Part B를 사용하시는 동안 계속 납부하셔야 합니다.

예를 들어 (핸드북에는 없는 일반 정보): 2년 늦게 가입하셨다면 정상 가격보다 20% 더 내시게 됩니다. 정상 가격이 100달러라면 120달러를 내시는 것입니다."

Remember: Be helpful, friendly, and clear. Elderly people need simple explanations, not complex legal language."""

    def __init__(self):
        """Initialize generator service."""
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0,
            openai_api_key=settings.openai_api_key
        )
        self.streaming_llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0,
            openai_api_key=settings.openai_api_key,
            streaming=True
        )
        # Fast model for classification and expansion
        self.fast_llm = ChatOpenAI(
            model=settings.fast_model if settings.use_fast_model_for_classification else settings.openai_model,
            temperature=0,
            openai_api_key=settings.openai_api_key
        ) if settings.use_fast_model_for_classification else self.llm

    def _format_evidence(self, chunks: List[Chunk]) -> str:
        """Format evidence chunks for prompt.

        Args:
            chunks: List of evidence chunks

        Returns:
            Formatted evidence string
        """
        evidence_parts = []

        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.metadata
            section = metadata.get("section", "Unknown")
            page = metadata.get("page_start", "Unknown")

            evidence_parts.append(
                f"[Evidence {i}]\n"
                f"Source: {section} (Page {page})\n"
                f"Content: {chunk.content}\n"
            )

        return "\n".join(evidence_parts)

    def _extract_citations_from_chunks(self, chunks: List[Chunk]) -> List[Citation]:
        """Extract citations from chunks.

        Args:
            chunks: List of chunks used as evidence

        Returns:
            List of Citation objects
        """
        citations = []
        seen = set()

        for chunk in chunks:
            metadata = chunk.metadata
            section = metadata.get("section", "Unknown")
            page = metadata.get("page_start", 0)
            doc_version = metadata.get("doc_version", settings.medicare_doc_version)

            # Create unique key to avoid duplicates
            key = (section, page, doc_version)

            if key not in seen:
                citations.append(Citation(
                    section=section,
                    page=page,
                    doc_version=doc_version,
                    chunk_id=chunk.chunk_id
                ))
                seen.add(key)

        return citations

    def generate(
        self,
        query: str,
        evidence_chunks: List[Chunk],
        intent: str = "general",
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, List[Citation]]:
        """Generate answer from evidence chunks.

        Args:
            query: User query
            evidence_chunks: Evidence chunks from retrieval
            intent: Query intent for context
            conversation_history: Previous messages [{"role": "user"|"assistant", "content": "..."}]

        Returns:
            Tuple of (answer, citations)
        """
        logger.info(f"Generating answer for query: {query[:100]}...")

        if not evidence_chunks:
            return (
                "I don't have sufficient information in the Medicare handbook to answer this question accurately. "
                "Please rephrase your question or consult the official Medicare documentation.",
                []
            )

        # Format evidence
        evidence_text = self._format_evidence(evidence_chunks)

        # Create prompt
        user_prompt = f"""User Question: {query}

Intent: {intent}

Evidence from Medicare Handbook 2026:
{evidence_text}

Based ONLY on the evidence provided above, answer the user's question. Remember to:
- Cite sources using [Section > Page X] format
- Use conservative language
- Never make claims without evidence
- State if information is insufficient"""

        # Build messages with conversation history
        messages = [SystemMessage(content=self.SYSTEM_PROMPT)]

        # Add conversation history if available
        if conversation_history:
            logger.info(f"🔗 [LLM] Including {len(conversation_history)} previous messages in context for multi-turn conversation")
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        else:
            logger.info(f"🔗 [LLM] No conversation history - processing as single-turn query")

        # Add current query
        messages.append(HumanMessage(content=user_prompt))

        response = self.llm.invoke(messages)
        answer = response.content

        # Extract citations
        citations = self._extract_citations_from_chunks(evidence_chunks)

        logger.info(f"Generated answer with {len(citations)} citations")

        return answer, citations

    async def generate_stream(
        self,
        query: str,
        evidence_chunks: List[Chunk],
        intent: str = "general",
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncIterator[str]:
        """Generate answer with streaming.

        Args:
            query: User query
            evidence_chunks: Evidence chunks from retrieval
            intent: Query intent for context
            conversation_history: Previous messages [{"role": "user"|"assistant", "content": "..."}]

        Yields:
            Answer chunks as they're generated
        """
        logger.info(f"Generating streaming answer for query: {query[:100]}...")

        if not evidence_chunks:
            yield "I don't have sufficient information in the Medicare handbook to answer this question accurately."
            return

        # Format evidence
        evidence_text = self._format_evidence(evidence_chunks)

        # Create prompt
        user_prompt = f"""User Question: {query}

Intent: {intent}

Evidence from Medicare Handbook 2026:
{evidence_text}

Based ONLY on the evidence provided above, answer the user's question. Remember to:
- Cite sources using [Section > Page X] format
- Use conservative language
- Never make claims without evidence
- State if information is insufficient"""

        # Build messages with conversation history
        messages = [SystemMessage(content=self.SYSTEM_PROMPT)]

        # Add conversation history if available
        if conversation_history:
            logger.info(f"🔗 [LLM STREAMING] Including {len(conversation_history)} previous messages in context for multi-turn conversation")
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        else:
            logger.info(f"🔗 [LLM STREAMING] No conversation history - processing as single-turn query")

        # Add current query
        messages.append(HumanMessage(content=user_prompt))

        async for chunk in self.streaming_llm.astream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                yield chunk.content

    def expand_query(self, query: str) -> str:
        """Expand query with Medicare-specific terminology.

        Args:
            query: Original user query

        Returns:
            Expanded query with Medicare terminology
        """
        expansion_prompt = f"""Expand this Medicare question by adding relevant Medicare terms and synonyms to improve search results.
Include official Medicare terminology, related concepts, and alternative phrasings.

Examples:
- "enrollment" → "enrollment, enroll, sign up, registration, initial enrollment period, IEP, general enrollment period"
- "penalty" → "penalty, late enrollment penalty, premium surcharge, additional cost"
- "Part B" → "Part B, Medicare Part B, medical insurance"

Original question: {query}

Expanded query with synonyms and related terms (2-3 sentences max):"""

        messages = [
            SystemMessage(content="You are a Medicare terminology expert. Expand queries to include synonyms and related Medicare terms for better search coverage."),
            HumanMessage(content=expansion_prompt)
        ]

        response = self.fast_llm.invoke(messages)
        expanded = response.content.strip()

        logger.info(f"Expanded query: {expanded}")
        return expanded

    def classify_intent(self, query: str) -> str:
        """Classify query intent.

        Args:
            query: User query

        Returns:
            Intent classification
        """
        classification_prompt = f"""Classify this Medicare question into ONE category:
- penalty: Late enrollment penalties, premium increases
- cost: Costs, premiums, deductibles, IRMAA
- enrollment: Enrollment periods, signing up
- coverage: What's covered, benefits
- eligibility: Who qualifies, requirements
- comparison: Comparing plans or parts
- procedure: How to do something
- exception: Special cases, exceptions
- general: Other

Question: {query}

Category:"""

        messages = [
            SystemMessage(content="You are a Medicare query classifier."),
            HumanMessage(content=classification_prompt)
        ]

        response = self.fast_llm.invoke(messages)
        intent = response.content.strip().lower()

        # Validate intent
        valid_intents = [
            "penalty", "cost", "enrollment", "coverage",
            "eligibility", "comparison", "procedure", "exception", "general"
        ]

        if intent not in valid_intents:
            intent = "general"

        logger.info(f"Classified intent: {intent}")
        return intent
