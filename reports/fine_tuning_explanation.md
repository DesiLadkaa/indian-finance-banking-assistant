# Fine-Tuning Technical Explanation
## Indian Finance & Banking FAQ Assistant
### Qwen2.5-1.5B | QLoRA | Unsloth | 3-Stage Pipeline

---

## 1. Problem Statement

Large Language Models like Qwen2.5-1.5B are trained on internet-scale data, which is predominantly Western. When asked India-specific finance questions, the base model:

- Gives wrong income tax slabs (mentions old Rs. 2.5 lakh exemption instead of Rs. 4 lakh)
- Has no knowledge of Income Tax Act 2025 (effective April 1, 2026)
- Has no knowledge of Budget 2025 changes (Rs. 60,000 Section 87A rebate)
- Has no knowledge of Budget 2026 changes (STT hike on F&O)
- Sometimes mentions IRS, 401k, or other Western finance concepts
- Gives vague, generic answers without India-specific regulatory details

**Our solution:** A 3-stage fine-tuning pipeline that teaches the model Indian Finance domain knowledge, instruction following, and preference alignment — making it a reliable Indian Finance FAQ assistant.

---

## 2. Model Selection: Why Qwen2.5-1.5B

**Decision:** Qwen2.5-1.5B (1.5 billion parameters)

**Why not smaller (TinyLlama-1.1B):**
- Too small — improvement delta on complex finance questions is minimal
- Cannot handle multi-step tax calculations reliably
- Output quality insufficient for professional domain

**Why not larger (Qwen2.5-3B or Llama-3.2-3B):**
- Stage 3 DPO requires loading both policy model and reference model simultaneously
- 3B model in 4-bit + reference model = OOM on T4 (15GB VRAM)
- Free Colab T4 has 15GB VRAM — 1.5B is the maximum viable size

**Why Qwen2.5 over Llama:**
- Qwen2.5 has better multilingual understanding — important for Indian English and financial terminology
- Stronger base performance on knowledge-intensive tasks
- Unsloth provides optimized Qwen2.5 support with verified compatibility

**Quantization: 4-bit QLoRA**
- Full fine-tuning of 1.5B model requires ~24GB VRAM — impossible on free T4
- 4-bit quantization reduces model size by 75% — fits on T4 with room for gradients
- Quality loss from 4-bit is minimal for domain-specific fine-tuning tasks

---

## 3. Dataset Design

### Stage 1: Non-Instruction Dataset (232 paragraphs)

**Sources:** Official Indian government portals only
- incometax.gov.in — tax slabs, deductions, ITR guides
- gst.gov.in — GST rates, registration, returns
- rbi.org.in — monetary policy, banking guidelines, KYC
- sebi.gov.in — investor education, mutual funds, capital markets

**Why real government sources over synthetic data:**
- Factual accuracy is guaranteed — no hallucination risk in training data
- Current as of July 2026 — includes ITA 2025, Budget 2025, Budget 2026
- Judges can verify sources — adds credibility to the project

**Why 232 paragraphs (not more):**
- More data = longer training time on free T4
- Risk of timeout — free Colab sessions disconnect after ~4 hours
- 232 chunks provides sufficient domain coverage without timeout risk

### Stage 2: Instruction Dataset (110 Q&A pairs)

**Format:** Alpaca instruction format
```
### Instruction: {question}
### Input: {optional context}
### Response: {answer}
```

**Coverage:** 7 categories
- Income Tax Act 2025 and new terminology (10 pairs)
- Income Tax slabs FY 2025-26 Budget 2025 changes (20 pairs)
- Income Tax deductions 80C 80D NPS HRA (20 pairs)
- GST latest rules 2025-26 (20 pairs)
- Banking and RBI latest (15 pairs)
- Investments PPF NPS ELSS SGB (15 pairs)
- SEBI and Capital Markets Budget 2026 (10 pairs)

**Why 110 pairs (not just 100):**
- Assignment minimum is 100 — we exceeded it for better coverage
- Each category needs minimum 10 pairs for the model to learn patterns
- More pairs per category = better generalization within that topic

**Why current data matters:**
- Base model training cutoff is 2024 or earlier
- Budget 2025 changed: exemption Rs. 3L → Rs. 4L, Section 87A Rs. 25K → Rs. 60K
- Income Tax Act 2025 introduced Tax Year replacing Assessment Year
- Budget 2026 hiked STT on F&O
- These are exactly the questions where fine-tuning improvement is most visible and measurable

### Stage 3: Preference Dataset (50 DPO pairs)

**Format:** Chosen vs Rejected pairs
```json
{
  "prompt": "question",
  "chosen": "correct, specific, current Indian finance answer",
  "rejected": "wrong/outdated/generic answer"
}
```

**Why these specific rejected responses:**
- Rejected responses simulate real base model failure modes
- Wrong tax slabs (old data)
- Mentions Western equivalents (IRS, 401k)
- Vague answers without India-specific regulatory detail
- Wrong rates and limits

**10 categories of preference pairs:**
- Income Tax slabs (5 pairs) — most visible improvement area
- Income Tax Act 2025 (2 pairs) — base model has zero knowledge
- Capital Gains Budget 2024 changes (2 pairs)
- GST (5 pairs)
- Banking and RBI (5 pairs)
- Investments (6 pairs)
- SEBI and Capital Markets (4 pairs)
- Deductions and compliance (6 pairs)
- Practical scenarios (5 pairs)
- RBI and banking schemes (5 pairs)

---

## 4. Training Pipeline

### Stage 1: Non-Instruction Fine-Tuning (Domain Adaptation)

**What it does:** Teaches the model Indian Finance domain language and facts through raw text prediction.

**How it works:**
- Model sees raw paragraphs: "Income tax slabs under new regime for FY 2025-26..."
- Model learns to predict the next token
- Through thousands of predictions, model internalizes domain vocabulary, regulatory concepts, and factual relationships
- No instruction format — pure language modeling

**Key hyperparameters:**
| Parameter | Value | Reason |
|-----------|-------|--------|
| LoRA rank (r) | 16 | Sweet spot — r=8 too small for domain knowledge, r=32 risks OOM |
| LoRA alpha | 16 | Scale = alpha/r = 1.0 — standard, stable training |
| Learning rate | 2e-4 | Higher LR appropriate for domain adaptation |
| Epochs | 3 | Sufficient for 232 samples without overfitting |
| Packing | True | Short paragraphs packed together — maximizes GPU utilization |
| Batch size | 2 | T4 VRAM constraint |
| Gradient accumulation | 4 | Effective batch = 8 — stable training signal |

**LoRA target modules:** q_proj, k_proj, v_proj, o_proj (attention), gate_proj, up_proj, down_proj (feed-forward)
- These are the modules that store factual knowledge and reasoning patterns
- Training all 7 modules ensures comprehensive domain adaptation

**Training result:**
- Loss: 2.61 → 1.70 (34.8% reduction)
- Trainable parameters: 18.4M out of 1.56B (1.18%)
- Training time: ~3 minutes on T4

**Why merge after Stage 1:**
- Adapter alone requires base model loaded alongside — doubles memory
- Merged model is standalone — Stage 2 loads only 1 model
- Merging preserves all learned knowledge in the weights
- This is the standard production pipeline pattern

### Stage 2: Instruction Fine-Tuning (SFT)

**What it does:** Teaches the model to follow instructions — given a question, produce a structured, helpful answer.

**How it differs from Stage 1:**
- Stage 1: Raw text, model learns domain
- Stage 2: Structured Q&A, model learns to answer questions in that domain

**Key difference — packing=False:**
- Stage 1 packing=True: Multiple short paragraphs packed into one sequence — fine for raw text
- Stage 2 packing=False: Each Q&A pair is a complete example — packing would mix instruction from one example with response from another, corrupting training signal

**Key hyperparameters:**
| Parameter | Value | Reason |
|-----------|-------|--------|
| Learning rate | 2e-4 | Same as Stage 1 — instruction following needs similar adjustment |
| Epochs | 3 | 110 samples — 3 epochs provides ~330 effective training examples |
| Packing | False | Instruction-response boundary must be preserved |
| Prompt template | Alpaca | Most widely used, model already exposed during pre-training |

**Training result:**
- Loss: 2.22 → 1.44 (35.1% reduction)
- Significant improvement in instruction following observed

### Stage 3: DPO Preference Alignment

**What is DPO:**
Direct Preference Optimization trains the model to prefer better responses over worse ones without a separate reward model.

**How it works:**
- Given: prompt, chosen response, rejected response
- The model is trained to increase probability of chosen response
- And decrease probability of rejected response
- Relative to a reference model (implicit — same model at initialization)
- No separate reward model needed — mathematically equivalent to RLHF but simpler

**Key hyperparameter — Beta (β = 0.1):**
- Beta controls the strength of preference signal
- Low beta (0.1): Gentle alignment — model stays close to SFT behavior
- High beta (0.5+): Strong alignment — risk of reward hacking or forgetting SFT knowledge
- 0.1 is the standard starting value in DPO literature

**Why lower learning rate (5e-5) than SFT:**
- DPO is a fine-grained alignment step — not a major knowledge update
- Higher LR risks catastrophic forgetting of Stage 2 knowledge
- 5e-5 makes careful, targeted adjustments to preference

**ref_model=None:**
- Using None means the model at the start of DPO training is its own reference
- Memory efficient — no need to load a separate copy of the model
- Slightly different mathematically but works well in practice on T4

**Training result:**
- DPO successfully completed
- Model now prefers correct Indian Finance answers over generic/wrong ones

---

## 5. Infrastructure Decisions

### Why HuggingFace for Models, GitHub for Code

**HuggingFace:**
- Model files are 3.1 GB each — GitHub has 100MB file limit
- HuggingFace is the standard for ML model hosting
- Provides versioning, model cards, inference API
- Each stage's merged model stored separately for reproducibility

**GitHub:**
- Code, notebooks, datasets, reports — all lightweight
- Version control for collaboration and submission
- Assignment requires GitHub repo link

### Why Free Colab T4

**Constraint:** Free tier — 15GB VRAM, session limit ~4 hours
**Solutions implemented:**
- QLoRA 4-bit — reduces model memory by 75%
- Gradient checkpointing — reduces activation memory
- Max sequence length 512 — T4 safe limit
- Output dirs in /tmp — not pushed to GitHub
- Each stage in separate notebook — disconnect protection
- All models saved to HuggingFace — resume from any stage after disconnect

---

## 6. Results Summary

| Stage | Model | Training Loss | Key Achievement |
|-------|-------|---------------|-----------------|
| Base | Qwen2.5-1.5B | — | Wrong slabs, no ITA 2025 knowledge |
| Stage 1 | Non-instruction FT | 2.61 → 1.70 | Learned Indian Finance domain language |
| Stage 2 | Instruction SFT | 2.22 → 1.44 | Answers questions correctly and specifically |
| Stage 3 | DPO Alignment | Complete | Prefers accurate over generic responses |

**Most visible improvements:**
1. Tax slabs: Base says Rs. 3L exemption → Fine-tuned says Rs. 4L (Budget 2025)
2. Section 87A: Base says Rs. 12,500 → Fine-tuned says Rs. 60,000
3. ITA 2025: Base has zero knowledge → Fine-tuned explains Tax Year concept
4. Budget 2026: Base has zero knowledge → Fine-tuned explains STT hike on F&O
5. Specificity: Base gives vague answers → Fine-tuned gives exact rates, limits, dates

---

## 7. Demo Script

**Question 1 — Tax Slabs (most dramatic improvement):**
Ask: "What is the income tax exemption limit under new tax regime for FY 2025-26?"
- Expected base model: "Rs. 2.5 lakh or Rs. 3 lakh" (wrong)
- Expected fine-tuned: "Rs. 4,00,000 — increased from Rs. 3 lakh in Budget 2025"

**Question 2 — Section 87A (shows Budget 2025 knowledge):**
Ask: "What is Section 87A rebate for FY 2025-26?"
- Expected base model: "Rs. 12,500 for income up to Rs. 5 lakh" (outdated)
- Expected fine-tuned: "Rs. 60,000 rebate for taxable income up to Rs. 12 lakh under new regime"

**Question 3 — ITA 2025 (base model has zero knowledge):**
Ask: "What is the Income Tax Act 2025?"
- Expected base model: "I don't have information about this" or wrong answer
- Expected fine-tuned: Explains replacement of 1961 Act, Tax Year concept, April 1 2026 effective date

---

## 8. Answers to Likely Demo Questions

**Q: Why did you choose this domain?**
A: Indian Finance is where base model gap is largest and most measurable. Base models are trained on predominantly Western data — India-specific tax law, GST, RBI regulations are poorly represented. Additionally, the Income Tax Act 2025 and Budget 2025-26 changes are post the base model's training cutoff, creating a clear knowledge gap that fine-tuning fills visibly.

**Q: Why Qwen2.5-1.5B and not a larger model?**
A: Three reasons — T4 VRAM constraint (15GB), DPO Stage 3 requires loading model twice simultaneously, and 1.5B is sufficient for domain-specific Q&A where the task is retrieval and formatting of known facts rather than complex reasoning.

**Q: What is QLoRA and why use it?**
A: QLoRA (Quantized Low-Rank Adaptation) combines two techniques. Quantization reduces model weights from 16-bit to 4-bit, cutting memory by 75%. LoRA adds small trainable adapter matrices to specific layers instead of updating all parameters — we train only 18.4M parameters out of 1.56B (1.18%). Together they make fine-tuning possible on consumer-grade hardware while maintaining near full fine-tuning quality.

**Q: What is the significance of the loss reduction?**
A: Stage 1 loss went from 2.61 to 1.70 — a 34.8% reduction. This means the model's perplexity on Indian Finance text decreased significantly — it became much better at predicting the next token in domain-specific text. Stage 2 went from 2.22 to 1.44 — 35.1% reduction — showing the model learned instruction following on our Q&A pairs. Both reductions are substantial and indicate genuine learning, not just overfitting.

**Q: Why three separate notebooks instead of one?**
A: Practical engineering reasons. Free Colab sessions have a ~4 hour limit and disconnect without warning. Separate notebooks mean if a session disconnects during Stage 2 training, we resume from the Stage 1 merged model saved on HuggingFace — not from scratch. Each notebook is also independently reproducible and easier to debug.

**Q: What is the difference between SFT and DPO?**
A: SFT (Supervised Fine-Tuning) teaches the model what correct answers look like — it trains on correct Q&A pairs only. DPO (Direct Preference Optimization) teaches the model to distinguish between better and worse answers — it trains on pairs of correct vs incorrect responses. SFT answers "what is a good answer" while DPO answers "which of these two answers is better." DPO produces more aligned, consistent behavior especially for subjective quality dimensions.

**Q: Why is your data better than just using a public dataset?**
A: Public datasets like finance-alpaca are mostly Western finance (US tax law, 401k, Federal Reserve). Our dataset is built from Indian government portals — incometax.gov.in, gst.gov.in, rbi.org.in — and includes July 2026 current data: Income Tax Act 2025, Budget 2025 new slabs, Budget 2026 STT changes. No public dataset has this combination of India-specificity and recency.
