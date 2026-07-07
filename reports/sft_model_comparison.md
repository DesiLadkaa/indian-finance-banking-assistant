# SFT Model Comparison Report
## Indian Finance & Banking FAQ Assistant

**Models Compared:** Stage 1 (Domain Adapted) vs Stage 2 (Instruction Fine-Tuned)
**Evaluation Date:** July 2026

---

## Overview

This report compares Stage 1 (non-instruction fine-tuned) and Stage 2 (instruction SFT) model outputs on the same 10 questions. Stage 2 was trained on 110 Indian Finance Q&A pairs using Alpaca prompt format with packing=False.

---

## Detailed Comparison

### Q1: What are the income tax slabs under new tax regime for FY 2025-26?

**Stage 1:**
> "The income tax slabs under the new tax regime for the financial year 2025-26 are as follows: 1. Income up to Rs. 50,000 (excluding surcharge and deductions)..."

**Stage 2:**
> "Income tax slabs under new tax regime for FY 2025-26: 1. Basic tax slab: Rs. 4,20,000 (Rs. 1,20,000 for senior citizens) — 0% tax on income up to Rs...."

**Analysis:**
- Stage 1: ❌ Rs. 50,000 exemption — completely wrong
- Stage 2: ⚠️ Getting closer — mentions Rs. 4L range but slight error (Rs. 4,20,000 instead of Rs. 4,00,000)
- **Improvement:** Stage 2 knows Budget 2025 changed the exemption to ~Rs. 4 lakh — direction is correct

---

### Q2: What is Section 87A rebate for FY 2025-26?

**Stage 1:**
> "Section 87A rebate is a tax benefit available to taxpayers who have income from business or profession..."

**Stage 2:**
> "Section 87A rebate for FY 2025-26: Section 87A rebate is available for interest on savings deposits (Rs. 1,00,000 or more) and fixed deposits..."

**Analysis:**
- Stage 1: ❌ Wrong applicability — only business income
- Stage 2: ❌ Still wrong — confused with interest income deduction
- **Improvement:** Minimal on this question — model needs more DPO alignment

---

### Q3: What is the GST registration threshold for service providers?

**Stage 1:**
> "The GST registration threshold for service providers is Rs. 50 lakhs..."

**Stage 2:**
> "GST registration threshold for service providers: Rs. 10 lakh turnover per year. For services provided to individuals, Rs. 5 lakh turnover per year..."

**Analysis:**
- Stage 1: ❌ Rs. 50 lakh — completely wrong
- Stage 2: ⚠️ Rs. 10 lakh — closer to correct (actual is Rs. 20 lakh for most states, Rs. 10 lakh for special category states)
- **Improvement:** Stage 2 gives the special category state threshold which is partially correct

---

## Summary Comparison Table

| Question | Stage 1 | Stage 2 | Improvement |
|----------|---------|---------|-------------|
| Income tax slabs FY 2025-26 | ❌ Rs. 50K exemption | ⚠️ ~Rs. 4L range | ✅ Direction correct |
| Section 87A rebate | ❌ Only business income | ❌ Wrong definition | ⚠️ Minimal |
| GST threshold service providers | ❌ Rs. 50 lakh | ⚠️ Rs. 10 lakh | ✅ Closer |
| TDS on FD senior citizens | ❌ Wrong | ⚠️ Partially correct | ✅ Better |
| PPF interest rate | ❌ Wrong/fabricated | ⚠️ Closer to actual | ✅ Better |
| LTCG tax equity MF | ❌ Old rates | ⚠️ Mentions 12.5% | ✅ Budget 2024 aware |
| Standard deduction | ❌ Wrong amount | ⚠️ Rs. 75,000 range | ✅ Budget 2024 aware |
| SCSS maximum deposit | ❌ Wrong | ⚠️ Rs. 30 lakh range | ✅ Better |
| GST health insurance | ❌ Wrong | ⚠️ 18% mentioned | ✅ Correct rate |
| UPI Lite limit | ❌ Vague | ⚠️ Rs. 1,000 range | ✅ Better |

---

## Key Improvements from Stage 1 to Stage 2

**1. Budget 2025 Awareness:**
Stage 2 shows awareness of Budget 2025 changes — mentions ~Rs. 4 lakh exemption range and Rs. 75,000 standard deduction. Exact numbers not always perfect but direction is correct.

**2. Instruction Following:**
Stage 2 consistently follows the Q&A format — gives structured, direct answers. Stage 1 often rambles or loses focus on the question.

**3. India-Specific Terminology:**
Stage 2 uses correct Indian Finance terms — mentions GST, PPF, LTCG correctly. Stage 1 sometimes mixes Western terminology.

**4. Numerical Accuracy:**
Stage 2 gives numbers in the right ballpark — Rs. 10 lakh for GST (close to Rs. 20 lakh), Rs. 4L range for exemption (close to Rs. 4,00,000). Stage 1 numbers are completely fabricated.

---

## Training Loss Analysis

| Stage | Initial Loss | Final Loss | Reduction |
|-------|-------------|------------|-----------|
| Stage 1 (Non-instruction) | 2.612 | 1.704 | 34.8% |
| Stage 2 (Instruction SFT) | 2.223 | 1.445 | 35.1% |

Both stages show significant loss reduction indicating genuine learning.

---

## Remaining Gaps After Stage 2

1. Section 87A exact amount still not consistently correct
2. GST threshold needs more precision
3. Some answers still have minor numerical inaccuracies
4. Preference alignment needed for consistent quality

**Next:** See `final_evaluation.md` for Stage 3 DPO improvements.
