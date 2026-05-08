"""
Parsers for different source types: Law, CourtPractice, Plenum, Template, FAQ.
"""

import re
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class ParsedDocument:
    """Result of parsing a document."""
    source_type: str
    title: str
    sections: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    raw_text: str


class BaseParser:
    """Base class for parsers."""
    def parse(self, text: str, **kwargs) -> ParsedDocument:
        raise NotImplementedError


class LawParser(BaseParser):
    """Parser for legal texts (ФЗ, Кодексы)."""
    def parse(self, text: str, **kwargs) -> ParsedDocument:
        # Simplified parsing: split by articles
        sections = []
        article_pattern = r"(Статья\s+\d+[\.\s]*(?:\w+\s*)*)"
        matches = list(re.finditer(article_pattern, text, re.IGNORECASE | re.MULTILINE))
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sections.append({
                "type": "article",
                "heading": match.group(1).strip(),
                "content": text[start:end].strip(),
                "metadata": {"article_number": i + 1}
            })
        return ParsedDocument(
            source_type="law",
            title=kwargs.get("title", "Unknown Law"),
            sections=sections,
            metadata={"parser": "LawParser"},
            raw_text=text[:5000]  # limit
        )


class CourtPracticeParser(BaseParser):
    """Parser for court decisions."""
    def parse(self, text: str, **kwargs) -> ParsedDocument:
        sections = [{
            "type": "decision",
            "heading": "Court Decision",
            "content": text,
            "metadata": {"court": kwargs.get("court", "unknown")}
        }]
        return ParsedDocument(
            source_type="court_practice",
            title=kwargs.get("title", "Court Decision"),
            sections=sections,
            metadata={"parser": "CourtPracticeParser"},
            raw_text=text[:5000]
        )


class PlenumParser(BaseParser):
    """Parser for Plenum resolutions."""
    def parse(self, text: str, **kwargs) -> ParsedDocument:
        sections = [{
            "type": "plenum",
            "heading": "Plenum Resolution",
            "content": text,
            "metadata": {"number": kwargs.get("number")}
        }]
        return ParsedDocument(
            source_type="plenum",
            title=kwargs.get("title", "Plenum Resolution"),
            sections=sections,
            metadata={"parser": "PlenumParser"},
            raw_text=text[:5000]
        )


class TemplateParser(BaseParser):
    """Parser for document templates."""
    def parse(self, text: str, **kwargs) -> ParsedDocument:
        sections = [{
            "type": "template",
            "heading": "Template",
            "content": text,
            "metadata": {"category": kwargs.get("category")}
        }]
        return ParsedDocument(
            source_type="template",
            title=kwargs.get("title", "Document Template"),
            sections=sections,
            metadata={"parser": "TemplateParser"},
            raw_text=text[:5000]
        )


class FAQParser(BaseParser):
    """Parser for FAQ (question-answer pairs)."""
    def parse(self, text: str, **kwargs) -> ParsedDocument:
        # Simple Q/A detection
        qa_pattern = r"(Q:|Вопрос:|Question:)\s*(.*?)\s*(A:|Ответ:|Answer:)\s*(.*?)(?=(?:\n\n|$))"
        sections = []
        for match in re.finditer(qa_pattern, text, re.DOTALL | re.IGNORECASE):
            sections.append({
                "type": "qa",
                "heading": match.group(2).strip(),
                "content": match.group(4).strip(),
                "metadata": {}
            })
        if not sections:
            sections.append({
                "type": "faq",
                "heading": "FAQ",
                "content": text,
                "metadata": {}
            })
        return ParsedDocument(
            source_type="faq",
            title=kwargs.get("title", "FAQ"),
            sections=sections,
            metadata={"parser": "FAQParser"},
            raw_text=text[:5000]
        )


def get_parser(source_type: str) -> BaseParser:
    """Factory function to get appropriate parser."""
    parsers = {
        "law": LawParser(),
        "court_practice": CourtPracticeParser(),
        "plenum": PlenumParser(),
        "template": TemplateParser(),
        "faq": FAQParser(),
    }
    return parsers.get(source_type, BaseParser())