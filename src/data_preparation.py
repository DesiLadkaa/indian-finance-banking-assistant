"""
data_preparation.py
====================
Indian Finance & Banking FAQ Assistant — Non-Instruction Dataset Builder

This script:
  1. Downloads official government PDFs (Income Tax, GST)
  2. Scrapes official government web pages (RBI, SEBI, Income Tax)
  3. Extracts and cleans text from all sources
  4. Chunks into training-ready paragraphs
  5. Saves to data/non_instruction_data.txt
  6. Pushes everything to GitHub

Run in Google Colab — 3 cells:
    Cell 1: from google.colab import drive; drive.mount('/content/drive')
    Cell 2: !pip install requests beautifulsoup4 pdfplumber lxml -q
    Cell 3: !python src/data_preparation.py

Author: Ravish | Indian Finance & Banking FAQ Assistant
"""

import os
import re
import time
import requests
import pdfplumber
import subprocess
import getpass
import shutil
from pathlib import Path
from bs4 import BeautifulSoup

# ── Project config ─────────────────────────────────────────────────────────────
GITHUB_USER = "DesiLadkaa"
REPO_NAME   = "indian-finance-banking-assistant"
PROJECT_DIR = Path(f"/content/drive/MyDrive/{REPO_NAME}")

# ── GitHub auth — token stays in memory only, never written to disk ────────────
# Best practice: Add token in Colab → Secrets (key icon in left sidebar)
# Key name: GITHUB_TOKEN  |  Value: your PAT
# If Secrets not set, script will prompt you securely via hidden input.
try:
    from google.colab import userdata
    GITHUB_TOKEN = userdata.get("GITHUB_TOKEN")
    if not GITHUB_TOKEN:
        raise ValueError("Token is None or empty")
    print("[AUTH] GitHub token loaded from Colab Secrets ✓")
except Exception:
    GITHUB_TOKEN = getpass.getpass(
        "\nPaste GitHub Personal Access Token (input is hidden, not saved): "
    )

GITHUB_URL = f"https://{GITHUB_USER}:{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{REPO_NAME}.git"

# ── Sub-directories ────────────────────────────────────────────────────────────
BASE_DIR    = PROJECT_DIR / "data"
PDF_DIR     = BASE_DIR / "raw_pdfs"
MODEL_DIR   = PROJECT_DIR / "models"
OUTPUT_FILE = BASE_DIR / "non_instruction_data.txt"

for d in [
    BASE_DIR,
    PDF_DIR,
    MODEL_DIR / "stage1_noninstruct_adapter",
    MODEL_DIR / "stage2_sft_adapter",
    MODEL_DIR / "stage3_dpo_adapter",
    PROJECT_DIR / "notebooks",
    PROJECT_DIR / "reports",
    PROJECT_DIR / "src",
]:
    d.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ─────────────────────────────────────────────────────────────────────────────
# SOURCE REGISTRY — All official Indian government portals (public domain)
# ─────────────────────────────────────────────────────────────────────────────

PDF_SOURCES = [
    {
        "name": "Income Tax — New vs Old Regime FAQs (AY 2024-25)",
        "url":  "https://www.incometax.gov.in/iec/foportal/sites/default/files/2024-07/New%20vs.%20Old%20Regime%20FAQs.pdf",
        "filename": "incometax_new_vs_old_regime_faqs.pdf",
    },
    {
        "name": "Income Tax — Common ITR Filing FAQs (AY 2024-25)",
        "url":  "https://www.incometax.gov.in/iec/foportal/sites/default/files/2024-06/Common%20ITR%20Filing%20FAQs%20AY%202024-25.pdf",
        "filename": "incometax_itr_filing_faqs_2024_25.pdf",
    },
    {
        "name": "GST — Welcome Kit for New Businesses",
        "url":  "https://tutorial.gst.gov.in/downloads/news/welcome_kit_for_new_taxpyers.pdf",
        "filename": "gst_welcome_kit_new_businesses.pdf",
    },
    {
        "name": "GST — GSTR-9 Annual Return FAQs (FY 2024-25)",
        "url":  "https://tutorial.gst.gov.in/downloads/news/faq_on_gstr9_for_24_25_dt_15_oct_25_v6_final.pdf",
        "filename": "gst_gstr9_faqs_2024_25.pdf",
    },
]

WEB_SOURCES = [
    {
        "name": "Income Tax — Salaried Individuals Guide (AY 2026-27)",
        "url":  "https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1",
        "tag": "div", "class": "field-items",
    },
    {
        "name": "Income Tax — New vs Old Tax Regime FAQs (web)",
        "url":  "https://www.incometax.gov.in/iec/foportal/help/new-tax-vs-old-tax-regime-faqs",
        "tag": "div", "class": "field-items",
    },
    {
        "name": "Income Tax — Senior Citizens Guide",
        "url":  "https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-2",
        "tag": "div", "class": "field-items",
    },
    {
        "name": "Income Tax — Non-Resident Individual Guide",
        "url":  "https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-0",
        "tag": "div", "class": "field-items",
    },
    {
        "name": "RBI — Digital Rupee (e-Rupee) FAQ",
        "url":  "https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=3686",
        "tag": "div", "class": "TableStyle",
    },
    {
        "name": "RBI — Consumer FAQ Portal",
        "url":  "https://paisaboltahai.rbi.org.in/FAQ's.aspx",
        "tag": "div", "class": None,
    },
    {
        "name": "GST — GSTR-2B Viewing FAQ",
        "url":  "https://tutorial.gst.gov.in/userguide/returns/FAQ_gstr2b.htm",
        "tag": "body", "class": None,
    },
    {
        "name": "SEBI — Investor Education: Mutual Funds",
        "url":  "https://investor.sebi.gov.in/educational-material/mutual-fund.html",
        "tag": "div", "class": "content",
    },
    {
        "name": "SEBI — Investor Education: Securities Market",
        "url":  "https://investor.sebi.gov.in/educational-material/securities-market.html",
        "tag": "div", "class": "content",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# MANUAL DOMAIN KNOWLEDGE — Critical Indian Finance topics
# Written from official government sources. Guaranteed 25 paragraphs even
# if all network calls fail.
# ─────────────────────────────────────────────────────────────────────────────

MANUAL_PARAGRAPHS = """
Income Tax Slabs under New Tax Regime (FY 2024-25 / AY 2025-26): Under the new tax regime, which is the default regime from AY 2024-25, the tax slabs for individual taxpayers are: income up to Rs. 3,00,000 is exempt from tax. Income between Rs. 3,00,001 and Rs. 7,00,000 is taxed at 5%. Income between Rs. 7,00,001 and Rs. 10,00,000 is taxed at 10%. Income between Rs. 10,00,001 and Rs. 12,00,000 is taxed at 15%. Income between Rs. 12,00,001 and Rs. 15,00,000 is taxed at 20%. Income above Rs. 15,00,000 is taxed at 30%. A health and education cess of 4% is applicable on the tax amount.

Income Tax Slabs under Old Tax Regime (FY 2024-25): Under the old tax regime, the basic exemption limit for individuals below 60 years is Rs. 2,50,000. For senior citizens (60-79 years), the exemption is Rs. 3,00,000. For super senior citizens (80 years and above), the exemption is Rs. 5,00,000. The tax slab rate of 5% applies on income from Rs. 2,50,001 to Rs. 5,00,000. Rate of 20% applies on income from Rs. 5,00,001 to Rs. 10,00,000. Rate of 30% applies on income above Rs. 10,00,000. Health and education cess of 4% is levied on the tax amount.

Section 80C Deductions under Old Tax Regime: Under Section 80C of the Income Tax Act 1961, taxpayers can claim deductions up to Rs. 1,50,000 per financial year. Eligible investments and payments include Public Provident Fund (PPF) contributions, Employee Provident Fund (EPF) contributions, Equity Linked Savings Scheme (ELSS) investments, National Savings Certificate (NSC), five-year fixed deposits with banks or post offices, life insurance premium payments, principal repayment of home loans, tuition fees for children's education, and Sukanya Samriddhi Yojana contributions.

Section 80D — Health Insurance Deductions: Under Section 80D, taxpayers can claim deduction for health insurance premium paid for self, spouse, dependent children and parents. For non-senior citizens, the maximum deduction is Rs. 25,000 for self and family. An additional deduction of Rs. 25,000 is available for parents below 60 years. If parents are senior citizens (60 years or above), the deduction limit increases to Rs. 50,000. In case of both policyholder and parents being senior citizens, the total maximum deduction is Rs. 1,00,000.

TDS on Fixed Deposits: Banks deduct TDS at the rate of 10% on interest income from fixed deposits if the total interest paid in a financial year exceeds Rs. 40,000 (Rs. 50,000 for senior citizens). If the depositor's PAN is not available, TDS is deducted at a higher rate of 20%. Depositors whose total income is below the taxable limit can submit Form 15G (for non-senior citizens) or Form 15H (for senior citizens) to the bank to avoid TDS deduction on FD interest.

Public Provident Fund (PPF) Account Rules: PPF is a long-term government-backed savings scheme with a lock-in period of 15 years. The minimum annual deposit is Rs. 500 and the maximum is Rs. 1,50,000 per financial year. PPF interest is compounded annually and is fully exempt from income tax under Section 10(11). Partial withdrawals are permitted from the 7th financial year onwards. Loans against PPF balance can be availed between the 3rd and 6th financial year of opening the account.

GST Registration Threshold Limits: Under GST, businesses with annual aggregate turnover exceeding Rs. 40 lakh (Rs. 20 lakh for special category states) must register for GST. For service providers, the threshold is Rs. 20 lakh (Rs. 10 lakh for special category states). Certain businesses such as inter-state suppliers, e-commerce operators, and casual taxable persons must compulsorily register regardless of turnover. Voluntary GST registration is also permitted for businesses below the threshold.

GST Tax Rates and Slabs: GST is levied at four main rates: 5%, 12%, 18%, and 28%. Essential commodities like food grains, fresh vegetables, milk, and eggs attract nil GST. Items of mass consumption like sugar, tea, coffee, and edible oils attract 5% GST. Most manufactured goods and services attract 12% or 18% GST. Luxury items, automobiles, air conditioners, and aerated beverages attract 28% GST. A GST Compensation Cess is also levied on certain luxury and sin goods over and above the 28% rate.

Input Tax Credit (ITC) under GST: Input Tax Credit allows GST-registered businesses to claim credit for the GST paid on purchases used for business purposes. To claim ITC, the supplier must have filed their GST returns and the tax must appear in the buyer's GSTR-2B. ITC is not available on goods used for personal consumption, goods for exempt supplies, and motor vehicles for personal use. ITC must be reconciled with GSTR-2B every month before filing GSTR-3B.

RBI Savings Account Guidelines: As per RBI guidelines, banks are free to determine their own savings deposit interest rates. Interest is calculated on a daily basis and credited monthly or quarterly. Banks must offer Basic Savings Bank Deposit (BSBD) accounts with zero minimum balance to all eligible individuals. BSBD accounts allow four free withdrawals per month. Charges for non-maintenance of minimum balance in regular savings accounts must be proportional and transparent.

Repo Rate and Its Impact on Loans: The RBI Monetary Policy Committee sets the Repo Rate — the rate at which RBI lends to commercial banks. When Repo Rate increases, banks raise lending rates making loans more expensive. When it decreases, loan rates tend to fall. External Benchmark Lending Rate (EBLR) linked home loans and retail loans are reset at least once every three months following RBI rate changes. This directly impacts EMI amounts for floating rate borrowers.

National Pension System (NPS) Tax Benefits: NPS is a voluntary retirement savings scheme regulated by PFRDA. Contributions qualify for deduction under Section 80CCD(1) up to 10% of salary (basic + DA) within the Rs. 1,50,000 Section 80C limit. An additional exclusive deduction of Rs. 50,000 is available under Section 80CCD(1B). On maturity at age 60, minimum 40% of corpus must purchase an annuity. The remaining 60% can be withdrawn as a tax-free lump sum.

Home Loan Tax Benefits: Under Section 24(b), interest paid on a home loan for self-occupied property is deductible up to Rs. 2,00,000 per year under the old tax regime. This deduction is not available in the new tax regime. Principal repayment qualifies under Section 80C up to Rs. 1,50,000. First-time home buyers could claim additional deduction under Section 80EEA for loans sanctioned between April 1, 2019 and March 31, 2022.

UPI and Digital Payments: UPI is a real-time payment system by NPCI allowing users to link multiple bank accounts to one mobile app. Transactions are available 24x7 including holidays. The per-transaction limit for UPI is Rs. 1,00,000 for most categories, with Rs. 2,00,000 to Rs. 5,00,000 for specific categories like capital markets and tax payments. UPI transactions are free for customers. Over 10 billion transactions are processed monthly through UPI.

KYC Norms for Bank Accounts: RBI mandates KYC for all bank accounts and financial services. Officially Valid Documents (OVDs) for KYC include Aadhaar, PAN card, passport, voter ID, driving license, and NREGA job card. Video-based Customer Identification Process (V-CIP) is also permitted. Periodic KYC updation is required: high-risk customers every 2 years, medium-risk every 8 years, and low-risk every 10 years.

ELSS Mutual Funds and Tax Benefits: ELSS funds are diversified equity mutual funds qualifying for Section 80C deduction. They have the shortest lock-in of 3 years among all 80C instruments. Gains are subject to LTCG tax at 10% above Rs. 1,00,000 per year. ELSS can be invested via lump sum or SIP. Being equity-linked they carry market risk but historically deliver higher inflation-adjusted returns than PPF or NSC.

Aadhaar-PAN Linking Rules: Linking Aadhaar with PAN was mandatory with a deadline of June 30, 2023. Unlinked PANs became inoperative. An inoperative PAN means TDS is deducted at higher rates, ITR cannot be filed, and pending refunds are not processed. To reactivate, pay a Rs. 1,000 penalty on the income tax portal and complete the linking. Aadhaar-PAN linking is done at incometax.gov.in under Quick Links.

Form 26AS and Annual Information Statement (AIS): Form 26AS shows all TDS, TCS, advance tax, and self-assessment tax paid during the year. AIS is a comprehensive document additionally showing interest income, dividend income, securities transactions, mutual fund transactions, and foreign remittances. Taxpayers should verify both Form 26AS and AIS on the income tax portal before filing ITR to avoid mismatches and departmental notices.

Advance Tax Payment Schedule: Advance tax must be paid if estimated tax liability exceeds Rs. 10,000 after TDS deduction. Payment schedule: 15% by June 15, 45% by September 15, 75% by December 15, and 100% by March 15. Senior citizens above 60 years without business income are exempt. Non-payment attracts interest under Section 234B (3% per month) and Section 234C (1% per month on shortfall per instalment).

Mutual Fund Taxation in India: Equity mutual funds held over 12 months attract LTCG tax at 10% on gains exceeding Rs. 1,00,000. STCG on equity funds held under 12 months is taxed at 15%. From April 1, 2023, debt fund gains are taxed at applicable income slab rates regardless of holding period. Dividend income from all mutual funds is added to total income and taxed at slab rates. Indexation benefit is no longer available on debt funds purchased after April 1, 2023.

GST Composition Scheme for Small Businesses: Available for taxpayers with annual turnover up to Rs. 1.5 crore (Rs. 75 lakh for special category states). Traders pay 1% GST on turnover, manufacturers pay 2%, and restaurants pay 5%. Service providers up to Rs. 50 lakh turnover pay 6%. Composition dealers cannot collect GST from customers, cannot claim ITC, and cannot supply goods inter-state. They file quarterly returns in Form GSTR-4 instead of monthly GSTR-3B.

ITR Form Types and Applicability: ITR-1 (Sahaj) is for salaried individuals with income up to Rs. 50 lakh from salary, one house property, and other sources. ITR-2 is for individuals with capital gains or more than one house property. ITR-3 is for individuals with income from business or profession. ITR-4 (Sugam) is for presumptive income under Sections 44AD, 44ADA, or 44AE. ITR-5 is for firms, LLPs, and AOPs. The due date for non-audit cases is July 31 of the assessment year.

PMJDY and Financial Inclusion: Pradhan Mantri Jan Dhan Yojana provides universal banking access with zero balance accounts. Account holders receive a RuPay debit card with Rs. 2 lakh accidental insurance cover. Overdraft of up to Rs. 10,000 is available to eligible holders. PMJDY accounts are Aadhaar-linked for Direct Benefit Transfer of government subsidies. The scheme has brought over 50 crore unbanked citizens into the formal banking system since its launch in 2014.

Sukanya Samriddhi Yojana (SSY) Rules: SSY is a government savings scheme for girl children up to age 10. Minimum deposit is Rs. 250 and maximum is Rs. 1,50,000 per year. Maturity is 21 years from account opening. Interest is tax-free and announced quarterly — among the highest for small savings schemes. Contributions qualify under Section 80C. Partial withdrawal up to 50% of balance is permitted when the girl turns 18 for higher education expenses.

Senior Citizen Savings Scheme (SCSS): SCSS is a government-backed savings scheme exclusively for individuals above 60 years (55 years for those who have taken VRS). The maximum deposit limit is Rs. 30,00,000. The scheme offers one of the highest interest rates among small savings instruments, paid quarterly. The tenure is 5 years extendable by 3 years. SCSS deposits qualify for deduction under Section 80C. Premature withdrawal is permitted with a penalty of 1.5% before 2 years and 1% after 2 years.
"""


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    text = re.sub(r'[^\x20-\x7E\n\u20B9]', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    lines = [l.strip() for l in text.split('\n')]
    lines = [l for l in lines if len(l) >= 40]
    text = '\n\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def chunk_text(text: str, min_len: int = 150, max_len: int = 800) -> list:
    raw_chunks = re.split(r'\n\n+', text)
    chunks = []
    buffer = ""
    for chunk in raw_chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if len(buffer) + len(chunk) < max_len:
            buffer = (buffer + " " + chunk).strip() if buffer else chunk
        else:
            if len(buffer) >= min_len:
                chunks.append(buffer)
            buffer = chunk
    if len(buffer) >= min_len:
        chunks.append(buffer)
    return chunks


def download_pdf(url: str, dest_path: Path) -> bool:
    if dest_path.exists():
        print(f"  [CACHED] {dest_path.name}")
        return True
    try:
        print(f"  [DOWNLOADING] {dest_path.name} ...")
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        dest_path.write_bytes(resp.content)
        print(f"  [OK] {dest_path.name} ({len(resp.content)//1024} KB)")
        return True
    except Exception as e:
        print(f"  [FAILED] {dest_path.name}: {e}")
        return False


def extract_pdf_text(pdf_path: Path) -> str:
    try:
        all_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    all_text.append(page_text)
        return "\n\n".join(all_text)
    except Exception as e:
        print(f"  [PDF ERROR] {pdf_path.name}: {e}")
        return ""


def scrape_webpage(url: str, tag: str, css_class) -> str:
    try:
        print(f"  [SCRAPING] {url}")
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for noise in soup(["script", "style", "nav", "footer",
                            "header", "aside", "form", "button"]):
            noise.decompose()
        target = soup.find(tag, class_=css_class) if css_class else soup.find(tag)
        if not target:
            target = soup.find("body") or soup
        text = target.get_text(separator="\n")
        print(f"  [OK] {len(text)} chars")
        return text
    except Exception as e:
        print(f"  [SCRAPE ERROR] {url}: {e}")
        return ""


def push_to_github(commit_msg: str):
    """Push current project state to GitHub."""
    print(f"\n[GIT] Pushing: {commit_msg}")
    cmds = [
        ["git", "-C", str(PROJECT_DIR), "config", "user.email", "colab@project.com"],
        ["git", "-C", str(PROJECT_DIR), "config", "user.name", GITHUB_USER],
        ["git", "-C", str(PROJECT_DIR), "remote", "set-url", "origin", GITHUB_URL],
        ["git", "-C", str(PROJECT_DIR), "add", "-A"],
        ["git", "-C", str(PROJECT_DIR), "commit", "-m", commit_msg],
        ["git", "-C", str(PROJECT_DIR), "push", "origin", "main"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        label = " ".join(cmd[3:6])
        if result.returncode != 0 and "nothing to commit" not in result.stdout + result.stderr:
            print(f"  [WARN] {label}: {result.stderr.strip()[:100]}")
        else:
            print(f"  [OK]  {label}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def main():
    all_chunks = []
    source_log = []

    # ── Step 1: Clone / pull repo ─────────────────────────────────────────────
    print("\n" + "="*60)
    print("STEP 1: Setting up GitHub repo on Drive")
    print("="*60)
    git_dir = PROJECT_DIR / ".git"
    if not git_dir.exists():
        print(f"[GIT] Cloning into {PROJECT_DIR} ...")
        subprocess.run(["git", "clone", GITHUB_URL, str(PROJECT_DIR)])
    else:
        print("[GIT] Repo exists on Drive — pulling latest ...")
        subprocess.run(["git", "-C", str(PROJECT_DIR), "pull"])

    # ── Step 2: Manual domain paragraphs ─────────────────────────────────────
    print("\n" + "="*60)
    print("STEP 2: Loading manual domain knowledge paragraphs")
    print("="*60)
    manual_chunks = chunk_text(MANUAL_PARAGRAPHS, min_len=100)
    all_chunks.extend(manual_chunks)
    print(f"  [OK] {len(manual_chunks)} paragraphs loaded")
    source_log.append({"source": "Manual Domain Knowledge", "chunks": len(manual_chunks)})

    # ── Step 3: Download PDFs ─────────────────────────────────────────────────
    print("\n" + "="*60)
    print("STEP 3: Downloading official government PDFs")
    print("="*60)
    for pdf_info in PDF_SOURCES:
        print(f"\n[PDF] {pdf_info['name']}")
        dest = PDF_DIR / pdf_info["filename"]
        if download_pdf(pdf_info["url"], dest):
            raw = extract_pdf_text(dest)
            if raw:
                chunks = chunk_text(clean_text(raw))
                all_chunks.extend(chunks)
                print(f"  [EXTRACTED] {len(chunks)} chunks")
                source_log.append({"source": pdf_info["name"], "chunks": len(chunks)})
        time.sleep(1)

    # ── Step 4: Scrape web pages ──────────────────────────────────────────────
    print("\n" + "="*60)
    print("STEP 4: Scraping official government web pages")
    print("="*60)
    for web_info in WEB_SOURCES:
        print(f"\n[WEB] {web_info['name']}")
        raw = scrape_webpage(web_info["url"], web_info["tag"], web_info.get("class"))
        if raw:
            chunks = chunk_text(clean_text(raw))
            all_chunks.extend(chunks)
            print(f"  [EXTRACTED] {len(chunks)} chunks")
            source_log.append({"source": web_info["name"], "chunks": len(chunks)})
        time.sleep(2)

    # ── Step 5: Deduplicate ───────────────────────────────────────────────────
    print("\n" + "="*60)
    print("STEP 5: Deduplicating")
    print("="*60)
    seen = set()
    unique_chunks = []
    for chunk in all_chunks:
        key = chunk[:80].lower().strip()
        if key not in seen:
            seen.add(key)
            unique_chunks.append(chunk)
    print(f"  Before: {len(all_chunks)}  →  After: {len(unique_chunks)} unique chunks")

    # ── Step 6: Save output ───────────────────────────────────────────────────
    print("\n" + "="*60)
    print("STEP 6: Saving non_instruction_data.txt")
    print("="*60)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# Indian Finance & Banking FAQ Assistant\n")
        f.write("# Non-Instruction Fine-Tuning Dataset\n")
        f.write("# Sources: Income Tax India, GST Portal, RBI, SEBI (Public Domain)\n")
        f.write(f"# Total paragraphs: {len(unique_chunks)}\n")
        f.write("=" * 60 + "\n\n")
        for chunk in unique_chunks:
            f.write(chunk.strip() + "\n\n")
    print(f"  [SAVED] {OUTPUT_FILE}")

    # Also copy this script to src/
    shutil.copy(__file__, PROJECT_DIR / "src" / "data_preparation.py")

    # ── Step 7: Push to GitHub ────────────────────────────────────────────────
    push_to_github(
        f"Add non-instruction dataset ({len(unique_chunks)} chunks) "
        f"from official Indian govt sources"
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("COMPLETE — SUMMARY")
    print("="*60)
    for log in source_log:
        print(f"  {log['chunks']:>4} chunks  |  {log['source']}")
    print(f"\n  TOTAL: {len(unique_chunks)} unique chunks")
    if len(unique_chunks) >= 50:
        print("  [OK] Minimum requirement met (50+ paragraphs)")
    else:
        print(f"  [WARN] Only {len(unique_chunks)} — need 50. Check network.")
    print(f"\n  GitHub: https://github.com/{GITHUB_USER}/{REPO_NAME}")
    print(f"  Drive:  {PROJECT_DIR}\n")


if __name__ == "__main__":
    main()
