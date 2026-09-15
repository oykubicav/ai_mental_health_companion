"""Retriever — embedding-based with safety override and metadata filter.

Pipeline step 3 (after safety + intent). Returns top-K CBT cards relevant
to the user message.

Mandatory rules per spec:
  1. Safety override: any safety card surfaced by the safety_classifier is
     prepended to the result with score=1.0. The retriever never silently
     drops these.
  2. Metadata filter: optional `module_filter` set restricts retrieval to
     specific topics (intent classifier hook).
  3. Embedding-based: uses pipeline.embedding_backend which auto-selects
     sentence-transformers when installed; TF-IDF char-ngram fallback
     otherwise. Either way fully local.

Cards are loaded once, embedded once (with on-disk cache keyed by content
hash + backend name).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

from . import config
from . import embedding_backend
from . import cards as _cards
from .types import RetrievedCard



# Embedding index (cached)
@lru_cache(maxsize=1)
def _build_card_index():
    """Fit the embedding backend on the CBT card texts and return the
    (backend, matrix, cards) triple. Cached — only fit once.
    """
    cards = _cards.all_cbt_cards()
    texts = [c["_text"] for c in cards]
    # Retriever eşik kullanmıyor, yalnızca sıralıyor — daha iyi bir gömme
    # burada doğrudan kazanç. Güvenlik katmanı ayrı bayrağa bakıyor.
    backend = embedding_backend.get_backend(prefer_st=config.PREFER_ST_RETRIEVAL)
    backend.fit(texts)
    matrix = backend.encode(texts)
    return backend, matrix, cards



# Modelin seçtiği kart, graf kartlarının (0.65 / 0.50) üstünde ama güvenlik
# kartının (1.0) altında. Güvenlik hiçbir koşulda geçilmez.
_LLM_SELECTION_SCORE = 0.90


# Public API
def retrieve(
    user_message: str,
    *,
    top_k: int = None,
    module_filter: Optional[set] = None,
    safety_card_ids: Optional[List[str]] = None,
    allow_cbt: bool = True,
    preferred_ids: Optional[List[str]] = None,
) -> List[RetrievedCard]:
    """Return the top-K cards. Safety cards (if provided) are prepended.

    HARD STOP: if allow_cbt is False, return ONLY the safety cards — the
    retriever does not surface any CBT card in a blocked safety lane.
    This prevents forbidden-card leakage in crisis / emergency routes.
    """
    top_k = top_k or config.RETRIEVAL_TOP_K
    out: List[RetrievedCard] = []
    seen_ids = set()

    # 1. Safety override — mandatory
    if safety_card_ids:
        safety_cards = _cards.safety_cards_by_id()
        for sid in safety_card_ids:
            if sid in safety_cards and sid not in seen_ids:
                c = safety_cards[sid]
                out.append(RetrievedCard(
                    card_id=c["card_id"],
                    topic="safety",
                    type=c["card_type"],
                    title_tr=c["title"],
                    score=1.0,
                    snippet=c["safe_response_template_tr"][:200],
                ))
                seen_ids.add(sid)

    # 1b. HARD STOP — blocked safety lanes never surface CBT content
    if not allow_cbt:
        return out

    # 1c. Modelin seçtiği kartlar — varsa gömme sıralamasının önüne geçer.
    #
    # Gömme sıralamasının ayırt etme gücü ölçüldü ve düşük çıktı (medyan
    # tepe skor 0.093, tepe/son oranı 1.58x). Model seçebiliyorsa onun
    # seçimi daha bilgili. Gelmezse aşağıdaki gömme yolu aynen çalışır.
    if preferred_ids:
        _, _, tum_kartlar = _build_card_index()
        by_id = {c["id"]: c for c in tum_kartlar}
        for rank, cid in enumerate(preferred_ids):
            c = by_id.get(cid)
            if c is None or cid in seen_ids:
                continue
            if module_filter is not None and c["topic"] not in module_filter:
                # Model konu filtresinin dışına çıktıysa ona uyuluyor:
                # filtre intent etiketinden geliyor ve o da yanılabiliyor.
                pass
            out.append(RetrievedCard(
                card_id=c["id"],
                topic=c["topic"],
                type=c["type"],
                title_tr=c["title_tr"],
                score=_LLM_SELECTION_SCORE - rank * 0.01,
                snippet=c["content_tr"][:200],
                source="llm",
            ))
            seen_ids.add(cid)

    # 2. Embedding retrieval
    backend, matrix, cards = _build_card_index()
    q = backend.encode([user_message])
    sims = embedding_backend.cosine_similarity(q, matrix)[0]

    indices = sorted(range(len(cards)), key=lambda i: -float(sims[i]))
    cap = top_k + len(out)
    for i in indices:
        c = cards[i]
        if c["id"] in seen_ids:
            continue
        if module_filter is not None and c["topic"] not in module_filter:
            continue
        out.append(RetrievedCard(
            card_id=c["id"],
            topic=c["topic"],
            type=c["type"],
            title_tr=c["title_tr"],
            score=float(sims[i]),
            snippet=c["content_tr"][:200],
        ))
        seen_ids.add(c["id"])
        if len(out) >= cap:
            break
    return out


# Hybrid retrieve — vector seeds + graph enrichment
# Skorlama sabitleri (Faz 2 kararı)
_GRAPH_TECHNIQUE_SCORE = 0.65   # aynı tekniği paylaşan kart
_GRAPH_NEIGHBOR_SCORE = 0.50    # komşu modülden kart


def hybrid_retrieve(
    user_message: str,
    *,
    top_k: int = None,
    k_vector_seeds: int = 5,
    k_graph_neighbors: int = 3,
    module_filter: Optional[set] = None,
    safety_card_ids: Optional[List[str]] = None,
    allow_cbt: bool = True,
    preferred_ids: Optional[List[str]] = None,
) -> List[RetrievedCard]:
    """Vektör seed'leri + graf zenginleştirme.

    Akış:
      1. Safety override (mevcut retrieve() ile aynı) — safety_card_ids varsa dön
      2. HARD STOP: allow_cbt=False ise sadece safety kartlar
      3. Vektör: top-K seed kart bul
      4. Her seed için:
         - cards_sharing_technique(seed) → aynı tekniği paylaşan cross-modül kartlar
         - neighbor_module_cards(seed) → komşu modülden kartlar
      5. Dedup (aynı card_id iki kez gelmesin)
      6. Skoru ile sort → top_k döndür

    Neo4j down / hata → vektör-only fallback (retrieve() sonucu döner).
    """
    top_k = top_k or config.RETRIEVAL_TOP_K

    # 1-2-3: mevcut retrieve() 'i vektör seed'ler için kullan
    vector_out = retrieve(
        user_message,
        top_k=k_vector_seeds,
        module_filter=module_filter,
        safety_card_ids=safety_card_ids,
        allow_cbt=allow_cbt,
        preferred_ids=preferred_ids,
    )

    # HARD STOP: safety-only lane
    if not allow_cbt:
        return vector_out

    # Safety kartlarını ayır (sonda tekrar üste koyacağız)
    safety_out = [c for c in vector_out if c.topic == "safety"]
    seed_cards = [c for c in vector_out if c.topic != "safety"]
    seed_ids = {c.card_id for c in seed_cards}

    # 4: Graf zenginleştirme
    graph_out: List[RetrievedCard] = []
    try:
        from graph import queries as gq

        # Full content lookup için — snippet doldurmak lazım
        cbt_by_id = _cards.cbt_cards_by_id()

        for seed in seed_cards[:k_vector_seeds]:
            # 4a. Technique-sharing (cross-modül)
            # NOT: module_filter'a saygı gösteriyoruz — teknik paylaşımı bir
            # "off-topic" modüle sıçratmasın. neighbor_module_cards'ta bilerek
            # bypass ediyoruz (o zaten komşu modül için tasarlandı).
            for row in gq.cards_sharing_technique(seed.card_id)[:k_graph_neighbors]:
                cid = row["id"]
                if cid in seed_ids:
                    continue
                if module_filter is not None and row.get("topic") not in module_filter:
                    continue

                retrieved_card = RetrievedCard(
                    card_id=cid,
                    topic=cbt_by_id[cid]["topic"],
                    type=cbt_by_id[cid]["type"],
                    title_tr=cbt_by_id[cid]["title_tr"],
                    score=_GRAPH_TECHNIQUE_SCORE,
                    snippet=cbt_by_id[cid]["content_tr"][:200],
                    source="graph_technique",
                    via_technique=row["technique"],
                )
                graph_out.append(retrieved_card)
                seed_ids.add(cid)

            # 4b. Neighbor-module cards
            for row in gq.neighbor_module_cards(seed.card_id, limit=k_graph_neighbors):
                cid = row["id"]
                if cid in seed_ids:
                    continue
                retrieved_card = RetrievedCard(
                    card_id=cid,
                    topic=cbt_by_id[cid]["topic"],
                    type=cbt_by_id[cid]["type"],
                    title_tr=cbt_by_id[cid]["title_tr"],
                    score=_GRAPH_NEIGHBOR_SCORE,
                    snippet=cbt_by_id[cid]["content_tr"][:200],
                    source="graph_neighbor",
                    via_neighbor_of=seed.card_id,
                )
                graph_out.append(retrieved_card)
                seed_ids.add(cid)

    except Exception as e:
        # Neo4j down ya da başka bir hata — sadece vektör dön
        import logging
        logging.warning(f"Graph enrichment failed, falling back to vector-only: {e}")
        return vector_out

    import logging
    logging.info(
        "graph_enrichment ok: %d seed → +%d graph card (%d technique, %d neighbor)",
        len(seed_cards),
        len(graph_out),
        sum(1 for c in graph_out if c.source == "graph_technique"),
        sum(1 for c in graph_out if c.source == "graph_neighbor"),
    )

    # Dedup: card_id → RetrievedCard (en yüksek skor kalır)
    combined: dict[str, RetrievedCard] = {}
    for card in seed_cards + graph_out:
        if card.card_id in combined:
            if card.score > combined[card.card_id].score:
                combined[card.card_id] = card
        else:
            combined[card.card_id] = card

    # Sort by score desc, take top_k CBT cards, safety önde
    sorted_cbt = sorted(combined.values(), key=lambda c: -c.score)[:top_k]
    return safety_out + sorted_cbt


def backend_name() -> str:
    backend, _, _ = _build_card_index()
    return backend.name


if __name__ == "__main__":
    queries = [
        "Sürekli nabzımı kontrol ediyorum",
        "Panik atak sırasında ne yapabilirim",
        "Yatakta uyuyamıyorum, düşüncelerim durmuyor",
    ]
    print(f"Backend: {backend_name()}\n")

    for q in queries:
        print(f">>> {q}")
        print("  Vector-only:")
        for r in retrieve(q, top_k=3):
            print(f"    {r.score:6.3f}  [{r.source:15s}]  {r.card_id:30s}  {r.title_tr}")
        print("  Hybrid:")
        for r in hybrid_retrieve(q, top_k=6):
            marker = ""
            if r.via_technique:
                marker = f" via:{r.via_technique}"
            elif r.via_neighbor_of:
                marker = f" via:{r.via_neighbor_of}"
            print(f"    {r.score:6.3f}  [{r.source:15s}]  {r.card_id:30s}  {r.title_tr}{marker}")
        print()