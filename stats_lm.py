import subprocess
from tqdm import tqdm
from multiprocessing import cpu_count

lm_stats = {
    'n_proc_var_time': [],
    'n_proc_var_msg': []

}

for i in tqdm(range(500, 50500, 500)):
    elapsed_time = 0
    msg_exchanges = 0
    result = subprocess.run(["python3", "./main.py",
                             "--n_proc", str(cpu_count()),
                             "--type", "lamport",
                             "--columns", str(i)], capture_output=True, text=True)
    r = result.stdout.split('\n')
    # print(result.stdout)
    elapsed_time += float(r[5].split('|')[2])
    msg_exchanges += int(r[6].split('|')[2].strip())
    lm_stats['n_proc_var_time'].append(elapsed_time)
    lm_stats['n_proc_var_msg'].append(msg_exchanges)
