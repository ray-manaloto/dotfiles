import json, sys, time
e = json.load(sys.stdin)
ti = e.get("tool_input", {})
with open(sys.argv[1], "a") as f:
    f.write(json.dumps({"t": time.time(), "tool": e.get("tool_name"), "to": ti.get("to")}) + "\n")
if e.get("tool_name") == "SendMessage" and ti.get("to") == "s0-alias":
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": {**ti, "to": "s0-recv"}}}))
