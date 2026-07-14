import os, time, base64, requests
from datetime import datetime, timezone

GITHUB_TOKEN    = os.environ["GITHUB_TOKEN"]
GITHUB_USER     = "fmb787"
GITHUB_REPO     = "fmb-news-seeds"
TE_URL = "https://api.tradingeconomics.com/calendar?c=guest:guest&importance=2"

IMP = {1:"low", 2:"medium", 3:"high"}

DB = {
    "non-farm":      ("positive","actual_high=USD_up/actual_low=USD_down"),
    "nonfarm":       ("positive","actual_high=USD_up/actual_low=USD_down"),
    "cpi":           ("positive","actual_high=USD_up/actual_low=USD_down"),
    "ppi":           ("positive","actual_high=USD_up/actual_low=USD_down"),
    "gdp":           ("positive","actual_high=cur_up/actual_low=cur_down"),
    "retail":        ("positive","actual_high=cur_up/actual_low=cur_down"),
    "ism":           ("positive","actual_high=USD_up/actual_low=USD_down"),
    "consumer":      ("positive","actual_high=USD_up/actual_low=USD_down"),
    "adp":           ("positive","actual_high=USD_up/actual_low=USD_down"),
    "jolts":         ("positive","actual_high=USD_up/actual_low=USD_down"),
    "unemployment":  ("negative","actual_high=USD_down/actual_low=USD_up"),
    "jobless":       ("negative","actual_high=USD_down/actual_low=USD_up"),
    "claimant":      ("negative","actual_high=cur_down/actual_low=cur_up"),
    "interest rate": ("positive","actual_high=cur_up/actual_low=cur_down"),
    "rate":          ("positive","actual_high=cur_up/actual_low=cur_down"),
    "trade":         ("positive","actual_high=cur_up/actual_low=cur_down"),
    "pmi":           ("positive","actual_high=cur_up/actual_low=cur_down"),
    "ifo":           ("positive","actual_high=EUR_up/actual_low=EUR_down"),
    "durable":       ("positive","actual_high=USD_up/actual_low=USD_down"),
    "housing":       ("positive","actual_high=USD_up/actual_low=USD_down"),
    "building":      ("positive","actual_high=USD_up/actual_low=USD_down"),
}

def get_dir(name):
    low = name.lower()
    for k, v in DB.items():
        if k in low:
            return v
    return ("unknown", "watch_price_action")

def fetch():
    try:
        r = requests.get(TE_URL, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print("TE error: " + str(e))
    return []

def to_pine(events):
    lines = []
    seen = set()
    for ev in events:
        try:
            name = str(ev.get("Event", "")).strip().replace("|", "")
            cur  = str(ev.get("Currency", "")).strip()
            ds   = str(ev.get("Date", "")).strip().replace("Z", "").replace("T", " ")
            if "." in ds:
                ds = ds[:ds.index(".")]
            imp    = int(ev.get("Importance", 1))
            actual = str(ev.get("Actual", "")).strip().replace("|", "")
            fore   = str(ev.get("Forecast", "")).strip().replace("|", "")
            prev   = str(ev.get("Previous", "")).strip().replace("|", "")
            if not name or not cur or not ds:
                continue
            dt  = datetime.strptime(ds, "%Y-%m-%d %H:%M:%S")
            ts  = int(dt.replace(tzinfo=timezone.utc).timestamp())
            key = name + "_" + str(ts) + "_" + cur
            if key in seen:
                continue
            seen.add(key)
            d, h = get_dir(name)
            lines.append(name + "|" + str(ts) + "|" + cur + "|" + IMP.get(imp, "low") + "|" + d + "|" + h + "|" + actual + "|" + fore + "|" + prev)
        except Exception as e:
            print("row error: " + str(e))
            continue
    return "\n".join(lines)

def push(content, filename):
    url  = "https://api.github.com/repos/" + GITHUB_USER + "/" + GITHUB_REPO + "/contents/" + filename
    hdrs = {
        "Authorization": "token " + GITHUB_TOKEN,
        "Accept": "application/vnd.github.v3+json"
    }
    sha = None
    r = requests.get(url, headers=hdrs, timeout=10)
    if r.status_code == 200:
        sha = r.json().get("sha")
    enc = base64.b64encode(content.encode()).decode()
    pay = {
        "message": "update " + datetime.utcnow().strftime("%H:%M:%S"),
        "content": enc
    }
    if sha:
        pay["sha"] = sha
    r = requests.put(url, headers=hdrs, json=pay, timeout=15)
    status = "OK" if r.status_code in (200, 201) else "FAIL"
    print(status + ": " + filename + " (" + str(r.status_code) + ")")

def main():
    print("start " + datetime.utcnow().strftime("%H:%M:%S"))
    evs = fetch()
    print(str(len(evs)) + " events")
    if evs:
        push(to_pine(evs), "calendar.txt")
        push(str(int(time.time())), "last_update.txt")
    print("done")

if __name__ == "__main__":
    main()
