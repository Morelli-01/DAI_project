import subprocess
from tqdm import tqdm
from multiprocessing import cpu_count

np_stats = []

for i in tqdm(range(500, 50500, 500)):
    elapsed_time = 0
    token_exchanges = 0
    result = subprocess.run(["python3", "./main.py",
                             "--n_proc", str(cpu_count()),
                             "--type", "np",
                             "--columns", str(i)], capture_output=True, text=True)
    r = result.stdout.split('\n')[5].split('|')[2]
    r = (float(r))

    np_stats.append(r)
