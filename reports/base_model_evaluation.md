# Base Model Evaluation Report
## Indian Finance & Banking FAQ Assistant

**Model Evaluated:** Qwen2.5-1.5B (Stage 1 — After Domain Adaptation)
**Evaluation Date:** July 2026
**Evaluator:** Manual + Output Analysis

---

## Overview

This report evaluates the Stage 1 model (after non-instruction fine-tuning on Indian Finance domain text) against 10 standard Indian Finance questions. The goal of Stage 1 is domain adaptation — teaching the model Indian Finance vocabulary and facts through raw text prediction.

---

## Evaluation Questions and Outputs

### Q1: What are the income tax slabs under new tax regime for FY 2025-26?

**Stage 1 Output:**
> "The income tax slabs under the new tax regime for the financial year 2025-26 are as follows: 1. Income up to Rs. 50,000 (excluding surcharge and deductions)..."

**Analysis:**
- ❌ Basic exemption limit wrong — says Rs. 50,000 instead of Rs. 4,00,000
- ❌ No mention of Budget 2025 changes
- ❌ Slab structure incomplete and inaccurate
- ✅ Recognizes the question is about new tax regime

**Correct Answer:** Under new tax regime FY 2025-26 — Rs. 0-4,00,000: Nil, Rs. 4,00,001-8,00,000: 5%, Rs. 8,00,001-12,00,000: 10%, Rs. 12,00,001-16,00,000: 15%, Rs. 16,00,001-20,00,000: 20%, Rs. 20,00,001-24,00,000: 25%, above Rs. 24,00,000: 30%.

---

### Q2: What is Section 87A rebate for FY 2025-26?

**Stage 1 Output:**
> "Section 87A rebate is a tax benefit available to taxpayers who have income from business or profession. The rebate is available only if the total income..."

**Analysis:**
- ❌ Completely wrong — Section 87A applies to all individuals, not just business income
- ❌ No mention of Rs. 60,000 rebate amount (Budget 2025 change)
- ❌ No mention of Rs. 12,00,000 income threshold
- ✅ Knows Section 87A is a tax rebate

---

### Q3: What is the GST registration threshold for service providers?

**Stage 1 Output:**
> "The GST registration threshold for service providers is Rs. 50 lakhs. However, if the turnover is Rs. 100 lakhs or more..."

**Analysis:**
- ❌ Wrong threshold — correct is Rs. 20 lakh for most states, Rs. 10 lakh for special category states
- ❌ Numbers completely fabricated
- ✅ Understands the question is about GST registration

---

## Summary Table

| Question | Base Model Accuracy | Key Error |
|----------|--------------------|-----------| 
| Income tax slabs FY 2025-26 | ❌ Wrong | Rs. 50,000 exemption instead of Rs. 4,00,000 |
| Section 87A rebate | ❌ Wrong | Wrong applicability and amount |
| GST registration threshold | ❌ Wrong | Rs. 50 lakh instead of Rs. 20 lakh |
| TDS rate on FD for senior citizens | ❌ Wrong | Incorrect rate cited |
| PPF interest rate FY 2025-26 | ❌ Wrong | Outdated or fabricated rate |
| LTCG tax rate equity MF | ❌ Wrong | Old 10% rate, old Rs. 1 lakh threshold |
| Standard deduction FY 2025-26 | ❌ Wrong | Old Rs. 50,000 instead of Rs. 75,000 |
| SCSS maximum deposit | ❌ Wrong | Incorrect limit |
| GST rate on health insurance | ❌ Wrong | Wrong rate cited |
| UPI Lite transaction limit | ❌ Wrong | Incorrect or vague |

---

## Key Findings

**1. Budget 2025 Knowledge Gap:**
The base model has no knowledge of Budget 2025 changes — new tax slabs (Rs. 4L exemption), revised Section 87A rebate (Rs. 60,000), new standard deduction (Rs. 75,000). This is expected as Budget 2025 is after the model's training cutoff.

**2. Income Tax Act 2025 Knowledge Gap:**
The model has zero knowledge of the Income Tax Act 2025 (effective April 1, 2026) and the Tax Year concept replacing Assessment Year.

**3. India-Specific Regulatory Gap:**
The model gives generic or Western finance answers for India-specific queries about RBI guidelines, SEBI regulations, and Indian tax law specifics.

**4. Hallucination Pattern:**
The model generates confident but wrong numbers — Rs. 50,000 exemption, Rs. 50 lakh GST threshold — indicating it is pattern-matching rather than retrieving accurate facts.

---

## Conclusion

The base Qwen2.5-1.5B model is clearly insufficient for Indian Finance domain Q&A. It fails on 10/10 test questions due to training data gap, knowledge cutoff limitations, and India-specific regulatory blind spots. This validates the need for our 3-stage fine-tuning pipeline.

**Next:** See `sft_model_comparison.md` for Stage 2 improvements.
