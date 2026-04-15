def generate_report(metadata, stats, charts):
    report = f"""
Metadata: {metadata}
Stats: {stats}
Charts: {charts}
"""

    with open("README.md", "w") as f:
        f.write(report)

    print("Report generated.")