# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx",
#   "pandas",
#   "matplotlib",
#   "requests",
#   "python-dotenv",
# ]
# ///

import pandas as pd
import sys
import requests
import json
import os
import traceback
import matplotlib.pyplot as plt
from dotenv import load_dotenv

# Load environment variables (AIPROXY_TOKEN)
load_dotenv()
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")
#Argument Handling
if len(sys.argv) < 2:
    print("Usage: uv run autolysis.py dataset.csv")
    sys.exit(1)

dataset_path = sys.argv[1]

#Dataset Loading

try:
    df = pd.read_csv(dataset_path, encoding='latin-1')
    print(f"Dataset loaded successfully with shape: {df.shape}")
except FileNotFoundError:
    print(f"Error: The file '{dataset_path}' was not found.")
    sys.exit(1)
except Exception as e:
    print(f"Error loading the dataset: {e}")
    sys.exit(1)

#Metadata Extraction and AI Model Interaction

data = df.head(10)
content = """
Analyze the given dataset. The first line is a header and the subsequent lines are data,
columns may have uncleaned data in them, ignore those cells, Infer the data type 
by considering majority. The datatype can be 'integer','boolean','float','string','date'.
"""
function_schema_metadata = [
    {
        "name": "get_column_type",
        "description": "Identify column names and their datatypes from a CSV for use in Python.",
        "parameters": {
            "type": "object",
            "properties": {
                "column_metadata": {
                    "type": "array",
                    "description": "Array of data types for each column",
                    "items": {
                        "type": "object",
                        "properties": {
                            "column_name": {"type": "string"},
                            "column_type": {"type": "string"}
                        },
                        "required": ["column_name", "column_type"]
                    },
                    "minItems": 1
                }
            },
            "required": ["column_metadata"]
        }
    }
]

json_data = {
    "model" : "gpt-4o-mini",
    "messages" : [{"role": "system", "content": content},
                  {"role":"user","content":data.to_json()}],
    "functions" : function_schema_metadata,
    "function_call" : {"name": "get_column_type"}
}

url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
headers = {"Authorization": f"Bearer {AIPROXY_TOKEN}"}

r = requests.post(url, json=json_data, headers=headers)
metadata = json.loads(r.json()['choices'][0]['message']['function_call']['arguments'])['column_metadata']

#Checking Binnability of Columns 

def check_binnability_with_function(column_stats):
    AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")
    if not AIPROXY_TOKEN:
        raise ValueError("AIPROXY_TOKEN environment variable not set.")
    
    url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {AIPROXY_TOKEN}"}
    function_schema = {
        "name": "binnable",
        "description": "Identify if the column is binnable or not; also provide a reason.",
        "parameters": {
            "type": "object",
            "properties": {
                "is_binnable": {"type": "boolean"},
                "reason": {"type": "string"}
            },
            "required": ["is_binnable", "reason"]
        }
    }

    prompt = f"""
        Analyze the column '{column_stats['column_name']}' with the following statistics:
        {column_stats['statistics']}
        Determine if the column is suitable for binning and explain why.
    """

    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "functions": [function_schema],
        "function_call": {"name": "binnable"}
    }

    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        function_call = response.json()['choices'][0]['message']['function_call']["arguments"]
        extracted_data = json.loads(function_call)
        is_binnable = extracted_data.get("is_binnable")
        reason = extracted_data.get("reason")
        return {"is_binnable": is_binnable, "reason": reason}
    else:
        print(f"Error: {response.text}")
        return None


#Executing Generated Code and Handling Errors

def execute_llm_code(code):
    try:
        exec(code, globals())
        print("Code executed successfully.")
        return True
    except Exception as e:
        error_line = traceback.extract_tb(e.__traceback__)[-1].lineno
        error_message = f"Error: {e}\nLine: {error_line}\nCode: {code}"
        print(error_message)
        return error_message


#Iterating Over Columns and Determining Binnability

results = []

for column in df.columns:
    if pd.api.types.is_numeric_dtype(df[column]):
        stats = df[column].describe().to_dict()
        stats["Name"] = column
        column_data = {"statistics": stats, "column_name": column}
        binnability = check_binnability_with_function(column_data)
        results.append({column: binnability})

binnable_columns = [column_name for item in results for column_name, binnability_data in item.items() if binnability_data and binnability_data['is_binnable']]

#Storing and Chart Generation

binnable_columns_data = {}
for column in binnable_columns:
    if pd.api.types.is_numeric_dtype(df[column]):
        stats = df[column].describe().to_dict()
        stats["Name"] = column
        column_data = {"statistics": stats, "column_name": column}
        binnable_columns_data[column] = column_data

for column_name, column_data in binnable_columns_data.items():
    prompt3 = f"""
    You are a code generation assistant for creating data visualizations.
    Given the following statistics about column '{column_name}': {column_data['statistics']}
    Create appropriate charts for the data using continuous binning.
    Export each chart as a PNG file with the column name as the file name.
    """

    function_schema_chart = [
        {
            "name": "generate_chart",
            "description": "Generate Python code to create a chart based on the prompt, export as PNG.",
            "parameters": {
                "type": "object",
                "properties": {
                    "python_code": {"type": "string"},
                    "chart_name": {"type": "string"}
                },
                "required": ["python_code", "chart_name"]
            }
        }
    ]

    json_data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "system", "content": prompt3}],
        "functions": function_schema_chart,
        "function_call": {"name": "generate_chart"}
    }

    response = requests.post(url, json=json_data, headers=headers)
    if response.status_code == 200:
        code = json.loads(response.json()['choices'][0]['message']['function_call']["arguments"])["python_code"]
        result = execute_llm_code(code)
        if result:
            print(f"Chart for {column_name} generated successfully.")
        else:
            print(f"Error generating chart for {column_name}")



#Report Generation 

prompt4 = f"""
You are an assistant writing a detailed report based on data analysis.

The data you received:
{metadata} 

Statistics of the data:
{binnable_columns_data}

The analysis you carried out: 
- Continuous binning was applied to create visualizations for the binnable columns.
- Charts were generated to explore the distribution and patterns in the data.

Include the following charts in the report:
{chart_paths}

Based on the data and visualizations, provide the following:
- The insights you discovered: Identify any interesting patterns, trends, or outliers observed in the data.
- The implications of your findings: Suggest potential actions or decisions that can be taken based on the insights.
"""

#Final Request and Report Writing

json_data = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "system", "content": prompt4}],
    "functions": function_schema_report,
    "function_call": {"name": "generate_report"}
}

response = requests.post(url, json=json_data, headers=headers)
if response.status_code == 200:
    generated_report = json.loads(response.json()['choices'][0]['message']['function_call']['arguments'])['analysis_report']
    print("Generated Report: ", generated_report)
else:
    print(f"Error: {response.text}")

with open("Readme.md", "w") as f:
    f.write(generated_report)
