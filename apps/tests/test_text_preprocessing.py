from django.test import SimpleTestCase

from core.rag.text_preprocessing import (
    normalize_document_text,
    normalize_for_search,
    normalize_user_query,
    sanitize_generated_answer,
)


class TextPreprocessingTests(SimpleTestCase):
    def test_normalize_user_query_collapses_noise(self):
        value = normalize_user_query(" \u200f\u0645\u0627   \u0647\u064A   any   query\ttext\u061F\u061F  ")
        self.assertEqual(value, "\u0645\u0627 \u0647\u064A any query text\u061F")

    def test_normalize_for_search_arabic_variants(self):
        left = normalize_for_search("\u0625\u062E\u062A\u0628\u0627\u0631 \u0627\u0644\u0623\u062A\u0645\u062A\u0629")
        right = normalize_for_search("\u0627\u062E\u062A\u0628\u0627\u0631 \u0627\u0644\u0627\u062A\u0645\u062A\u0629")
        self.assertEqual(left, right)

    def test_normalize_document_text_removes_ocr_header_noise(self):
        raw = "1\n\n  \n=====\n\nOracle Security Guide\n\n2\n"
        cleaned = normalize_document_text(raw)
        self.assertIn("Oracle Security Guide", cleaned)
        self.assertNotIn("=====", cleaned)

    def test_sanitize_generated_answer_strips_meta_lines(self):
        question = "What is the answer?"
        answer = (
            "Here is the answer:\n"
            "NOTE: this is generated.\n"
            "The main point is access control."
        )
        cleaned = sanitize_generated_answer(question, answer)
        self.assertNotIn("Here is the answer", cleaned)
        self.assertNotIn("NOTE:", cleaned)
        self.assertIn("access control", cleaned)

    def test_sanitize_generated_answer_removes_cyrillic_noise_for_arabic(self):
        question = "\u0645\u0627 \u0647\u064A \u0627\u0644\u062E\u0644\u0627\u0635\u0629\u061F"
        answer = "\u0647\u0630\u0627 \u0646\u0635 \u062A\u062C\u0631\u064A\u0628\u064A \u043F\u0440\u0438\u0432\u0435\u0442."
        cleaned = sanitize_generated_answer(question, answer)
        self.assertNotRegex(cleaned, r"[\u0400-\u04FF]")

    def test_sanitize_generated_answer_trims_incomplete_tail(self):
        question = "List the steps"
        answer = "Step one completed. Step two completed. Step three is"
        cleaned = sanitize_generated_answer(question, answer)
        self.assertTrue(cleaned.endswith("."))
        self.assertNotIn("Step three is", cleaned)

    def test_sanitize_generated_answer_keeps_technical_terms_as_is(self):
        question = "\u0645\u0627 \u0647\u0648 Katalon Studio\u061F"
        answer = "Katalon Studio is a Test Automation Tool."
        cleaned = sanitize_generated_answer(question, answer)
        self.assertIn("Katalon Studio", cleaned)
        self.assertIn("Test Automation Tool", cleaned)

    def test_sanitize_generated_answer_removes_based_on_documents_prefix(self):
        question = "\u0645\u0627 \u0647\u0648 Katalon Studio\u061F"
        answer = "\u0628\u062d\u0633\u0628 \u0627\u0644\u0648\u062b\u0627\u0626\u0642 \u0627\u0644\u0645\u062a\u0627\u062d\u0629: Katalon Studio \u0623\u062f\u0627\u0629 \u0623\u062a\u0645\u062a\u0629."
        cleaned = sanitize_generated_answer(question, answer)
        self.assertFalse(cleaned.startswith("\u0628\u062d\u0633\u0628 \u0627\u0644\u0648\u062b\u0627\u0626\u0642"))
        self.assertIn("Katalon Studio", cleaned)

    def test_sanitize_generated_answer_repairs_spaced_latin_noise(self):
        question = "what is katalon studio"
        answer = "SO FTW ARE TESTIN G \u25A1 KATALON STUDIO"
        cleaned = sanitize_generated_answer(question, answer)
        self.assertIn("SOFTWARE", cleaned)
        self.assertIn("TESTING", cleaned)
        self.assertNotIn("\u25A1", cleaned)
