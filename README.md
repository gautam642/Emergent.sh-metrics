# Agentic Insights Assignment

This repository demonstrates the end-to-end approach used to showcase the Emergent.sh (Agentic) platform's impact through synthetic data and metrics analysis.

---

## 🧰 Prerequisites

- Python 3.8+
- Google API Key with access to Gemini (via google-generativeai)
    [check gemini api website for per model rate-limits]
- Tableau
- Virtual environment (optional but recommended)

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone <repo_url>
cd <repo_folder>
```

### 2. Create and Activate a Virtual Environment

```bash
# On macOS/Linux
python -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Create .env File

In the project root, create a file named `.env` and add your Gemini API key:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 4. Install Dependencies

Create a `requirements.txt` file with the following content:

```text
pandas
numpy
google-generativeai
ratelimit
rapidfuzz
better_profanity
python-dotenv
```

Then install the dependencies:

```bash
pip install -r requirements.txt
```

---

## 🚀 Approach Overview

### ✅ 1. Idea Generation
Used the Gemini API (gemini-2.0-flash) to generate hundreds of concise project ideas, each with an estimated manual development time (e.g., 3 hrs). This served as a foundation for simulating development productivity.

### ✅ 2. Data Enrichment & Simulation
- **Date Assignment**: Projects were randomly distributed from October 2024 to April 2025.
- **User Simulation**:
  - Monthly user cohorts (e.g., 200 → 5000 new users per month)
  - 40% of users revisited the platform 5–30 days after signup
  - Additional visits were simulated using exponential inter-arrival (mean = 15 days)
- **Run Capping**: Max 5 projects per user in any 7-day window with enforced 7–30 day cooldown if exceeded.

### ✅ 3. Metric Computation
- **Success Rate (%):**
  - Starts at 100%, reduced by 5% per interruption (0–3)

- **Avg. Cost Savings:**
  ```
  Cost Savings = (Manual Hours * $50) - (Platform Hours * $1)
  ```

- **Productivity Score:**
  ```
  Productivity Score = 0.7 * Success Rate%
                   + 0.3 * (1 - (Platform Time / Manual Time)) * 100
  ```

- **Repeat Usage Rate (%):**
  ```
  Repeat Usage Rate = (# Users with return in 30 days / Total Users) * 100
  ```

---
## main files

- `ideagenerator.py`: Generates project ideas using Gemini API.
- `dataset_creator.ipynb`: processes gemini data and creates other features and metrics
- `project_metrics_after_may_adjusted.csv`: final dataset with all metrics

## 📊 Key Outcomes

- **Average Productivity Score:** ~86%
- **30-Day Repeat Usage Rate:** 38.5%
- **Average Cost Savings per Deployment:** ~$290
- **Total Deployments:** 13,390
- **Unique Simulated Users:** 6,994

## 📈 Visualization & Insights

Designed a Tablaeu dashboard showcasing:
- **Effectiveness:** Productivity vs. task complexity.
- **Time Saved** Task Complexity vs avg time saved
- **ROI:** Monthly and cumulative cost savings.
- **Adoption:** User growth over time.
- **Efficiency:** Time savings distribution by task size.
- **Productivity with time:** Productivity over time
