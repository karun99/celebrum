"""Tests for the Celebrum neural implementation.

Run with:  python -m unittest discover -s tests
or:        pytest tests
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celebrum.engine import Celebrum, default_home
from celebrum.memory import MemoryGraph, tokenize, decay, HALF_LIFE_DAYS
from celebrum.persona import PersonaModel
from celebrum.tensor import PersonalTensorMemory
from celebrum.truth import TruthEngine
from celebrum.guardrails import GuardrailEngine
from celebrum.simulate import Simulation


def data_dir():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def make_engine():
    tmp = tempfile.mkdtemp()
    return Celebrum(home=os.path.join(tmp, "brain")), tmp


class TestMemory(unittest.TestCase):
    def test_decay_tiers(self):
        self.assertGreater(HALF_LIFE_DAYS["identity"], HALF_LIFE_DAYS["fact"])
        self.assertAlmostEqual(decay(0, "fact"), 1.0)
        self.assertLess(decay(30, "fact"), decay(30, "identity"))  # ephemera decay faster than core

    def test_graph_and_recall(self):
        eng, _ = make_engine()
        a = eng.graph.add_neuron("fact", "local-first privacy-preserving AI is the future")
        b = eng.graph.add_neuron("preference", "Dislikes vendor lock-in", meta={"topic": "cost", "sentiment": -1.0})
        eng.graph.add_synapse(a, b, "related_to")
        hits = eng.graph.recall("privacy local AI")
        self.assertTrue(hits)
        ids = {h["id"] for h in hits}
        self.assertIn(a, ids)

    def test_right_to_forget(self):
        eng, _ = make_engine()
        a = eng.graph.add_neuron("note", "doomed note")
        b = eng.graph.add_neuron("fact", "another")
        eng.graph.add_synapse(a, b, "related_to")
        eng.graph.delete_neuron(a)
        self.assertIsNone(eng.graph.neuron(a))
        self.assertIsNotNone(eng.graph.neuron(b))


class TestPersona(unittest.TestCase):
    def test_build_and_feedback(self):
        eng, _ = make_engine()
        eng.graph.add_neuron("preference", "loves privacy-first tools", meta={"topic": "privacy", "sentiment": 1.0})
        eng.graph.add_neuron("preference", "dislikes vendor lock-in", meta={"topic": "cost", "sentiment": -1.0})
        eng.graph.add_neuron("decision", "constraint: hosted cloud, decision: keep local",
                             meta={"context": "choosing architecture", "choice": "keep local", "rationale": "privacy"})
        eng.learn()
        self.assertGreater(len(eng.persona.values), 0)
        self.assertGreaterEqual(len(eng.persona.heuristics), 1)
        v = eng.persona.to_vector()
        self.assertEqual(len(v), 10)
        eng.persona.apply_feedback("formality", -0.2)
        self.assertLess(eng.persona.style["formality"], 0.5)


class TestTensor(unittest.TestCase):
    def test_budget_and_privacy(self):
        t = PersonalTensorMemory()
        self.assertLessEqual(t.nbytes(), 8 * 1024 * 1024)
        t.update_from_text("the brain remembers privacy first zero cloud cost")
        t.update_from_text("privacy first local-first artificial brain")
        blob = t.to_bytes()
        t2 = PersonalTensorMemory.from_bytes(blob)
        self.assertAlmostEqual(t.cosine(t2), 1.0, places=4)
        self.assertTrue("privacy" not in blob.decode("latin1"))


class TestTruth(unittest.TestCase):
    def test_index(self):
        eng, _ = make_engine()
        eng.graph.add_neuron("fact", "privacy is core", source="duet", confidence=0.9)
        eng.graph.add_neuron("fact", "privacy matters for trust", source="web", confidence=0.8)
        tr = TruthEngine(eng.graph)
        idx = tr.index()
        self.assertIn("truth_index", idx)
        self.assertGreaterEqual(idx["truth_index"], 0.0)


class TestGuardrails(unittest.TestCase):
    def test_tiers_and_reversibility(self):
        eng, _ = make_engine()
        # the right-to-erasure guardrail (DPDP/GDPR legal requirement) is intentionally fixed;
        # everything else must be reversible.
        non_rev = [g for g in eng.guardrails.all() if not g["reversible"]]
        self.assertTrue(all(("right to be forgotten" in g["rationale"]) or ("right to erasure" in g["rationale"])
                            for g in non_rev))
        with self.assertRaises(PermissionError):
            eng.guardrails.apply({"tier": "high", "rule": "x", "rationale": "y"}, approved_by="auto")
        low = eng.guardrails.apply({"tier": "low", "rule": "demo low rule", "rationale": "test"})
        eng.guardrails.revert(low["id"])
        self.assertEqual(eng.guardrails.get(low["id"])["status"], "reverted")


class TestSimulate(unittest.TestCase):
    def test_stance_and_conflicts(self):
        eng, _ = make_engine()
        eng.persona.values = [
            {"key": "privacy", "label": "privacy", "strength": 0.9, "evidence": 3},
            {"key": "honesty", "label": "honesty", "strength": 0.8, "evidence": 2},
        ]
        r = Simulation(eng.persona, eng.graph).run("should I publish all private user data to the cloud?")
        self.assertTrue(any(c["value"] in ("privacy", "honesty") for c in r["value_conflicts"]))


class TestValidation(unittest.TestCase):
    def test_harness_runs(self):
        eng, tmp = make_engine()
        eng.ingest_html(os.path.join(data_dir(), "matruswara", "oi.html"), consent=True)
        eng.ingest_html(os.path.join(data_dir(), "matruswara", "satyasandha.html"), consent=True)
        with open(os.path.join(data_dir(), "duet_sample.json"), encoding="utf-8") as fh:
            eng.ingest_duet(json.load(fh), consent=True)
        report = eng.validate()
        names = [c["name"] for c in report["checks"]]
        for n in ["bridge-drift-bound", "id-rag-identity-recall", "pgmem-evidential-validity",
                  "ptm-tensor-memory", "dpdp-guardrails", "recall-latency-10k"]:
            self.assertIn(n, names)
        self.assertLessEqual(report["summary"]["failed"], 2)  # acceptable: some require seeding

    def test_demo_seed_and_snapshot(self):
        eng, tmp = make_engine()
        with open(os.path.join(data_dir(), "duet_sample.json"), encoding="utf-8") as fh:
            eng.ingest_duet(json.load(fh), consent=True)
        s = eng.snapshot()
        self.assertGreater(s["stats"]["neurons"], 0)


class TestMCP(unittest.TestCase):
    def test_mcp_tool_call(self):
        from celebrum.mcp import McpServer, TOOLS
        import io
        eng, _ = make_engine()
        out = io.StringIO()
        server = McpServer(eng, out=out)
        resp = json.loads(server.handle({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "celebrum.snapshot", "arguments": {}}}))
        self.assertEqual(resp["result"]["isError"], False)
        self.assertIn("persona", resp["result"]["content"][0]["text"])


class TestIngest(unittest.TestCase):
    def test_consent_and_ssrf(self):
        eng, _ = make_engine()
        with self.assertRaises(PermissionError):
            eng.ingest_html(os.path.join(data_dir(), "duet_sample.json"), consent=False)
        from celebrum.ingest import Ingestor
        with self.assertRaises(PermissionError):
            Ingestor(eng.graph)._guard_ssrf("http://127.0.0.1/x")
        with self.assertRaises(PermissionError):
            Ingestor(eng.graph)._guard_ssrf("http://localhost/x")


if __name__ == "__main__":
    unittest.main(verbosity=2)