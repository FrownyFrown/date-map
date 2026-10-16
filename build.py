#!/usr/bin/env python3
"""인상·수영 맛집 지도 빌드 — 노션 DB -> 암호화된 data.enc.

공개 repo(GitHub Pages)라 평문 데이터·사진은 커밋하지 않는다. 노션 값·좌표(geo.json)·
사진(photos/<page_id>_N.jpg)을 한 JSON 으로 묶어 AES-GCM 으로 암호화하고 index.html 이
브라우저에서 비밀번호로 푼다. geo.json·photos/·_local/ 은 .gitignore.

  DATEMAP_PW=... NOTION_TOKEN=... python3 build.py
"""
import base64, glob, json, os, urllib.request
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

DS = "76fa807c-78b6-4b8d-baf6-038608d41776"
ITER = 600_000
HERE = os.path.dirname(os.path.abspath(__file__))


def notion_rows():
    rows, cur = [], None
    while True:
        body = {"page_size": 100, **({"start_cursor": cur} if cur else {})}
        req = urllib.request.Request(
            f"https://api.notion.com/v1/data_sources/{DS}/query", json.dumps(body).encode(),
            {"Authorization": "Bearer " + os.environ["NOTION_TOKEN"], "Notion-Version": "2025-09-03",
             "Content-Type": "application/json"})
        d = json.load(urllib.request.urlopen(req))
        rows += d["results"]
        if not d.get("has_more"): return rows
        cur = d["next_cursor"]


def val(v):
    t = v["type"]; x = v[t]
    if t in ("title", "rich_text"): return "".join(a["plain_text"] for a in x)
    if t == "select": return (x or {}).get("name")
    if t == "date": return (x or {}).get("start")
    if t == "url": return x
    return x


def main():
    geo = json.load(open(os.path.join(HERE, "geo.json")))
    places = []
    for p in notion_rows():
        pr = {k: val(v) for k, v in p["properties"].items()}
        g = geo.get(p["id"], {})
        # <id>_r.jpg = 식당 대표 사진(웹), <id>_<n>.jpg = 우리가 찍은 사진. 대표 사진을 앞에 둔다
        photos = [{"src": "data:image/jpeg;base64," + base64.b64encode(open(f, "rb").read()).decode(),
                   "mine": not f.endswith("_r.jpg")}
                  for f in sorted(glob.glob(os.path.join(HERE, "photos", p["id"] + "_*.jpg")),
                                  key=lambda f: (not f.endswith("_r.jpg"), f))]
        places.append({
            "id": p["id"], "name": pr.get("이름"), "status": pr.get("상태"), "kind": pr.get("음식 종류"),
            "minutes": pr.get("이동 시간(분)"), "area": pr.get("지역"), "menu": pr.get("대표 메뉴"),
            "note": pr.get("메모"), "visits": pr.get("방문 횟수"), "date": pr.get("방문일"),
            "link": pr.get("지도 링크"), "lat": g.get("lat"), "lon": g.get("lon"), "photos": photos,
        })
    plain = json.dumps({"places": places}, ensure_ascii=False).encode()
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(hashes.SHA256(), 32, salt, ITER).derive(os.environ["DATEMAP_PW"].encode())
    ct = AESGCM(key).encrypt(iv, plain, None)
    out = {"v": 1, "iter": ITER, "salt": base64.b64encode(salt).decode(),
           "iv": base64.b64encode(iv).decode(), "ct": base64.b64encode(ct).decode()}
    json.dump(out, open(os.path.join(HERE, "data.enc"), "w"))
    print(f"places {len(places)} / pinned {sum(1 for x in places if x['lat'])} / "
          f"photos {sum(len(x['photos']) for x in places)} / {len(plain)//1024}KB")


if __name__ == "__main__":
    main()
