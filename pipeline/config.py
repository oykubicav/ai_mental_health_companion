"""Pipeline configuration.

All paths and runtime flags live here. Secrets (API keys) come from env vars,
NOT from this file.
"""

import os
from pathlib import Path

# --- paths ---
ROOT = Path(__file__).resolve().parent.parent  # cbt_knowledge_base/
CARDS_PATH = ROOT / "cards" / "cbt_cards.jsonl"
SAFETY_CARDS_PATH = ROOT / "cards" / "safety_cards.jsonl"
POLICY_PATH = ROOT / "policies" / "response_policy.md"
TEST_SET_PATH = ROOT / "evals" / "retrieval_test_set.jsonl"
REGISTRY_PATH = ROOT / "registry" / "source_registry.csv"

# --- LLM provider ---
# Switchable at runtime. KVKK note: for production deployment to TR users,
# this should default to a private/local model, with cloud APIs gated.
LLM_PROVIDER = os.environ.get("CBT_LLM_PROVIDER", "anthropic")  # anthropic | openai | local | mock
LLM_MODEL_COMPOSER = os.environ.get("CBT_MODEL_COMPOSER", "claude-sonnet-4-6")
LLM_MODEL_INTENT = os.environ.get("CBT_MODEL_INTENT", "claude-haiku-4-5-20251001")
LLM_MODEL_CRITIC = os.environ.get("CBT_MODEL_CRITIC", "claude-haiku-4-5-20251001")

# --- safety classifier ---
SAFETY_KEYWORD_MATCH_MIN_RATIO = 0.6  # token overlap threshold for fuzzy match
SAFETY_LLM_FALLBACK = False           # off by default for offline / KVKK-safe runs

# Embedding backend preference for Layer 3.
# Empirically TF-IDF outperforms sentence-transformers on the current
# test set (90% vs 78% overall_pass) because ST's semantic breadth
# over-triggers CBT-appropriate messages onto safety routes. Anchor
# cümleleri şu an TF-IDF karakter n-gram örüntüsüne uygun; ST için
# ayrı ve daha ayırt edici anchor seti gerekir. LLM composer/critic
# tarafı gelince Layer 3 üzerindeki basınç zaten düşecek — o zaman
# ST tekrar değerlendirilebilir.
PREFER_SENTENCE_TRANSFORMERS = os.environ.get("CBT_PREFER_ST", "0") == "1"

# Bu bayrak YALNIZCA retriever için geçerli. Güvenlik sınıflandırıcısının
# 3. katmanı TF-IDF'e sabitlenmiş durumda ve bayrağı dinlemiyor.
#
# Ölçüm (2026-09-09, 73 vakalık retrieval seti):
#     CBT_PREFER_ST=1  →  retrieval_hit_rate  80.0% → 87.7%   (+7.7)
#                         safety_recall       88.2% → 61.4%  (-26.8)
#
# Sebep eşiklerin ölçeğe bağlı olması: TF-IDF karakter n-gramı benzerlikleri
# 0.05–0.20 aralığında toplanıyor, sentence-transformers 0.3–0.9 civarında
# üretiyor. Layer 3 eşikleri TF-IDF dağılımına göre ayarlandığı için ST'ye
# geçince aynı sayı bambaşka bir anlama geliyor ve riskli mesajlar eşiğin
# altında kalıyor. 57 riskli vakanın 22'si kaçıyordu.
#
# Retriever'ın eşiği yok, yalnızca sıralama yapıyor — orada daha iyi bir
# gömme doğrudan kazanç. Bu yüzden iki taraf ayrıldı. Güvenlik tarafında
# ST'ye geçilecekse önce Layer 3 eşiklerinin ST dağılımına göre yeniden
# ayarlanması ve safety_recall'ın yeniden ölçülmesi gerekiyor.
PREFER_ST_RETRIEVAL = PREFER_SENTENCE_TRANSFORMERS
PREFER_ST_SAFETY = False

# --- retriever ---
EMBED_MODEL = os.environ.get(
    "CBT_EMBED_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
RETRIEVAL_TOP_K = 5
EMBED_CACHE_PATH = ROOT / "pipeline" / "_embed_cache.npz"  # gitignore this

# --- privacy / KVKK ---
ENABLE_PII_REDACTION = True
ENABLE_LLM_PROMPT_LOGGING = False  # never log raw user input by default
ENABLE_TEST_PROMPT_LOGGING = os.environ.get("CBT_TEST_LOG_PROMPTS", "0") == "1"

# --- eval ---
EVAL_RESULTS_DIR = ROOT / "evals" / "results"
EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
