"""Document search for the staffing assistant (the `search_docs` tool).

Sources: CMS PBJ documentation, the CMS nursing home data dictionary, and the project's own
metric glossary (docs/). `python3 rag.py --build` splits them into chunks, embeds each chunk
with a small local model (BAAI/bge-small-en-v1.5 via fastembed, no API key needed) and saves the
index to index/. At question time, search() combines two rankings:
  - meaning (cosine similarity of embeddings): finds "agency staff" when the doc says "contract"
  - keywords (BM25): finds exact column names like HRS_RN_CTR that embeddings blur
and merges them with reciprocal rank fusion. Every result carries its source and page so the
assistant can cite it.

  python3 rag.py --build                       # (re)build the index after changing docs/
  python3 rag.py "what counts as contract staff"   # try a search
"""
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
INDEX = ROOT / "index"
MODEL_NAME = "BAAI/bge-small-en-v1.5"
CHUNK_CHARS = 1100
OVERLAP_CHARS = 200

SOURCES = [
    {
        "file": "metric_glossary.md",
        "title": "Project metric glossary",
        "url": "https://github.com/jlredding/clipboard_health_ai/blob/main/docs/metric_glossary.md",
    },
    {
        "file": "PBJ_PUF_Documentation_July_2023.pdf",
        "title": "CMS PBJ Public Use Files: Technical Specifications (July 2023)",
        "url": "https://data.cms.gov/sites/default/files/2023-06/PBJ_PUF_Documentation_July_2023.pdf",
    },
    {
        "file": "Payroll_Based_Journal_Daily_Nursing_Staffing_Data_Dictionary.pdf",
        "title": "CMS PBJ Daily Nurse Staffing Data Dictionary",
        "url": "https://data.cms.gov/resources/payroll-based-journal-daily-nurse-staffing-data-dictionary",
    },
    {
        "file": "pbj-policy-manual-v2-8-august-2026.pdf",
        "title": "CMS PBJ Long-Term Care Facility Policy Manual v2.8 (August 2026)",
        "url": "https://www.cms.gov/files/document/pbj-policy-manual-v2-8-august-2026.pdf",
    },
    {
        "file": "NH_Data_Dictionary.pdf",
        "title": "CMS Nursing Home Care Compare / Provider Data Catalog Data Dictionary (Oct 2024)",
        "url": "https://data.cms.gov/provider-data/sites/default/files/data_dictionaries/nursing_home/NH_Data_Dictionary.pdf",
    },
]


# ---------- building the index ----------

def _pages(source: dict) -> list[tuple[str, str]]:
    """Return (location label, text) pairs: PDF pages, or markdown sections for the glossary."""
    path = DOCS / source["file"]
    if path.suffix == ".md":
        sections = re.split(r"\n(?=## )", path.read_text())
        out = []
        for s in sections:
            heading = s.splitlines()[0].lstrip("# ").strip()
            out.append((f"section: {heading}", s.strip()))
        return out
    from pypdf import PdfReader  # only needed when building

    return [(f"p. {i}", page.extract_text() or "") for i, page in enumerate(PdfReader(path).pages, 1)]


def _clean(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def _chunk(text: str) -> list[str]:
    """Pack paragraphs into chunks of ~CHUNK_CHARS, overlapping so a definition isn't cut in half."""
    paras = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    chunks, current = [], ""
    for p in paras:
        while len(p) > CHUNK_CHARS:  # very long paragraph: hard-split it
            head, p = p[:CHUNK_CHARS], p[CHUNK_CHARS - OVERLAP_CHARS:]
            if current:
                chunks.append(current)
                current = ""
            chunks.append(head)
        if len(current) + len(p) + 2 > CHUNK_CHARS and current:
            chunks.append(current)
            current = current[-OVERLAP_CHARS:] + "\n\n" + p
        else:
            current = f"{current}\n\n{p}" if current else p
    if current:
        chunks.append(current)
    return [c for c in chunks if len(c) > 80]  # drop page-number-only fragments


def build_index() -> None:
    from fastembed import TextEmbedding

    chunks = []
    for source in SOURCES:
        for location, text in _pages(source):
            for piece in _chunk(_clean(text)):
                chunks.append(
                    {
                        "id": f"C{len(chunks) + 1}",
                        "source": source["title"],
                        "location": location,
                        "url": source["url"],
                        "text": piece,
                    }
                )
    model = TextEmbedding(MODEL_NAME)
    vectors = np.array(list(model.passage_embed([c["text"] for c in chunks])), dtype=np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)

    INDEX.mkdir(exist_ok=True)
    (INDEX / "chunks.json").write_text(json.dumps(chunks, indent=1))
    np.save(INDEX / "embeddings.npy", vectors)
    per_source = {}
    for c in chunks:
        per_source[c["source"]] = per_source.get(c["source"], 0) + 1
    print(f"Indexed {len(chunks)} chunks:")
    for s, n in per_source.items():
        print(f"  {n:4d}  {s}")


# ---------- searching ----------

def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


@lru_cache(maxsize=1)
def _load():
    from fastembed import TextEmbedding
    from rank_bm25 import BM25Okapi

    chunks = json.loads((INDEX / "chunks.json").read_text())
    vectors = np.load(INDEX / "embeddings.npy")
    bm25 = BM25Okapi([_tokens(c["source"] + " " + c["text"]) for c in chunks])
    return chunks, vectors, bm25, TextEmbedding(MODEL_NAME)


def search(query: str, k: int = 5) -> list[dict]:
    """Top-k chunks for a query, best first, each with id, source, location, url, text and score."""
    chunks, vectors, bm25, model = _load()
    qv = np.array(list(model.query_embed([query]))[0], dtype=np.float32)
    qv /= np.linalg.norm(qv)
    dense_rank = np.argsort(-(vectors @ qv))
    sparse_rank = np.argsort(-bm25.get_scores(_tokens(query)))

    # Reciprocal rank fusion: a chunk that ranks well on either list rises to the top.
    fused: dict[int, float] = {}
    for ranking in (dense_rank[:50], sparse_rank[:50]):
        for rank, idx in enumerate(ranking):
            fused[int(idx)] = fused.get(int(idx), 0.0) + 1.0 / (60 + rank)
    best = sorted(fused, key=fused.get, reverse=True)[:k]
    return [{**chunks[i], "score": round(fused[i], 4)} for i in best]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--build":
        build_index()
    elif len(sys.argv) > 1:
        for r in search(" ".join(sys.argv[1:])):
            print(f"\n[{r['id']}] {r['source']}, {r['location']} (score {r['score']})")
            print(r["text"][:500])
    else:
        print(__doc__)
