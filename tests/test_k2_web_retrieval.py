"""
Unit tests for K-2 Temporal Web Retrieval module and engine integration.
"""

import unittest
from src.ai_core.layers.k2_web_retrieval import TemporalWebRetriever, BLACKLIST_DOMAINS, WHITELIST_DOMAINS
from src.ai_core.engine.engine import KizilelmaEngine


class TestTemporalWebRetrieval(unittest.TestCase):

    def setUp(self):
        self.retriever = TemporalWebRetriever(request_timeout=5, max_search_results=3)

    def test_query_cleaning(self):
        claim = "Acaba Türkiye uzay misyonu için ne zaman fırlatma yapıldı?"
        clean_q = self.retriever.extract_clean_query(claim)
        self.assertTrue(len(clean_q) > 0)
        self.assertNotIn("acaba", clean_q.lower())

    def test_blacklist_filtering(self):
        for b in BLACKLIST_DOMAINS:
            url = f"https://www.{b}/haber/12345"
            self.assertTrue(self.retriever.is_blacklisted(url), f"Should blacklist {b}")

    def test_whitelist_authority(self):
        auth_aa = self.retriever.get_domain_authority("https://www.aa.com.tr/tr/gundem/test")
        auth_gov = self.retriever.get_domain_authority("https://www.resmigazete.gov.tr/falan")
        self.assertGreaterEqual(auth_aa, 0.90)
        self.assertGreaterEqual(auth_gov, 0.95)

    def test_engine_mixin_structure(self):
        engine = KizilelmaEngine(lazy_load=True)
        # Verify text heuristics mixin methods
        self.assertTrue(hasattr(engine, "akilli_fark_analizi"))
        self.assertTrue(hasattr(engine, "kelime_capasi_kontrolu"))
        self.assertTrue(hasattr(engine, "intent_analyzer"))
        # Verify knowledge store mixin methods
        self.assertTrue(hasattr(engine, "sync_db"))
        self.assertTrue(hasattr(engine, "inject_knowledge"))
        # Verify response generator mixin methods
        self.assertTrue(hasattr(engine, "local_response_engine"))
        self.assertTrue(hasattr(engine, "detect_source_channel"))
        # Verify web retrieval fallback
        self.assertTrue(hasattr(engine, "_try_web_retrieval"))


if __name__ == "__main__":
    unittest.main()
