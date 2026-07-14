import os, time, base64, requests
from datetime import datetime, timezone, timedelta

GITHUB_TOKEN   = os.environ["GITHUB_TOKEN"]
JBLANKED_TOKEN = os.environ["JBLANKED_TOKEN"]
GITHUB_USER    = "fmb787"
GITHUB_REPO    = "fmb-news-seeds"

DB = {
    "non-farm":      ("positive", "actual_high=USD_up/actual_low=USD_down"),
    "nonfarm":       ("positive", "actual_high=USD_up/actual_low=USD_down"),
    "cpi":           ("positive", "actual_high=USD_up/actual_low=USD_down"),
    "ppi":           ("positive", "actual_high=USD_up/actual_low=USD_down"),
    "gdp":           ("positive", "actual_high=cur_up/actual_low=cur_down"),
    "retail":        ("positive", "actual_high=cur_up/actual_low=cur_down"),
    "ism":           ("positive", "actual_high=USD_up/actual_low=USD_down"),
    "consumer":      ("positive", "actual_high=USD_up/actual_low=USD_down"),
    "adp":           ("positive", "actual_high=USD_up/actual_low=USD_down"),
    "jolts":         ("positive", "actual_high=USD_up/actual_low=USD_down"),
    "unemployment":  ("negative", "actual_high=USD_down/actual_low=USD_up"),
    "jobless":       ("negative", "actual_high=USD_down/actual_low=USD_up"),
    "claimant":      ("negative", "actual_high=cur_down/actual_low=cur_up"),
    "interest rate": ("positive", "actual_high=cur_up/actual_low=cur_down"),
    "rate decision": ("positive", "actual_high=cur_up/actual_low=cur_down"),
    "trade balance": ("positive", "actual_high=cur_up/actual_low=cur_down"),
    "pmi":           ("positive", "actual_high=cur_up/actual_low=cur_down"),
    "ifo":           ("positive", "actual_high=EUR_up/actual_low=EUR_down"),
    "durable":       ("positive", "actual_high=USD_up/actual_low=USD_down"),
    "housing":       ("positive", "actual_high=USD_up/actual_low=USD_down"),
    "building":      ("positive", "actual_high=USD_up/actual_low=USD_down"),
    "existing home": ("positive", "actual_high=USD_up/actual_low=USD_down"),
    "pce":           ("positive", "actual_high=USD_up/actual_low=USD_down"),
}

def get_dir(name):
    low = name.lower()
    for k, v in DB.items():
        if k in low:
            return v
    return ("unknown", "watch_price_action")

def fetch():
    url = "https://www.jblanked.com/news/api/public/calendar/today/"
    hdrs = {
        "Authorization": "Api-Key " + JBLANKED_TOKEN,
        "Content-Type": "application/json"
    }
    try:
        r = requests.get(url, headers=hdrs, timeout=15)
        print("JBlanked status: " + str(r.status_code))
        if r.status_code == 200:
            data = r.json()
            print("type: " + str(type(data)))
            if isinstance(data, list):
                print(str(len(data)) + " events")
                return data
            elif isinstance(data, dict):
                for key in ("results", "data", "events", "calendar"):
                    if key in data:
                        print(str(len(data[key])) + " events in '" + key + "'")
                        return data[key]
                print("keys: " + str(list(data.keys())))
        else:
            print("Response: " + r.text[:300])
    except Exception as e:
        print("JBlanked error: " + str(e))
    return []

def to_pine(events):
    lines = []
    seen = set()
    for ev in events:
        try:
            # JBlanked fields
            name   = str(ev.get("name",     ev.get("event",    ""))).strip().replace("|", "")
            cur    = str(ev.get("currency", ev.get("cur",      ""))).strip().upper()
            ds     = str(ev.get("date",     ev.get("time",     ev.get("datetime", "")))).strip()
            actual = str(ev.get("actual",   "")).strip().replace("|", "")
            fore   = str(ev.get("forecast", ev.get("estimate", ""))).strip().replace("|", "")
            prev   = str(ev.get("previous", ev.get("prev",     ""))).strip().replace("|", "")
            impact = str(ev.get("impact",   ev.get("strength", "low"))).strip().lower()

            if not name or not cur or not ds:
                continue

            # تحويل الوقت
            try:
                ds_clean = ds.replace("Z", "").replace("T", " ")
                if "." in ds_clean:
                    ds_clean = ds_clean[:ds_clean.index(".")]
                dt = datetime.strptime(ds_clean, "%Y-%m-%d %H:%M:%S")
                ts = int(dt.replace(tzinfo=timezone.utc).timestamp())
            except:
                try:
                    dt = datetime.strptime(ds[:10], "%Y-%m-%d")
                    ts = int(dt.replace(tzinfo=timezone.utc).timestamp())
                except:
                    continue

            key = name + "_" + str(ts) + "_" + cur
            if key in seen:
                continue
            seen.add(key)

            d, h = get_dir(name)
            imp = impact if impact in ("high", "medium", "low") else "low"

            lines.append(name + "|" + str(ts) + "|" + cur + "|" + imp + "|" + d + "|" + h + "|" + actual + "|" + fore + "|" + prev)
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
    if evs:
        pine_data = to_pine(evs)
        print("lines: " + str(len(pine_data.splitlines())))
        push(pine_data, "calendar.txt")
        push(str(int(time.time())), "last_update.txt")
    else:
        print("no data")
    print("done")

if __name__ == "__main__":
    main()
