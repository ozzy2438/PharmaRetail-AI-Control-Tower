Kesinlikle. Bu ilana **“OpenAI API + PDF chatbot”** ile girilmez. Bu ilanda aranan şey: **Snowflake + dbt + governed enterprise data + RAG + agentic AI + LLMOps + CI/CD + monitoring + security** kombinasyonunu gerçekten anlayan biri.

Ben olsam tek bir ana proje yapardım:

# Proje: **PharmaRetail AI Control Tower**

## Kısa tanım

**Snowflake ve dbt Cloud üzerinde çalışan, eczane/perakende operasyonları için governed RAG + agentic AI destekli operasyon kontrol merkezi.**

Bu sistem, mağaza müdürü, bölge yöneticisi veya tedarik/supply-chain ekibinin şu tarz sorularına cevap verir:

> “VIC bölgesinde son 7 günde cold & flu kategorisinde stockout riski en yüksek mağazalar hangileri? Bunun nedeni tedarik gecikmesi mi, promosyon etkisi mi, forecast hatası mı? İlgili SOP’ye göre ne yapılmalı?”

Sistem sadece cevap vermez. Şunları yapar:

- Snowflake’teki governed satış/stok/tedarik verisini sorgular.
- dbt semantic layer / marts üzerinden tutarlı metrik kullanır.
- SOP, policy, recall, cold-chain, returns, store operations dokümanları üzerinden RAG yapar.
- Cevapları kaynaklı ve denetlenebilir verir.
- Kullanıcının rolüne göre RLS/RBAC uygular.
- Yetki dışı store/region/customer verisini göstermez.
- Gerektiğinde “ticket/action plan draft” üretir ama insan onayı olmadan işlem yapmaz.
- Her cevabı latency, cost, retrieval quality, hallucination risk, SQL accuracy açısından loglar ve izler.

Yani bu bir “chatbot” değil. Bu, **enterprise AI data product**.

---

# Neden bu proje Chemist Warehouse ilanına çok iyi oturur?

Çünkü ilan aslında şunu arıyor:

> “LLM bilen biri” değil,  
> **enterprise-grade AI capability build/run/monitor/optimise edebilen biri.**

Bu proje ilanla birebir eşleşir:

| İlan ihtiyacı | Projede nasıl kanıtlanır? |
|---|---|
| Snowflake | Veri modeli, RBAC/RLS, masking, warehouse cost management, query optimisation |
| dbt Cloud | staging/intermediate/mart modelleri, tests, docs, environments, Git workflow |
| RAG | SOP/policy/operations dokümanları üzerinde metadata-filtered RAG |
| Conversational AI | Store/area manager doğal dil arayüzü |
| Agentic AI | Stockout investigation agent, supplier escalation draft, incident triage workflow |
| LLMOps/MLOps | Eval suite, regression tests, monitoring, prompt/model versioning |
| CI/CD | GitHub Actions + dbt Cloud jobs + deployment automation |
| Governance | Role-based answers, masking, audit logging, medical-advice refusal |
| Production outcome | Runbook, SLO, dashboards, cost/latency reports, pilot/UAT evidence |

---

# Projenin ana hikâyesi

Chemist Warehouse gibi 600+ mağazalı, çok ülkeli, pharmacy + retail + distribution yapısında sorun şu olur:

- Veri Snowflake’te olabilir ama iş kullanıcıları SQL yazamaz.
- SOP/policy dokümanları ayrı yerde durur.
- Mağaza ekipleri hızlı cevap ister.
- Tedarik, stockout, promo, supplier delay, recall, cold-chain, returns gibi konular hem veri hem doküman bilgisi ister.
- AI kullanılsa bile governance, güvenlik, maliyet ve audit olmadan production’a alınamaz.

Senin projen bu problemi çözer:

> **“Doğal dille sor, governed enterprise data + policy knowledge üzerinden açıklamalı, kaynaklı, güvenli ve aksiyona çevrilebilir cevap al.”**

---

# Modüller

## 1. Governed Retail Pharmacy Data Platform

Snowflake üzerinde synthetic ama gerçekçi bir pharmacy-retail veri modeli kurarsın.

Örnek tablolar:

- `dim_store`
- `dim_product`
- `dim_supplier`
- `dim_date`
- `fct_sales_daily`
- `fct_inventory_snapshot`
- `fct_supplier_delivery`
- `fct_stockout_event`
- `fct_returns`
- `fct_promotion`
- `fct_incident`

Örnek metrikler:

- stockout rate
- days of cover
- lost sales estimate
- supplier OTIF
- inventory turn
- gross margin rate
- promo uplift
- stale inventory
- data freshness score

Burada kritik nokta şu: AI doğrudan raw tabloya gitmeyecek. dbt ile modellenmiş, test edilmiş, semantic olarak tutarlı mart/metric katmanını kullanacak.

Bu, senior/principal sinyali verir.

---

## 2. SOP / Policy RAG Katmanı

RAG kısmında rastgele PDF chatbot yapmayacaksın. Dokümanları enterprise metadata ile işleyeceksin.

Örnek doküman kategorileri:

- store operations SOP
- cold-chain incident SOP
- product recall process
- returns/refunds policy
- supplier escalation process
- inventory adjustment guide
- promotional execution checklist
- pharmacy safety/compliance boundaries
- AI usage policy

Her chunk şu metadata ile tutulur:

- `doc_id`
- `doc_version`
- `country`
- `business_unit`
- `effective_date`
- `expiry_date`
- `access_level`
- `policy_owner`
- `source_url_or_file`
- `embedding_model_version`

Cevaplarda mutlaka citation olacak:

> “Kaynak: Cold Chain Incident SOP v1.3, Section 4.2, effective from 2025-01-01”

Bu, sıradan RAG projesini kurumsal RAG projesine çevirir.

---

## 3. Agentic Workflow

Burada “agent” serbest bırakılmış bir robot olmayacak. Kontrollü, deterministic, human-in-the-loop bir workflow olacak.

Örnek agent: **Stockout Investigation Agent**

Kullanıcı sorar:

> “NSW bölgesinde hay fever ürünlerinde stockout neden arttı?”

Agent adımları:

1. Kullanıcının rolünü kontrol eder.
2. Yetkili olduğu region/store listesini belirler.
3. dbt mart üzerinden stockout metriğini çeker.
4. Supplier delivery ve promotion verisini analiz eder.
5. İlgili replenishment / supplier escalation SOP’sini RAG ile bulur.
6. Root cause summary üretir.
7. Aksiyon planı önerir.
8. Eğer gerekiyorsa ticket draft oluşturur.
9. İnsan onayı olmadan hiçbir dış işlem yapmaz.
10. Tüm süreci audit log’a yazar.

Tool örnekleri:

- `get_stockout_metrics`
- `get_supplier_delivery_performance`
- `search_policy_docs`
- `draft_supplier_escalation`
- `create_action_plan`
- `log_ai_interaction`

Bu, ilandaki “secure conversational AI and agentic AI with guardrails” maddesini çok güçlü karşılar.

---

## 4. LLMOps / Monitoring / Evaluation Katmanı

Bu kısmı özellikle güçlü yapmalısın. Çünkü seni diğer adaylardan ayıracak yer burası.

Sistem şu metrikleri izlemeli:

- prompt version
- model version
- retrieval documents
- answer latency
- token cost
- Snowflake query cost
- retrieval hit rate
- citation coverage
- SQL accuracy
- refusal accuracy
- hallucination risk
- user feedback
- failed guardrail events
- data freshness

Ayrıca bir eval set oluşturmalısın.

Örnek eval kategorileri:

- 40 policy/RAG sorusu
- 40 SQL/data sorusu
- 30 mixed data + policy sorusu
- 20 adversarial prompt-injection testi
- 20 RLS/security testi
- 20 medical-advice refusal testi

Hedef metrikler:

- RLS leakage: **0**
- Policy answer citation coverage: **%100**
- SQL metric accuracy: **%90+**
- Medical advice refusal accuracy: **%95+**
- P95 latency: örneğin **< 8 saniye**
- Cost per query: hedef limit altında

Böylece “AI yaptım” değil, “AI sistemini işletiyorum” diyebilirsin.

---

# Mimari

Basit bir mimari şöyle olur:

```text
Synthetic / Public-like Data
        |
        v
Snowflake RAW
        |
        v
dbt Cloud
STG -> INT -> MART -> Semantic Metrics
        |
        +-----------------------------+
        |                             |
        v                             v
Governed SQL Tools              Policy/SOP Docs
        |                             |
        |                      Chunking + Embedding
        |                             |
        +-------------+---------------+
                      |
                      v
              AI Orchestration Layer
        Intent Router + Guardrails + Agent Workflow
                      |
        +-------------+--------------+
        |                            |
        v                            v
 Store Ops Copilot UI         Monitoring/Eval Dashboard
 Streamlit/FastAPI            LLMOps + Cost + Quality
```

Tech stack önerisi:

- **Snowflake**: warehouse, RBAC, RLS, masking, audit logs
- **dbt Cloud**: models, tests, docs, environments, Git workflow
- **Python**: FastAPI, Pydantic, pytest, ruff, mypy
- **LLM layer**: Azure OpenAI / OpenAI / Snowflake Cortex abstraction
- **RAG**: Snowflake table/vector storage veya approved vector service
- **Agent orchestration**: LangGraph veya kendi controlled workflow yapın
- **CI/CD**: GitHub Actions
- **Monitoring**: Langfuse/Phoenix + Snowflake log tables + dashboard
- **UI**: Streamlit, ama business logic UI içinde değil; backend/package içinde olmalı

---

# Roadmap

## Faz 1 — Product framing ve use-case tasarımı

Süre: 2-3 gün

Amaç: Projenin “ben AI yaptım” değil, “enterprise problem çözdüm” gibi görünmesini sağlamak.

Yapılacaklar:

- 3 persona belirle:
  - Store Manager
  - Area Manager
  - Supply Chain Analyst
- 4 ana use-case belirle:
  - stockout root-cause analysis
  - SOP/policy Q&A
  - supplier performance investigation
  - incident/action plan generation
- Non-functional requirement yaz:
  - security
  - latency
  - cost
  - accuracy
  - auditability
  - human approval

Çıktı:

- `docs/product_brief.md`
- `docs/personas.md`
- `docs/non_functional_requirements.md`

Bu bile seni junior projelerden ayırır.

---

## Faz 2 — Snowflake data platform

Süre: 1 hafta

Amaç: AI’ın oturacağı sağlam data foundation’ı kurmak.

Yapılacaklar:

- Snowflake database/schema yapısı:
  - `RAW`
  - `STAGING`
  - `INTERMEDIATE`
  - `MARTS`
  - `AI_LOGS`
  - `GOVERNANCE`
- Warehouse ayrımı:
  - `WH_DBT_DEV`
  - `WH_DBT_PROD`
  - `WH_AI_APP`
  - `WH_ADHOC`
- Resource monitor kur.
- Query tagging kullan.
- Synthetic data generator yaz.
- Store, product, sales, inventory, supplier, promotion datası üret.

Önemli: Dataset çok küçük olmasın. En azından production hissi versin.

Örnek demo ölçeği:

- 100 store
- 5,000 product
- 2 yıl sales data
- birkaç milyon sales/inventory row
- 100+ supplier
- multi-region / multi-country field

Çıktı:

- Snowflake schema
- data loading scripts
- ERD diagram
- sample query profile screenshots
- cost/warehouse configuration notes

---

## Faz 3 — dbt Cloud modelling

Süre: 1 hafta

Amaç: Data engineering tarafını kanıtlamak.

Yapılacaklar:

- dbt Cloud environment:
  - dev
  - staging
  - prod
- dbt layer:
  - source models
  - staging models
  - intermediate models
  - marts
- dbt tests:
  - not null
  - unique
  - relationships
  - accepted values
  - freshness
  - custom business tests
- Incremental models kullan.
- dbt docs oluştur.
- Exposures tanımla:
  - AI Copilot
  - Control Tower Dashboard
  - Evaluation Dashboard

Örnek custom tests:

- negative inventory olmamalı
- stockout event end date start date’den küçük olmamalı
- supplier OTIF 0-1 aralığında olmalı
- discontinued product satış üretmemeli
- promotion date future/past logic doğru olmalı

Çıktı:

- dbt docs link/screenshot
- 50+ dbt test
- CI’da dbt build
- semantic metric definitions

---

## Faz 4 — Security & governance

Süre: 3-4 gün

Amaç: İlanda özellikle geçen RBAC/RLS/masking/logging tarafını göstermek.

Yapılacaklar:

- Role model:
  - `STORE_MANAGER`
  - `AREA_MANAGER`
  - `SUPPLY_CHAIN_ANALYST`
  - `AI_APP_SERVICE`
  - `DATA_ENGINEER`
  - `ADMIN`
- Row-level security:
  - store manager sadece kendi mağazasını görür
  - area manager sadece kendi region’ını görür
  - national role tüm ülkeyi görür
- Masking:
  - customer/email/phone gibi alanlar maskelenir
  - synthetic bile olsa PII governance gösterilir
- Audit logging:
  - kim ne sordu?
  - hangi data döndü?
  - hangi doküman kullanıldı?
  - hangi model/prompt version kullanıldı?

Çıktı:

- security matrix
- RLS demo
- masking demo
- audit log dashboard

Bu kısım çok değerli. Çünkü çoğu portföy projesinde yok.

---

## Faz 5 — RAG knowledge base

Süre: 1 hafta

Amaç: Governed enterprise documentation üzerinde ciddi RAG kurmak.

Yapılacaklar:

- SOP/policy dokümanlarını markdown/PDF formatında hazırla.
- Chunking stratejisi belirle:
  - section-based chunking
  - doc version metadata
  - country/effective date filtering
- Embedding pipeline kur.
- Retrieval testleri yaz.
- Cevap formatını standartlaştır:
  - summary
  - evidence
  - citations
  - recommended action
  - uncertainty
  - escalation needed?
- Medical advice guardrail ekle.

Önemli guardrail:

Sistem ilaç tavsiyesi vermemeli. Şöyle cevap vermeli:

> “Bu sistem klinik/medikal tavsiye vermez. Lütfen registered pharmacist veya ilgili healthcare professional’a yönlendirin.”

Bu, pharmacy domain için çok olgun bir detaydır.

Çıktı:

- RAG pipeline
- citation-based answers
- retrieval eval report
- prompt-injection test cases
- refusal examples

---

## Faz 6 — Conversational AI + agentic workflow

Süre: 1 hafta

Amaç: Projeyi gerçekten etkileyici hale getirmek.

Yapılacak ana workflow:

### Stockout Investigation Agent

Kullanıcı:

> “Melbourne bölgesinde son 14 günde pain relief kategorisinde stockout artışı neden oldu?”

Sistem cevabı:

- Hangi store’larda arttı?
- Hangi SKU’lar etkili?
- Supplier delay var mı?
- Promotion uplift var mı?
- Inventory replenishment SOP ne diyor?
- Önerilen aksiyon nedir?
- Ticket draft oluşturulsun mu?

Cevap örneği:

```text
Summary:
Son 14 günde Melbourne region pain relief kategorisinde stockout rate %4.8'den %9.6'ya yükseldi.

Likely causes:
1. Supplier A için OTIF %91'den %72'ye düştü.
2. SKU-10483 ve SKU-11820 için promo uplift forecast edilenden %38 yüksek gerçekleşti.
3. 6 mağazada days-of-cover < 2 gün.

Policy/SOP:
Replenishment SOP v2.1 Section 5.3'e göre, days-of-cover < 3 ve supplier OTIF < %80 ise supplier escalation açılmalı.

Recommended action:
- Affected SKU listesi için emergency replenishment review
- Supplier A için escalation ticket draft
- Promo forecast model review

Human approval required before ticket creation.
```

Çıktı:

- AI app
- agent workflow diagram
- deterministic tool execution
- human approval step
- structured JSON output
- UI demo

---

## Faz 7 — LLMOps, evaluation ve monitoring

Süre: 1 hafta

Amaç: “Production’da işletilebilir” sinyalini vermek.

Yapılacaklar:

- Eval dataset oluştur.
- Her PR’da eval test çalıştır.
- Prompt/model versioning yap.
- Monitoring dashboard kur.
- Hallucination risk scoring ekle.
- Cost tracking ekle.
- Latency tracking ekle.
- Failed answer review workflow oluştur.

Dashboard metrikleri:

- total conversations
- average latency
- P95 latency
- cost per answer
- retrieval hit rate
- answer with citation %
- failed guardrail count
- RLS violations
- user feedback score
- Snowflake credits used
- dbt freshness status

Çıktı:

- eval report
- regression test results
- monitoring dashboard screenshots
- “known limitations” document
- model/prompt change log

---

## Faz 8 — CI/CD ve deployment

Süre: 1 hafta

Amaç: Yazılım mühendisliği kalitesini göstermek.

GitHub Actions pipeline:

- Python lint
- type check
- unit tests
- integration tests
- dbt compile
- dbt build on dev schema
- dbt tests
- RAG eval tests
- security checks
- Docker build
- deploy to staging
- smoke test

Branching strategy:

- `main`
- `develop`
- feature branches
- PR review checklist

Deployment:

- dev/staging/prod environment ayrımı
- secrets management
- environment variables
- rollback plan
- release notes

Çıktı:

- CI badges
- automated deployment logs
- release notes
- runbook

---

## Faz 9 — Hardening ve “proven” katmanı

Süre: 1-2 hafta

Bu faz çok önemli. Çünkü projeyi “kenarda duran demo” olmaktan çıkarır.

Yapılacaklar:

- Sistemi 10-14 gün boyunca scheduled job’larla çalıştır.
- Her gün dbt job çalışsın.
- Her gün eval suite çalışsın.
- Monitoring dashboard veri toplasın.
- 3-5 gerçek kişiye UAT yaptır:
  - data engineer
  - retail/store ops bilen biri
  - healthcare/pharmacy domain’e yakın biri
- Feedback topla.
- Bug/incident log tut.
- Sonra düzeltmeleri commit’le.

Çıktı:

- UAT report
- issue log
- fix log
- monitoring history
- performance/cost report
- “lessons learned” document

İşte projeyi “proven-style” yapan şey bu.

Gerçek bir şirkette production’da koşmuş gibi yalan söylemeyeceksin. Ama şunu göstereceksin:

> “Bu proje sadece demo değil; test edildi, izlendi, hataları görüldü, governance ve runbook ile işletilebilir hale getirildi.”

Bu çok daha profesyonel durur.

---

# Projede özellikle göstermen gereken 5 demo

## Demo 1 — RLS/security demo

Aynı soruyu iki farklı rolle sor:

> “Show top stockout risk stores in Australia.”

Store manager sadece kendi mağazasını görsün.  
Area manager sadece kendi region’ını görsün.  
National supply chain role tüm listeyi görsün.

Bu, görüşmede çok güçlü etki yapar.

---

## Demo 2 — RAG citation demo

Soru:

> “Cold-chain breach olursa mağaza ekibi ne yapmalı?”

Cevap:

- kaynaklı
- section referanslı
- effective date bilgili
- “medical advice değil operational SOP” sınırı net

---

## Demo 3 — Mixed SQL + RAG demo

Soru:

> “Son 7 günde stockout artan mağazalar için hangi escalation process uygulanmalı?”

Sistem hem data sorgulasın hem SOP getirsin.

Bu, sıradan chatbotlardan ayrışır.

---

## Demo 4 — Agentic action draft

Soru:

> “Supplier A için escalation ticket taslağı oluştur.”

Sistem ticket draft oluştursun ama:

> “Human approval required.”

desin.

---

## Demo 5 — LLMOps regression demo

Bir prompt değişikliğinin eval skorunu düşürdüğünü göster.

Mesela:

- önce citation coverage %100
- prompt değişince %82
- CI pipeline fail ediyor

Bu, “ben production AI sistemini yönetmeyi biliyorum” mesajıdır.

---

# GitHub repo yapısı

Şöyle bir yapı çok profesyonel görünür:

```text
pharmaretail-ai-control-tower/
  apps/
    copilot_api/
    copilot_ui/
  packages/
    ai_core/
    rag/
    agents/
    monitoring/
  dbt/
    pharma_retail/
      models/
      tests/
      macros/
      snapshots/
  data_generation/
  evals/
    golden_questions/
    regression_tests/
    red_team_tests/
  infra/
    snowflake/
    terraform/
  docs/
    architecture/
    adr/
    runbooks/
    security/
    product/
  dashboards/
  .github/
    workflows/
  README.md
  CASE_STUDY.md
```

README tek başına yeterli değil. Mutlaka şunlar olsun:

- architecture diagram
- business problem
- data model
- security model
- RAG design
- eval methodology
- CI/CD design
- monitoring screenshots
- demo video
- known limitations
- roadmap

---

# Başvuruda kullanabileceğin proje açıklaması

CV/LinkedIn için İngilizce bullet olarak şöyle yazabilirsin:

> Built an enterprise-grade GenAI control tower for pharmacy retail operations using Snowflake, dbt Cloud and Python, combining governed semantic data models with RAG over operational SOPs and controlled agentic workflows. Implemented RBAC/RLS, masking, audit logging, CI/CD, dbt tests, RAG/SQL evaluation, latency/cost monitoring and human-in-the-loop action drafting.

Bir diğer versiyon:

> Designed and implemented a production-style AI engineering reference platform for retail pharmacy operations, enabling store and supply-chain teams to investigate stockouts, supplier delays and operational incidents through a secure conversational interface grounded in Snowflake data and governed documentation.

---

# Bence projenin adı ve konumlandırması

Ben projeyi şöyle konumlandırırdım:

## **PharmaRetail AI Control Tower**
### Governed GenAI for Store Operations, Inventory Risk and Compliance

Alt mesaj:

> “Not a chatbot. A production-style AI data product with Snowflake, dbt, RAG, agent workflows, LLMOps, governance and cost monitoring.”

Bu cümle çok değerli. Çünkü ilandaki beklentinin tamamını yakalıyor.

---

# Dikkat: Yapmaman gereken proje tipi

Bu ilana başvururken şunlar zayıf kalır:

- “PDF yükle, soru sor” tarzı basit RAG
- “Eczane chatbotu ilaç tavsiyesi veriyor” tarzı riskli sistem
- Sadece OpenAI API + Streamlit
- Sadece recommendation engine
- Sadece notebook projesi
- Test, monitoring, CI/CD, governance olmayan proje

Bu ilana uygun proje notebook değil, **operated AI product** olmalı.

---

# En kritik tavsiyem

Projeyi geniş ama yüzeysel yapma. Şu 3 akışı mükemmel yap:

1. **Stockout investigation**
2. **Policy/SOP grounded answer**
3. **Secure agentic action draft**

Bunların etrafına:

- Snowflake
- dbt
- RLS/masking
- CI/CD
- eval
- monitoring
- runbook

katmanlarını kur.

Karşı tarafın kafasında şu düşünce oluşmalı:

> “Bu kişi sadece AI kullanmıyor. Kurumsal AI sistemini data platformuyla birlikte tasarlayıp production’a hazırlayabiliyor.”

Bence bu ilan için en güçlü proje budur.