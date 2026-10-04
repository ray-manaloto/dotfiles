import time, datetime
with open("/Users/rmanaloto/.claude/jobs/4daaf7e1/tmp/probes/g3-clear/beat.log", "a") as f:
    f.write(datetime.datetime.now().isoformat() + "\n")
time.sleep(20)
