import subprocess
from tqdm import tqdm
from multiprocessing import cpu_count

np_stats = {}
rm_stats = {
    'n_proc_var_time': [],
    'n_proc_var_msg': []
}

for i in tqdm(range(500, 50500, 500)):
    result = subprocess.run(["python3", "./main.py",
                             "--n_proc", str(cpu_count()),
                             "--type", "token-ring",
                             "--columns", str(i)], capture_output=True, text=True)

    r = result.stdout.split('\n')
    elapsed_time = float(r[5].split('|')[2])
    token_exchanges = int(r[7].split('|')[2])
    rm_stats['n_proc_var_time'].append(elapsed_time)
    rm_stats['n_proc_var_msg'].append(token_exchanges)

