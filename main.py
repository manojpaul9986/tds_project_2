import sys
from utils import load_dataset
from llm import get_metadata, check_binnability
from analysis import get_numeric_stats
from visualization import generate_charts
from report import generate_report

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py dataset.csv")
        sys.exit(1)

    df = load_dataset(sys.argv[1])

    metadata = get_metadata(df)
    stats = get_numeric_stats(df)

    binnable = check_binnability(stats)

    chart_paths = generate_charts(binnable)

    generate_report(metadata, stats, chart_paths)

if __name__ == "__main__":
    main()