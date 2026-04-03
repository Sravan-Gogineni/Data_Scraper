# UniScraper: High-Precision University Data Extraction Ecosystem

UniScraper is an advanced, AI-driven data extraction platform designed to capture, clean, and categorize comprehensive university information. It leverages Large Language Models (LLMs) with Google Search grounding to ensure 100% data accuracy and provides a seamless web interface for real-time monitoring and processing.

---

## 🏗️ Architecture Overview

The system is organized into specialized modules to handle the three pillars of university data:

### 1. [Institution](file:///Users/sravan/projects/Scraper_UI/University_Data/Institution/)
Extracts high-level university details including:
*   Contact information (Admissions Email, Phone)
*   Global identifiers (UnitID, OPEID)
*   Institutional social and web presence.

### 2. [Departments](file:///Users/sravan/projects/Scraper_UI/University_Data/Departments/)
Identifies the university's organizational structure:
*   Official colleges (e.g., College of Engineering)
*   Department-specific admissions offices.
*   Administrative units for specialized mapping.

### 3. [Programs](file:///Users/sravan/projects/Scraper_UI/University_Data/Programs/)
The core extraction engine for academic offerings, split into **Undergraduate** and **Graduate** tracks. It uses a consolidated "Master Extraction" strategy to minimize token usage and maximize data integrity.

---

## 🚀 The Data Pipeline

The extraction process follows a rigorous 7-step sequence to ensure professional-grade datasets:

| Step | Phase | Description |
| :--- | :--- | :--- |
| **1** | **Discovery** | Crawls the university portal to find all valid program URLs. |
| **2** | **Master Extraction** | Consolidated AI pass for Fees, Test Scores, Reqs, and Descriptions. |
| **3-5** | **Deprecated** | Consolidated into Step 2 for high-speed execution. |
| **6** | **Standardization** | Merges all multi-source data into the enterprise CSV schema. |
| **7** | **Global Merge** | Final deduplication and cross-track consistency check. |
| **Map** | **Dept Association** | AI matching of programs to decentralized college offices. |

---

## 🧠 Advanced Features

### 🔹 AI-Managed Citation Stripping
Uses a robust regex-based logic (`r'\[\d+(?:,\s*\d+)*\]'`) coupled with AI prompt enforcement to remove complex multi-number citations (e.g., `[2, 4, 15]`) from all extracted text fields, ensuring 100% clean and ready-to-use data.

### 🔹 Decentralized Department Mapping
A specialized utility that intelligently maps programs to their specific college-level admissions offices. It prioritizes specificity (e.g., mapping "MS in CS" to the **College of Engineering**) over generic university-wide offices.

### 🔹 Google Search Grounding
Instead of relying on internal LLM knowledge, every extraction is grounded in real-time Google Search results pointing specifically to official university domains (`.edu`).

---

## 🛠️ Operating Instructions

### 1. Setup
Ensure your environment variables are configured in `.env`:
*   `GCP_PROJECT`: Your Google Cloud Project ID.
*   `MODEL`: The Gemini model version (e.g., `gemini-1.5-pro-002`).

### 2. Starting the Ecosystem
Run the backend server:
```bash
python3 web-app/backend/app.py
```
Open `index.html` in your browser to access the control panel.

### 3. Extracting a University
1.  **Institution/Dept**: Run the discovery steps first to get the blueprint.
2.  **Step 1 (Programs)**: Discover the full list of academic offerings.
3.  **Step 8 (All Extraction)**: Trigger the consolidated Master Extraction for all fields.
4.  **Map Departments**: Upload your final program and department files to generate the authoritative association file.

---

## 📂 Project Structure

```text
├── University_Data/
│   ├── Institution/      # Global university data
│   ├── Departments/      # Administrative units
│   └── Programs/         # Academic program datasets
│       ├── graduate_programs/      # Grad extraction modules
│       └── undergraduate_programs/ # UG extraction modules
├── web-app/
│   ├── backend/          # Flask SSE server
│   └── frontend/         # Modern glass-morphism UI
└── README.md             # This document
```

---

> [!TIP]
> Always verify that your CSV headers match the standard schema defined in `merge_and_standardize.py` before running the Department Mapper for custom files.

> [!SUCCESS]
> UniScraper is now optimized and fully documented for professional data operations.
