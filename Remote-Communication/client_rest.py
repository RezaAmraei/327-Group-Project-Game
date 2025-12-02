import requests, sys, time, json

BASE = "http://127.0.0.1:8080"
pid = sys.argv[1] if len(sys.argv) > 1 else "P1"

# enqueue
r = requests.post(f"{BASE}/enqueue",
                  json={"playerId": pid},
                  headers={"content-type":"application/json"})
data = r.json()
print("ACCEPTED:", json.dumps(data, indent=2))
tid = data["ticket"]["id"]

# print ticket until status is "matched"
while True:
    t = requests.get(f"{BASE}/ticket/{tid}").json()
    print("TICKET:", t)
    if t.get("status") == "matched":
        print("🎉 MATCHED!", t)
        break
    time.sleep(1)