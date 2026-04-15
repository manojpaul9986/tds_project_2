# AutoLysis – LLM-Powered Automated EDA

AutoLysis is an AI-driven system that performs automated exploratory data analysis (EDA) using LLMs.

## 🚀 Features
- Automatic schema inference (column types)
- Data cleaning & preprocessing insights
- Statistical summaries and analysis
- Visualization generation using matplotlib
- LLM-based reasoning for dataset understanding

## 🧠 How it Works
1. Loads dataset (CSV)
2. Extracts metadata from sample rows
3. Uses LLM (via API) to infer column types
4. Generates analysis + visualizations

## 🛠️ Tech Stack
- Python
- Pandas
- Matplotlib
- LLM APIs (function calling)

## ▶️ Usage
```bash
python autolysis.py dataset.csv
