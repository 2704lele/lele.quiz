import subprocess, time, json

runs = [
    # ProductQC (Pinyin)
    '33462473418', '33462476389', '33462479527', '33462482258', '33462484794',
    # vocabcn_qc
    '33462487383', '33462490325', '33462493267', '33462495966', '33462498489',
    # vocabvn_qc
    '33462501358', '33462503811', '33462506598', '33462509036', '33462511667',
    # multilevels_qc
    '33462514129', '33462516444', '33462519174', '33462521760', '33462524352', '33462527405', '33462529929', '33462532372', '33462534456'
]
runs = list(dict.fromkeys(runs))

print(f"Monitoring {len(runs)} QC runs...")

for attempt in range(30): # max 7.5 minutes
    in_prog = 0
    completed = 0
    failed = 0

    for r in runs:
        res = subprocess.run(['gh', 'run', 'view', r, '--json', 'status,conclusion'], capture_output=True, text=True)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            st = data.get('status')
            conc = data.get('conclusion')
            if st == 'completed':
                if conc == 'success':
                    completed += 1
                else:
                    failed += 1
            else:
                in_prog += 1
        else:
            in_prog += 1

    print(f"Attempt {attempt+1}: In-Progress={in_prog}, Completed={completed}, Failed={failed}")
    if in_prog == 0:
        print("All QC runs finished!")
        break
    time.sleep(15)
