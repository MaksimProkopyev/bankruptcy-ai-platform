"""
Query processor: NER, classification, synonyms, case context.
"""

import re
from typing import Dict, Any, List, Optional
from rag.models import ProcessedQuery


class QueryProcessor:
    """Processes natural language queries for retrieval."""

    def __init__(self):
        # Predefined synonyms for legal terms
        self.synonyms = {
            "банкротство": ["несостоятельность", "финансовая несостоятельность"],
            "кредитор": ["займодавец", "взыскатель"],
            "должник": ["заёмщик", "дебитор"],
            "реструктуризация": ["реорганизация долга", "пересмотр условий"],
            "арбитражный суд": ["суд по банкротству", "экономический суд"],
        }

    async def process(
        self,
        query: str,
        case_context: Optional[Dict[str, Any]] = None,
    ) -> ProcessedQuery:
        """Process a query."""
        normalized = self._normalize(query)
        entities = self._extract_entities(normalized)
        classification = self._classify(normalized)
        synonyms = self._expand_synonyms(normalized)

        return ProcessedQuery(
            original_query=query,
            normalized_query=normalized,
            entities=entities,
            classification=classification,
            synonyms=synonyms,
            case_context=case_context,
        )

    def _normalize(self, text: str) -> str:
        """Normalize text: lowercasing, remove extra spaces, etc."""
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract simple entities (mock implementation)."""
        entities = []
        # Look for amounts
        amount_pattern = r"(\d+(?:[.,]\d+)?)\s*(тыс|млн|миллион|миллиард)?\s*(руб|₽|долл|€)"
        for match in re.finditer(amount_pattern, text):
            entities.append({
                "type": "amount",
                "text": match.group(0),
                "value": match.group(1),
                "unit": match.group(3) or "руб",
            })
        # Look for legal terms
        legal_terms = ["банкротство", "суд", "кредитор", "должник", "иск", "заявление"]
        for term in legal_terms:
            if term in text:
                entities.append({
                    "type": "legal_term",
                    "text": term,
                    "value": term,
                })
        return entities

    def _classify(self, text: str) -> str:
        """Classify query into a category."""
        categories = {
            "law": ["статья", "закон", "фз", "кодекс"],
            "procedure": ["как", "процедура", "этап", "срок"],
            "cost": ["стоимость", "цена", "сколько стоит", "оплата"],
            "eligibility": ["могу ли", "имею ли право", "условия"],
            "court": ["суд", "заседание", "решение", "определение"],
        }
        for cat, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return cat
        return "general"

    def _expand_synonyms(self, text: str) -> List[str]:
        """Expand query with synonyms."""
        expanded = []
        words = text.split()
        for word in words:
            if word in self.synonyms:
                expanded.extend(self.synonyms[word])
        return expanded