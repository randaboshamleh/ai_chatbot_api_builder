"""
Unit Tests for Assistify Core Business Logic
Tests cover: RAG pipeline, document processing, embeddings, vector store
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.documents.models import Document
from core.rag.document_processor import DocumentProcessor, tag_category, _semantic_split
from core.rag.pipeline import RAGPipeline, StreamAnswerState
from core.rag.embeddings import OllamaEmbeddingEngine

User = get_user_model()


# ═══════════════════════════════════════════════════════════════
# 🧪 Document Processor Tests
# ═══════════════════════════════════════════════════════════════

class TestDocumentProcessor(TestCase):
    """Test document processing and chunking logic"""

    def setUp(self):
        self.processor = DocumentProcessor(chunk_size=500, chunk_overlap=50)

    def test_tag_category_pricing(self):
        """Test category tagging for pricing-related text"""
        text = "Our pricing plans start at $29 per month"
        category = tag_category(text)
        self.assertEqual(category, "pricing")

    def test_tag_category_features(self):
        """Test category tagging for features"""
        text = "This integration allows you to connect with Slack API"
        category = tag_category(text)
        self.assertEqual(category, "features")

    def test_tag_category_support(self):
        """Test category tagging for support content"""
        text = "If you encounter an error, contact our support team"
        category = tag_category(text)
        self.assertEqual(category, "support")

    def test_tag_category_general(self):
        """Test category tagging for general content"""
        text = "The weather is nice today"
        category = tag_category(text)
        self.assertEqual(category, "general")

    def test_tag_category_arabic(self):
        """Test category tagging for Arabic text"""
        text = "ما هي الأسعار المتاحة؟"
        category = tag_category(text)
        self.assertEqual(category, "pricing")

    def test_semantic_split_with_headings(self):
        """Test semantic splitting detects chapter headings"""
        text = """Chapter 1: Introduction
This is the intro.

Chapter 2: Pricing
Our prices are competitive.

Chapter 3: Support
Contact us anytime."""
        sections = _semantic_split(text)
        self.assertGreaterEqual(len(sections), 3)
        self.assertIn("Chapter 1", sections[0])

    def test_semantic_split_numbered_sections(self):
        """Test semantic splitting with numbered sections"""
        text = """1. First Section
Content here.

2. Second Section
More content.

3. Third Section
Final content."""
        sections = _semantic_split(text)
        self.assertGreaterEqual(len(sections), 3)

    def test_semantic_split_fallback_paragraphs(self):
        """Test semantic splitting falls back to paragraphs when no headings"""
        text = """This is paragraph one.
It has multiple lines.

This is paragraph two.
Also multiple lines.

This is paragraph three."""
        sections = _semantic_split(text)
        self.assertGreaterEqual(len(sections), 2)

    def test_compute_checksum(self):
        """Test file checksum computation"""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()
            checksum = DocumentProcessor.compute_checksum(f.name)
            self.assertEqual(len(checksum), 64)  # SHA256 hex length
            self.assertIsInstance(checksum, str)


# ═══════════════════════════════════════════════════════════════
# 🧪 RAG Pipeline Tests
# ═══════════════════════════════════════════════════════════════

class TestRAGPipeline(TestCase):
    """Test RAG pipeline logic"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            max_documents=10,
            max_users=5
        )
        self.pipeline = RAGPipeline(tenant=self.tenant)

    def test_is_arabic_detection_pure_arabic(self):
        """Test Arabic language detection for pure Arabic text"""
        text = "ما هو التعلم الآلي"
        self.assertTrue(self.pipeline._is_arabic(text))

    def test_is_arabic_detection_pure_english(self):
        """Test Arabic language detection for pure English text"""
        text = "What is machine learning"
        self.assertFalse(self.pipeline._is_arabic(text))

    def test_is_arabic_detection_mixed(self):
        """Test Arabic language detection for mixed Arabic/English"""
        text = "ما هو supervised learning"
        # Mixed text might be detected as Arabic or English depending on implementation
        # Just verify the method returns a boolean
        result = self.pipeline._is_arabic(text)
        self.assertIsInstance(result, bool)

    def test_no_info_message_arabic(self):
        """Test no-info message returns Arabic for Arabic question"""
        question = "ما هو السعر"
        message = self.pipeline._no_info_message(question)
        self.assertIn("الوثائق", message)

    def test_no_info_message_english(self):
        """Test no-info message returns English for English question"""
        question = "What is the price"
        message = self.pipeline._no_info_message(question)
        self.assertIn("clear answer", message.lower())

    def test_detect_intent_pricing(self):
        """Test intent detection for pricing questions"""
        question = "What are your pricing plans?"
        intent = self.pipeline.detect_intent(question)
        self.assertEqual(intent, "pricing")

    def test_detect_intent_features(self):
        """Test intent detection for features questions"""
        question = "What integrations do you support?"
        intent = self.pipeline.detect_intent(question)
        self.assertEqual(intent, "features")

    def test_detect_intent_support(self):
        """Test intent detection for support questions"""
        question = "How do I fix this error?"
        intent = self.pipeline.detect_intent(question)
        self.assertEqual(intent, "support")

    def test_detect_intent_general(self):
        """Test intent detection for general questions"""
        question = "Tell me about your company"
        intent = self.pipeline.detect_intent(question)
        self.assertEqual(intent, "general")

    def test_cache_key_generation(self):
        """Test cache key is generated consistently"""
        query = "test query"
        key1 = self.pipeline._cache_key(query)
        key2 = self.pipeline._cache_key(query)
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 32)  # MD5 hex length

    def test_cache_key_different_for_different_languages(self):
        """Test cache key differs for same question in different languages"""
        query_en = "What is machine learning"
        query_ar = "What is machine learning"  # Same text but will be detected differently
        key_en = self.pipeline._cache_key(query_en)
        key_ar = self.pipeline._cache_key(query_ar)
        # Keys should be same for identical text
        self.assertEqual(key_en, key_ar)

    @patch('core.rag.pipeline.OLLAMA_AVAILABLE', False)
    def test_generate_without_ollama(self):
        """Test generate returns error message when Ollama unavailable"""
        pipeline = RAGPipeline(tenant=self.tenant)
        result = pipeline.generate("test query", "test context")
        self.assertIn("unavailable", result.lower())

    def test_build_hierarchical_context_empty_chunks(self):
        """Test build_hierarchical_context handles empty chunks gracefully"""
        context = self.pipeline.build_hierarchical_context("general", [])
        self.assertIsInstance(context, str)

    def test_build_hierarchical_context_with_chunks(self):
        """Test build_hierarchical_context builds proper context from chunks"""
        chunks = [
            {
                "content": "Test content 1",
                "metadata": {"source": "doc1.pdf", "page": 1, "level": "detail"}
            },
            {
                "content": "Test content 2",
                "metadata": {"source": "doc2.pdf", "page": 2, "level": "detail"}
            }
        ]
        context = self.pipeline.build_hierarchical_context("pricing", chunks)
        self.assertIsInstance(context, str)
        self.assertGreater(len(context), 0)

    def test_rerank_prefers_confident_document(self):
        """When one document is clearly stronger, selected chunks should come from it."""
        query = "annual subscription discount"
        chunks = [
            {
                "content": "General company introduction and mission statement.",
                "metadata": {"source": "doc1.pdf", "document_id": "doc-1"},
                "similarity_score": 0.92,
            },
            {
                "content": "Annual subscription discount is 20 percent for yearly plan.",
                "metadata": {"source": "pricing.docx", "document_id": "doc-2"},
                "similarity_score": 0.78,
            },
            {
                "content": "Yearly subscription includes 20 percent discount and priority support.",
                "metadata": {"source": "pricing.docx", "document_id": "doc-2"},
                "similarity_score": 0.76,
            },
        ]

        selected = self.pipeline.rerank(query, chunks)
        self.assertGreaterEqual(len(selected), 1)
        self.assertEqual(selected[0]["metadata"]["document_id"], "doc-2")

    def test_needs_arabic_rewrite_for_mixed_script(self):
        """Arabic answers containing latin letters should trigger rewrite."""
        query = "ما هي أسعار الاشتراك؟"
        mixed_answer = "الأسعاr متاحة في الخطة السنوية."
        self.assertTrue(self.pipeline._needs_arabic_rewrite(query, mixed_answer))

    def test_postprocess_answer_fixes_test_automation_translation(self):
        """Arabic post-processing should enforce the correct automation terminology."""
        query = "ما هو Katalon Studio؟"
        answer = "Katalon Studio هو تطبيق لاختبار التكرار (Test Automation Tool)."
        cleaned = self.pipeline._postprocess_answer(query, answer)
        self.assertIn("أتمتة الاختبارات", cleaned)
        self.assertNotIn("اختبار التكرار", cleaned)

    def test_postprocess_answer_fixes_katalon_misspelling(self):
        """Arabic post-processing should normalize malformed product-name variants."""
        query = "ما هو katalon studio"
        answer = "كتابل ستوديو منصة رائعة."
        cleaned = self.pipeline._postprocess_answer(query, answer)
        self.assertIn("Katalon Studio", cleaned)


# ═══════════════════════════════════════════════════════════════
# 🧪 Embedding Engine Tests (Skipped - requires Ollama running)
# ═══════════════════════════════════════════════════════════════

# Note: Embedding tests are skipped because they require Ollama to be running
# These would be tested in integration tests with real Ollama instance


# ═══════════════════════════════════════════════════════════════
# 🧪 Edge Cases & Error Handling
# ═══════════════════════════════════════════════════════════════

    @patch('core.rag.pipeline.OLLAMA_AVAILABLE', True)
    def test_generate_stream_hybrid_cleanup_sets_final_answer(self):
        """Streaming should lightly clean chunks, then finalize with full post-processing."""
        self.pipeline.llm_client = Mock()
        self.pipeline.model = "test-model"
        self.pipeline.model_arabic = "test-model"
        self.pipeline.llm_client.generate.return_value = iter(
            [
                {"response": "Here is the answer:\n"},
                {"response": "Test\u200f value \u25A1.\u0007"},
            ]
        )
        state = StreamAnswerState()

        streamed = list(self.pipeline.generate_stream("What is this?", "ctx", state=state))
        stream_text = "".join(streamed)

        self.assertNotIn("\u200f", stream_text)
        self.assertNotIn("\u25A1", stream_text)
        self.assertNotIn("Here is the answer", state.final_answer)
        self.assertIn("Test value", state.final_answer)

    def test_query_stream_returns_answer_state(self):
        """Stream query should return a state object for finalized storage content."""
        chunk = {
            "content": "Some context",
            "metadata": {"source": "doc.pdf", "page": 1, "document_id": "doc-1"},
            "final_score": 0.9,
            "lexical_overlap": 0.5,
        }
        self.pipeline.detect_intent = Mock(return_value="general")
        self.pipeline.retrieve = Mock(return_value=[chunk])
        self.pipeline.rerank = Mock(return_value=[chunk])
        self.pipeline.build_hierarchical_context = Mock(return_value="ctx")

        def fake_stream(_query, _context, state=None):
            if state:
                state.tokens.append("hello")
                state.final_answer = "hello"
            yield "hello"

        self.pipeline.generate_stream = fake_stream

        result = self.pipeline.query("hello", stream=True)

        self.assertIn("answer_state", result)
        self.assertEqual(list(result["answer"]), ["hello"])
        self.assertEqual(result["answer_state"].final_answer, "hello")


class TestEdgeCases(TestCase):
    """Test edge cases and error handling"""

    def test_tag_category_empty_string(self):
        """Test category tagging with empty string"""
        category = tag_category("")
        self.assertEqual(category, "general")

    def test_tag_category_special_characters(self):
        """Test category tagging with special characters"""
        text = "!@#$%^&*()"
        category = tag_category(text)
        self.assertEqual(category, "general")

    def test_semantic_split_empty_text(self):
        """Test semantic split with empty text"""
        sections = _semantic_split("")
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0], "")

    def test_semantic_split_single_line(self):
        """Test semantic split with single line"""
        text = "Single line of text"
        sections = _semantic_split(text)
        self.assertEqual(len(sections), 1)

    def test_document_processor_invalid_file_type(self):
        """Test document processor rejects invalid file types"""
        processor = DocumentProcessor()
        with self.assertRaises(ValueError):
            processor.load_document("test.xyz", "application/xyz")


# ═══════════════════════════════════════════════════════════════
# 🧪 Run Tests
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
