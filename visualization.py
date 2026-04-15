import matplotlib.pyplot as plt

def generate_charts(data):
    paths = []

    for col, stats in data.items():
        plt.figure()
        plt.hist(stats.values())
        filename = f"{col}.png"
        plt.savefig(filename)
        paths.append(filename)

    return paths