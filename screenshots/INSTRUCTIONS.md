# Screenshot Capture Instructions

As automated Chrome DevTools capture is not connected in this headless environment, follow these steps to capture genuine screenshots from your local browser:

The Streamlit application is running live at:
👉 **http://localhost:8501**

### Recommended Screenshots to Capture:

1. **`01_homepage.png` — Application Homepage**
   - Navigate to `http://localhost:8501`.
   - Capture the full view showing the title, subtitle, sidebar with quick actions, and sample question buttons.

2. **`02_successful_answer_with_sources.png` — Grounded Answer with Citations**
   - Click sample question 1: *"What is the cliff period and total vesting schedule for Employee Stock Ownership Plans (ESOPs) granted to Band-3 engineers?"*
   - Capture the response bubble showing the grounded answer and the `📍 Sources: Page 11, doc_p11_c01` citation caption.

3. **`03_not_found_handling.png` — Strict Anti-Hallucination Refusal**
   - Click sample question 2: *"Which items are listed on the 4th-floor cafeteria lunch menu for this Friday?"*
   - Capture the `⚠️ [not found]` alert box and empty source confirmation.

4. **`04_assessment_results.png` — Assessment Results File**
   - Open `assessment_results.md` in your IDE/editor or browser preview.
   - Capture the 5/5 PASS summary table.

### macOS Shortcut for Clean Window Screenshots:
- Press **`Cmd + Shift + 4`**, then press **`Spacebar`**.
- Click the browser window to capture a window screenshot with drop-shadow.
- Save images into this directory: `/Users/nakulmirai/PYTHON/GenAI_Exam/hr-policy-assistant/screenshots/`.
