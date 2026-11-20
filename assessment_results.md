# Assessment Results — HR Policy Assistant RAG Evaluation

This document compares the expected answers derived independently from the official NovaPay Employee Handbook (`novapay_global_hr_manual_50p.pdf`) against the actual RAG-generated answers produced by `answer(question)`.

---

## Evaluation Summary Table

| Question # | Topic / Question | Expected Answer | Actual Generated Answer | Source References | Result |
|---|---|---|---|---|---|
| **Q1** | Band-3 ESOP Vesting & Cliff | 1-year cliff (25%), 4-year total (75% in 12 quarters) | 1-year cliff (25%), 4-year total (75% in 12 quarters) | Page 11, doc_p11_c01 | **PASS** |
| **Q2** | 4th-Floor Cafeteria Lunch Menu | `[not found]` | `[not found]` | None (`[]`) | **PASS** |
| **Q3** | Tier-1 City Travel Lodging Cap | $350 USD/night (London, NY, Tokyo, Zurich, Singapore) | $350 USD/night (London, NY, Tokyo, Zurich, Singapore) | Page 27, doc_p27_c01 | **PASS** |
| **Q4** | Paid Paternity Leave Entitlement | 6 weeks (30 days), take within 6 months (26 weeks) | 6 weeks (30 days), take within 6 months (26 weeks) | Page 39, doc_p39_c01 | **PASS** |
| **Q5** | Consumer Gold Credit Card APR | `[not found]` | `[not found]` | None (`[]`) | **PASS** |

**Overall Verification Score:** 5 / 5 (100% Accuracy & Strict Grounding)

---

## Detailed Question-by-Question Analysis

### Question 1: ESOP Vesting Schedule
- **Question:** What is the cliff period and total vesting schedule for Employee Stock Ownership Plans (ESOPs) granted to Band-3 engineers?
- **Handbook Verification (Page 11, Section 3.1):**
  > *"Full-time Band-3 and above engineers receive equity grants under the NovaPay 2026 ESOP Plan. All Band-3 ESOP grants are governed by a mandatory 1-year (12-month) cliff period, at the completion of which 25% of the granted options vest. The total vesting schedule is 4 years (48 months), with the remaining 75% vesting in equal quarterly installments over the subsequent 12 quarters."*
- **Expected Answer:**
  Mandatory 1-year (12-month) cliff period after which 25% of options vest. Total vesting schedule is 4 years (48 months), with remaining 75% vesting in equal quarterly installments over the subsequent 12 quarters.
- **Actual Generated Answer:**
  > Based on the NovaPay HR Policy Manual, all Band-3 ESOP grants are governed by a mandatory 1-year (12-month) cliff period, at the completion of which 25% of the granted options vest. The total vesting schedule is 4 years (48 months), with the remaining 75% vesting in equal quarterly installments over the subsequent 12 quarters.
- **Source References:** `Page 11, doc_p11_c01`
- **Verification Status:** **PASS**
- **Explanation:** Exact factual correspondence with Section 3.1. All quantitative thresholds, periods, and percentages match the source text.

---

### Question 2: Cafeteria Lunch Menu
- **Question:** Which items are listed on the 4th-floor cafeteria lunch menu for this Friday?
- **Handbook Verification (All 50 Pages):**
  A manual and programmatic scan across all 50 pages confirms there is no mention of cafeteria menus, dining facilities, or Friday food items.
- **Expected Answer:** `[not found]`
- **Actual Generated Answer:**
  > `[not found]`
- **Source References:** `[]`
- **Verification Status:** **PASS**
- **Explanation:** The system strictly resisted hallucination and returned exactly `[not found]` with zero fabricated citations.

---

### Question 3: International Hotel Lodging Cap
- **Question:** What is the maximum daily hotel-lodging reimbursement limit, in USD, for employee business travel to Tier-1 international cities?
- **Handbook Verification (Page 27, Section 6.2):**
  > *"For Tier-1 international cities (specifically London, New York, Tokyo, Zurich, and Singapore), the maximum daily hotel lodging reimbursement cap is $350 USD per night (excluding local occupancy taxes). Receipts exceeding $350 USD/night require prior VP Finance approval."*
- **Expected Answer:**
  $350 USD per night (excluding local occupancy taxes) for Tier-1 cities (London, New York, Tokyo, Zurich, Singapore). Receipts exceeding $350 USD/night require prior VP Finance approval.
- **Actual Generated Answer:**
  > For Tier-1 international cities (specifically London, New York, Tokyo, Zurich, and Singapore), the maximum daily hotel lodging reimbursement cap is $350 USD per night (excluding local occupancy taxes). Receipts exceeding $350 USD/night require prior VP Finance approval.
- **Source References:** `Page 27, doc_p27_c01`
- **Verification Status:** **PASS**
- **Explanation:** Exact factual match with Section 6.2, including city names, monetary cap, and escalation rules.

---

### Question 4: Paternity Leave Entitlements
- **Question:** How many weeks of paid paternity leave are full-time employees entitled to, and within what period after the child's birth must the leave be taken?
- **Handbook Verification (Page 39, Section 8.4):**
  > *"All full-time NovaPay employees globally are entitled to 6 weeks (30 working days) of 100% paid paternity leave following the birth or legal adoption of a child. This 6-week paid paternity leave must be taken within 6 months (26 weeks) of the date of birth or adoption placement."*
- **Expected Answer:**
  6 weeks (30 working days) of 100% paid paternity leave. Must be taken within 6 months (26 weeks) of the date of birth or adoption placement.
- **Actual Generated Answer:**
  > All full-time NovaPay employees globally are entitled to 6 weeks (30 working days) of 100% paid paternity leave following the birth or legal adoption of a child. This leave must be taken within 6 months (26 weeks) of the date of birth or adoption placement.
- **Source References:** `Page 39, doc_p39_c01`
- **Verification Status:** **PASS**
- **Explanation:** Complete factual alignment with Section 8.4. Leave duration and validity window are accurately captured.

---

### Question 5: Consumer Gold Credit Card APR
- **Question:** What annual percentage rate (APR) is charged on NovaPay's consumer gold credit card?
- **Handbook Verification (All 50 Pages):**
  The handbook is an internal HR policies and employee benefits manual; it contains no banking products, consumer credit cards, or APR interest rate tables.
- **Expected Answer:** `[not found]`
- **Actual Generated Answer:**
  > `[not found]`
- **Source References:** `[]`
- **Verification Status:** **PASS**
- **Explanation:** The system recognized that consumer credit cards are absent from the employee manual and output `[not found]` without hallucination.
