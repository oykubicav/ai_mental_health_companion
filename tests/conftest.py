"""Test ortamı — HERHANGİ bir pipeline/api modülü import edilmeden önce.

pipeline/config.py ayarları modül seviyesinde okuyor (LLM_PROVIDER gibi).
pytest test dosyalarını toplarken import ediyor; kök dizindeki bir test
pipeline'ı import ederse config o anda gerçek sağlayıcıyla donuyor ve
tests/api/conftest.py'deki fixture sonradan çalıştığında iş işten geçmiş
oluyor — API testleri "anthropic package not installed" ile düşüyor.

conftest.py'ler test modüllerinden önce import edildiği için ayarları
burada, fixture'da değil, modül seviyesinde yapıyoruz.
"""

import os

os.environ.setdefault("CBT_LLM_PROVIDER", "mock")
os.environ.setdefault("CBT_PREFER_ST", "0")
