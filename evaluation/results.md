# Retrieval Evaluation

- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Corpus: `data/sample_policies.md` (synthetic demonstration data)
- Indexed chunks: 14
- Distance metric: cosine
- `TOP_K`: 4
- Supported questions: 12 (8 direct, 4 paraphrased)
- Unsupported questions: 8
- Supported top-similarity range: 0.454581–0.739649
- Unsupported top-similarity range: 0.201173–0.511700
- Selected `MIN_SIMILARITY`: 0.52

The score ranges overlap. A threshold of 0.52 rejected all eight evaluated
unsupported questions, prioritizing anti-hallucination behavior, but it also
rejected three supported questions. This value is specific to this embedding
model and synthetic corpus; it is not universal.

Two direct supported questions retrieved the general Incident Response section
above their more specific Employee Device Security or Vendor and Third-Party
Access sections. The correct sections may still appear within `TOP_K=4`, but
this is a top-result retrieval limitation.
