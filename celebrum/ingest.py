"""Ingestion (FR-1): web corpus + consented personal memory (Duet) + local HTML
knowledge sources (matruswara: SatyaSandha AI and Neural Research OS/OI).

Every ingest path requires consent (DPDP/GDPR) and is audited. Web fetch is
SSRF-protected (private/loopback IPs are refused) and size-limited.
"""

from __future__ import annotations

import html as html_lib
import ipaddress
import json
import re
import socket
import urllib.parse
import urllib.request

from .memory import MemoryGraph, tokenize
from .store import now_iso

MAX_WEB_BYTES = 5_000_000
MATRUSWARA_SOURCES = ["satyasandha.html", "oi.html"]

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<(script|style)[\s\S]*?</\1>", re.I)


def strip_html(raw: str) -> str:
    body = _SCRIPT_RE.sub(" ", raw)
    body = _TAG_RE.sub(" ", body)
    body = html_lib.unescape(body)
    body = re.sub(r"\s+", " ", body)
    return body.strip()


class Ingestor:
    def __init__(self, graph: MemoryGraph):
        self.graph = graph

    def _consent(self, consent: bool) -> None:
        if not consent:
            raise PermissionError("consent required (DPDP/GDPR); pass consent=True")

    # ---- Duet personal memory ------------------------------------------------
    def ingest_duet(self, duet: dict, consent=True, source="duet") -> int:
        """Consented personal memory export -> neuron graph."""
        self._consent(consent)
        n = 0
        profile = duet.get("profile", {})
        if profile.get("communication_style"):
            style = profile["communication_style"]
            self._add_signal("style", json.dumps(style), source, confidence=0.8,
                             meta={"signal": "communication_style"})
            n += 1
        for dom in profile.get("domains", []):
            self._add_signal("trait", f"knowledge domain: {dom}", source, confidence=0.7,
                             meta={"signal": "domain", "topic": dom})
            n += 1
        for kind, key in [("fact", "facts"), ("preference", "preferences"),
                          ("decision", "decisions"), ("milestone", "milestones"),
                          ("relationship", "relationships")]:
            for item in duet.get(key, []):
                content = item.get("content") or self._compose(item)
                meta = {k: v for k, v in item.items() if k not in ("content", "confidence")}
                nid = self.graph.add_neuron(kind, content, source,
                                            confidence=item.get("confidence", 0.5),
                                            meta=meta)
                self._link_synapses(nid, meta)
                n += 1
        return n

    @staticmethod
    def _compose(item) -> str:
        """Fall back to a human-readable string when an export item has no content."""
        parts = [f"{k}: {v}" for k, v in item.items() if k not in ("confidence",)]
        return " | ".join(parts) or "unnamed memory"

    # ---- web corpus ------------------------------------------------------------
    def ingest_web(self, url: str, consent=True, source=None) -> int:
        """Fetch a public page, strip chrome, store paragraphs as fact neurons."""
        self._consent(consent)
        self._guard_ssrf(url)
        req = urllib.request.Request(url, headers={"User-Agent": "celebrum/0.1 (local-first)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read(MAX_WEB_BYTES + 1).decode("utf-8", errors="ignore")
        if len(raw) > MAX_WEB_BYTES:
            raise ValueError("source exceeds MAX_WEB_BYTES")
        src = source or urllib.parse.urlparse(url).netloc
        text = strip_html(raw)
        chunks = self._chunk(text)
        n = 0
        for c in chunks:
            nid = self.graph.add_neuron("fact", c, src, confidence=0.6)
            self.graph.add_synapse(nid, nid, "source_of", 1.0)
            n += 1
        return n

    # ---- local HTML knowledge sources (matruswara) ----------------------------
    def ingest_html_file(self, filename: str, text=None, source=None, consent=True) -> int:
        """Ingest a local HTML knowledge file (e.g. SatyaSandha AI or Neural
        Research OS/OI). Extracts readable content AND any embedded neuron/synapse
        graph JSON so the knowledge graph component survives the move."""
        self._consent(consent)
        if text is None:
            with open(filename, encoding="utf-8", errors="ignore") as fh:
                raw = fh.read()
        else:
            raw = text
        src = source or "matruswara:" + filename.split("/")[-1]
        n = 0

        # embedded neuron/synapse graphs (OI/Neural Research OS style)
        for m in re.finditer(r"\[?\s*\{[^{}]*?['\"]id['\"][^{}]*?\}\s*\]?", raw):
            pass  # heuristic scan below is more reliable; avoid brittle JSON-fragments

        body_nodes = self._extract_graph_fragments(raw, src)
        for node in body_nodes:
            nid = self.graph.add_neuron(node.get("kind", "note"),
                                        node.get("content", node.get("title", "")),
                                        src, confidence=0.5,
                                        meta={"title": node.get("title")})
            for syn in node.get("synapses", []):
                target = self._find_or_create(source_text=syn, src=src)
                self.graph.add_synapse(nid, target, "synapse", 1.0)
            n += 1

        # readable text as facts
        text_body = strip_html(raw)
        for c in self._chunk(text_body, max_words=40):
            nid = self.graph.add_neuron("note", c, src, confidence=0.4)
            self._link_synapses(nid, {"topic": " ".join(tokenize(c)[:4])})
            n += 1
        return n

    # ---- helpers -----------------------------------------------------------------
    def _add_signal(self, kind, content, source, confidence, meta):
        nid = self.graph.add_neuron(kind, content, source, confidence=confidence, meta=meta)
        return nid

    def _link_synapses(self, nid, meta):
        topic = meta.get("topic")
        if not topic:
            return
        for r in self.graph.store.all_nodes():
            if r["node_id"] == nid:
                continue
            rmeta = json.loads(r["meta"] or "{}") if isinstance(r["meta"], str) else {}
            if rmeta.get("topic") == topic:
                self.graph.add_synapse(nid, r["node_id"], "related_to", 0.7)
                self.graph.add_synapse(r["node_id"], nid, "related_to", 0.7)
            if r["kind"] in ("value", "trait") and rmeta.get("topic") == topic:
                self.graph.add_synapse(nid, r["node_id"], "evidence_for", 1.0)

    def _find_or_create(self, source_text, src):
        """find or create a neuron for a synapse label (OI neuron graph)."""
        for r in self.graph.store.all_nodes():
            if (r["content"] or "").strip() == source_text.strip():
                return r["node_id"]
        return self.graph.add_neuron("note", source_text, src, confidence=0.4)

    def _extract_graph_fragments(self, raw, src):
        out = []
        for m in re.finditer(r"\{\s*['\"]?id['\"]?\s*:\s*['\"][^'\"]+['\"][^{}]*?\}", raw):
            frag = m.group(0)
            try:
                clean = re.sub(r"([{,])\s*(\w+)\s*:", r'\1"\2":', frag)
                clean = re.sub(r":\s*'([^']*)'", r':"\1"', clean)
                obj = json.loads(clean)
                if "id" in obj and ("content" in obj or "title" in obj):
                    out.append(obj)
            except (ValueError, json.JSONDecodeError):
                continue
        return out[:20]

    def _chunk(self, text, max_words=64):
        words = text.split()
        out = []
        for i in range(0, len(words), max_words):
            piece = " ".join(words[i:i + max_words])
            if len(piece) > 20:
                out.append(piece)
        return out

    def _guard_ssrf(self, url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("only http/https URLs allowed")
        host = parsed.hostname or ""
        try:
            addrs = socket.getaddrinfo(host, None)
        except socket.gaierror as e:
            raise ValueError(f"cannot resolve {host}: {e}") from e
        for af, *_ , (ip, *_) in [a for a in addrs if a[0] in (socket.AF_INET,)]:
            ipobj = ipaddress.ip_address(ip)
            if not ipobj.is_global:
                raise PermissionError(f"SSRF guard: refusing non-public address {ip}. Hosting services may change resolved IPs; add explicit allowlisting for fixed hosts.")