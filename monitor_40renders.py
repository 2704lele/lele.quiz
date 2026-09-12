import subprocess, time, json

runs = [
    # Pinyin
    '33641057531', '33641061104', '33641066085', '33641072180', '33641077689', '33641083314', '33641088669', '33641093600', '33641099184', '33641104348',
    # VocabCN
    '33641110540', '33641116289', '33641121643', '33641126409', '33641131911', '33641137263', '33641142743', '33641148385', '33641153906', '33641159231', '33641165233', '33641171148', '33641176159', '33641181215',
    # VocabVN
    '33641186192', '33641190697', '33641195910', '33641201071', '33641206544', '33641211182', '33641216470', '33641221998', '33641226522', '33641231456', '33641236566', '33641241190',
    # Multilevels
    '33641246088', '33641250766', '33641256511', '33641262575'
]
runs = list(dict.fromkeys(runs))

print(f"Monitoring {len(runs)} render runs...")

for attempt in range(40): # max 10 minutes
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
        print("All 40 render runs finished!")
        break
    time.sleep(15)
