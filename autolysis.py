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
import sys  # To capture the dataset file path
import requests
import json
import os
import traceback
import matplotlib.pyplot as plt
from dotenv import load_dotenv
load_dotenv()
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")
# Ensure the script receives the dataset file path
if len(sys.argv) < 2:
    print("Usage: uv run autolysis.py dataset.csv")
    sys.exit(1)

# Capture the dataset file path
dataset_path = sys.argv[1]

# Load the dataset using pandas
try:
    df = pd.read_csv(dataset_path, encoding='latin-1')
    print(f"Dataset loaded successfully with shape: {df.shape}")
except FileNotFoundError:
    print(f"Error: The file '{dataset_path}' was not found.")
    sys.exit(1)
except Exception as e:
    print(f"Error loading the dataset: {e}")
    sys.exit(1)




#Metadata Extraction 


data = df.head(10)
content = (
    "Analyze the given datset. The first line is a header and the subsequent lines are data,"
    "collumns may have uncleaned data in them , ignore those cells , Infer the data type "
    "by considering majority."
    "the datatype can be 'integer','boolean','float','string','date'"
)

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
                                "column_name": {
                                    "type": "string",
                                    "description": "Name of the column."
                                },
                                "column_type": {
                                    "type": "string",
                                    "description": "The data type of the column (e.g., integer, string)."
                                }
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


#Find Binnable Columns 


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
                "is_binnable": {
                    "type": "boolean",
                    "description": "Indicates if the column can be binned."
                },
                "reason": {
                    "type": "string",
                    "description": "Reason why the column is or isn't binnable."
                },
            },
            "required": ["is_binnable", "reason"],
        },
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
        #print(response.json())  # Inspect the response
        function_call = response.json()['choices'][0]['message']['function_call']["arguments"]
        extracted_data = json.loads(function_call)
        is_binnable = extracted_data.get("is_binnable")
        reason = extracted_data.get("reason")
        return {"is_binnable": is_binnable, "reason": reason}
        
    else:
        print(f"Error: {response.text}")
        return None


results = []
    
for column in df.columns:
    if pd.api.types.is_numeric_dtype(df[column]):
        stats = df[column].describe().to_dict()
        stats["Name"] = column
        column_data = {"statistics": stats, "column_name": column}
        binnability = check_binnability_with_function(column_data)
        results.append({column: binnability})



    
for column in df.columns:
    if pd.api.types.is_numeric_dtype(df[column]):
        stats = df[column].describe().to_dict()
        stats["Name"] = column
        column_data = {"statistics": stats, "column_name": column}
        binnability = check_binnability_with_function(column_data)
        results.append({column: binnability})


binnable_columns = []
for item in results:
       for column_name, binnability_data in item.items():
           if binnability_data is not None and binnability_data['is_binnable']:
               binnable_columns.append(column_name)

binnable_columns_data = {}  # Initialize an empty dictionary
for column in binnable_columns:
    if pd.api.types.is_numeric_dtype(df[column]):
        stats = df[column].describe().to_dict()
        stats["Name"] = column
        column_data = {"statistics": stats, "column_name": column}
        binnable_columns_data[column] = column_data  # Store column_data with column name as key

#Chart Generation for Binnable Columns with Error Handling 

for column_name, column_data in binnable_columns_data.items():
        prompt3 = f"""
        You are a code generation assistant for creating data visualizations.
        do not make your own data, dataset is stored in the dataframe named df, 
        Given the following statistics about column '{column_name}': {column_data['statistics']}

        Use only the columns from this list: {binnable_columns}.
        Create appropriate charts for the data using continuous binning.
        Export each chart as a PNG file with the column name as the file name.
        use matplotlib. Don't use comments or unrelated libraries.

        Generate only Python code to achieve this.
        """

        function_schema_chart = [
            {
                "name": "generate_chart",
                "description": "Generate Python code without comments to create a chart based on the prompt, export as PNG.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "python_code": {
                            "type": "string",
                            "description": "Generate Python code without comments that creates an appropriate chart.",
                        },
                        "chart_name": {
                            "type": "string",
                            "description": "Chart/file name of the PNG chart.",
                        }
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

        url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {AIPROXY_TOKEN}"}

        response = requests.post(url, json=json_data, headers=headers)
        if response.status_code == 200:
            code = json.loads(response.json()['choices'][0]['message']['function_call']["arguments"])["python_code"]

            # Retry mechanism
            max_retries = 3
            for attempt in range(max_retries):
                result = execute_llm_code(code)  # Assuming execute_llm_code is defined elsewhere
                if result is True:
                    break
                else:
                    print(f"Retry {attempt + 1}: Fixing errors...")
                    prompt += f"\n\nPrevious attempt failed with the following error:\n{result}"
        else:
            print(f"Error: {response.text}")


def execute_llm_code(code):
    try:
        exec(code, globals())  # Execute the code in the global namespace
        print("Code executed successfully.")
        return True  # Indicate success
    except Exception as e:
        error_line = traceback.extract_tb(e.__traceback__)[-1].lineno
        error_message = f"Error: {e}\nLine: {error_line}\nCode: {code}"
        print(error_message)  # Print detailed error information
        return error_message  # Return the error for retry

#Report generation 


chart_paths = []  # Initialize an empty list to store chart paths

for column_name, column_data in binnable_columns_data.items():
    # ... (Your existing code for generating and executing charts)

    # After successfully generating the chart:
    chart_path = f"{column_name}.png"  # Or your desired path
    chart_paths.append(chart_path)


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

function_schema_report = [
    {
        "name": "generate_report",
        "description": "Generate a detailed analysis report with charts embedded.",
        "parameters": {
            "type": "object",
            "properties": {
                "analysis_report": {
                    "type": "string",
                    "description": "Generate a detailed report including analysis and charts."
                },
                "metadata": {
                    "type": "object",
                    "description": "Metadata about the dataset."
                },
                "statistics": {
                    "type": "object",
                    "description": "Statistics of the binnable columns."
                },
                "charts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "chart_name": {"type": "string"},
                            "chart_path": {"type": "string"}
                        },
                        "required": ["chart_name", "chart_path"]
                    }
                }
            },
            "required": ["analysis_report", "metadata", "statistics", "charts"]
        }
    }
]

json_data = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "system", "content": prompt4}],
    "functions": function_schema_report,
    "function_call": {"name": "generate_report"}
        
    }

response = requests.post(url, json=json_data, headers=headers)

# Check if the response status code is 200 (success)
if response.status_code == 200:
    # Get the generated report from the response
    generated_report = json.loads(response.json()['choices'][0]['message']['function_call']['arguments'])['analysis_report']
    print("Generated Report: ", generated_report)
else:
    print(f"Error: {response.text}")

with open("Readme.md", "w") as f:
    f.write(generated_report)
