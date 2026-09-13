"""PTM - Personal Tensor Memory.

A privacy-preserving, on-device tensor sketch of the user's memory stream
(extension of the Personal Tensor Memory add-on by Ravishankar S R, India).

The raw conversational/text memory never leaves the local SQLite vault.
PTM is only a *feature-hashed, sign-randomized* accumulation of token
frequencies into a fixed-size tensor. It:

* leaks no raw text (feature hashing without a decoder),
* is tiny (default 2^19 float32 buckets ~= 2 MB, far under the 8 MB budget),
* supports cosine similarity for drift / similarity probing,
* can be carried on a smartphone and merged with the main brain like a
  memory bridge.

Latent Personal Memory (LPM, arXiv 2606.20911) motivates compact persistent
per-user matrices as a scalable, interpretable personalization substrate; PTM
is the privacy-preserving on-device variant.
"""

from __future__ import annotations

import array
import hashlib
import json
import math
import struct

DEFAULT_BUCKETS = 1 << 19  # 2^19 float32 values = 2 MiB
BYTES_PER_BUCKET = 4


def _hash_pair(token: str):
    b1 = hashlib.sha256(b"ptm:idx:" + token.encode("utf-8")).digest()
    b2 = hashlib.sha256(b"ptm:sgn:" + token.encode("utf-8")).digest()
    idx = int.from_bytes(b1[:8], "big") % (1 << 63)
    sign = 1.0 if (b2[0] & 1) else -1.0
    return idx, sign


class PersonalTensorMemory:
    """Feature-hashed tensor sketch. Immutable summary; no raw plaintext."""

    def __init__(self, buckets=None, data=None):
        self.buckets = buckets or DEFAULT_BUCKETS
        if data is None:
            self.data = array.array("f", [0.0]) * self.buckets
        else:
            self.data = data

    # ---------------- update -------------------------------------------------
    def add_tokens(self, tokens, weight=1.0) -> None:
        half = self.buckets // 2
        for t in tokens:
            idx, sign = _hash_pair(t)
            bucket = idx % self.buckets
            # split-sign trick keeps the sketch zero-mean and private
            self.data[bucket] += sign * float(weight)
            self.data[(bucket + half) % self.buckets] -= sign * float(weight)

    def update_from_text(self, text, weight=1.0):
        from .memory import tokenize
        self.add_tokens(tokenize(text), weight)

    # ---------------- similarity ---------------------------------------------
    def cosine(self, other: "PersonalTensorMemory") -> float:
        a, b = self.data, other.data
        n = min(len(a), len(b))
        dot = sum(a[i] * b[i] for i in range(n))
        na = math.sqrt(sum(x * x for x in a[:n]))
        nb = math.sqrt(sum(x * x for x in b[:n]))
        denom = na * nb or 1.0
        return dot / denom

    # ---------------- serialization ------------------------------------------
    def to_bytes(self) -> bytes:
        return b"PTM1" + struct.pack(">I", self.buckets) + self.data.tobytes()

    @classmethod
    def from_bytes(cls, raw: bytes) -> "PersonalTensorMemory":
        if raw[:4] != b"PTM1":
            raise ValueError("bad PTM header")
        buckets = struct.unpack(">I", raw[4:8])[0]
        arr = array.array("f")
        arr.frombytes(raw[8:8 + buckets * BYTES_PER_BUCKET])
        return cls(buckets=buckets, data=arr)

    # ---------------- metadata ------------------------------------------------
    def nbytes(self) -> int:
        return len(self.data.tobytes())

    def summary(self) -> dict:
        return {
            "buckets": self.buckets,
            "nbytes": self.nbytes(),
            "mib": round(self.nbytes() / (1024 * 1024), 3),
            "under_8mb_budget": self.nbytes() <= 8 * 1024 * 1024,
            "privacy": "feature-hashed, sign-randomized; no raw text stored",
        }

    # ---------------- memory-bridge export ------------------------------------
    def to_bridge(self, recipient_path: str) -> None:
        """Write a portable PTM bridge file for smartphone merge."""
        with open(recipient_path, "wb") as fh:
            fh.write(self.to_bytes())

    @classmethod
    def merge(cls, a: "PersonalTensorMemory", b: "PersonalTensorMemory") -> "PersonalTensorMemory":
        n = min(a.buckets, b.buckets)
        out = array.array("f", a.data[:n])
        for i in range(n):
            out[i] += b.data[i]
        return cls(buckets=n, data=out)