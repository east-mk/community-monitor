#!/usr/bin/env python3
"""커뮤니티 키워드 감시 봇 -> 구글 시트 기록 (제목 + 본문 검사)

동작
  1. 각 게시판 목록 페이지에서 글 링크/제목을 가져온다.
  2. 제목에 키워드가 있으면 바로 기록한다.
  3. 제목에 없으면 그 글의 본문 페이지를 열어 본문에서 키워드를 찾는다.
  4. 한 번 확인한 글은 seen.json에 기억해서 다시 열지 않는다.
  5. 일치한 글만 구글 시트에 추가한다.
  + 구글 뉴스 검색 결과에서 제목에 키워드가 있는 글을 별도 탭에 기록한다 (search_sources.py).

사용법
  python monitor.py --test            # 시트/seen.json을 건드리지 않고 사이트별 상태만 점검
  python monitor.py                   # 1회 실행 (GitHub Actions용)
  python monitor.py --loop 300        # 300초마다 반복 실행 (내 PC/서버용)

환경변수
  SHEET_ID                 구글 시트 주소의 /d/ 와 /edit 사이 문자열
  GOOGLE_CREDENTIALS       서비스 계정 JSON 내용 전체 (GitHub Secret용)
  GOOGLE_CREDENTIALS_FILE  또는 서비스 계정 JSON 파일 경로 (로컬용)
  WORKSHEET_NAME           (선택) 커뮤니티 탭 이름, 기본 "커뮤니티 모니터링"
  SEARCH_WORKSHEET_NAME    (선택) 검색 탭 이름, 기본 "구글 모니터링"
  SEARCH_ENABLED           (선택) "0"이면 검색 수집을 끔
  NAVER_CLIENT_ID / NAVER_CLIENT_SECRET  (선택) 네이버 검색 API 키
  KAKAO_REST_KEY           (선택) 카카오(다음) 검색 API 키
  SEEN_FILE                (선택) 확인한 글 기록 파일, 기본 "seen.json"
  TIME_BUDGET              (선택) 본문 확인에 쓸 최대 시간(초), 기본 420
  MAX_BODY_PER_BOARD       (선택) 게시판당 1회 실행에서 열어볼 본문 최대 개수, 기본 40
"""
import argparse
import json
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urldefrag, urljoin

import requests
from bs4 import BeautifulSoup

from sites import SITES

KST = timezone(timedelta(hours=9))
HEADER = ["발견시각", "커뮤니티", "게시판", "제목", "키워드", "일치위치", "링크"]
LINK_COL = 7  # G열
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5",
}

SEEN_FILE = os.environ.get("SEEN_FILE", "seen.json")
SEEN_TTL = 5 * 24 * 3600          # 확인 기록은 5일 보관
TIME_BUDGET = int(os.environ.get("TIME_BUDGET", "420"))
MAX_BODY_PER_BOARD = int(os.environ.get("MAX_BODY_PER_BOARD", "40"))
TEST_BODY_PER_SITE = 3            # --test 에서는 게시판당 3개만 열어봄
MAX_FETCH_FAILS = 3               # 본문 열기가 3번 연속 실패하면 포기


def load_keywords(path="keywords.txt"):
    kws = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                kws.append(line)
    return kws


def norm(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def find_keywords(text, keywords):
    n = norm(text)
    return [k for k in keywords if norm(k) in n]


def fetch(session, url, referer=None):
    headers = {"Referer": referer} if referer else None
    r = session.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    # charset 표기가 없으면 requests가 ISO-8859-1로 잘못 추정하므로 보정 (euc-kr 사이트 대응)
    if "charset" not in r.headers.get("Content-Type", "").lower():
        r.encoding = r.apparent_encoding
    return r.text


def extract_posts(html, base_url, pattern):
    """목록 페이지에서 게시글 링크와 제목을 뽑는다. {링크: 제목}"""
    soup = BeautifulSoup(html, "html.parser")
    rx = re.compile(pattern)
    posts = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("javascript:", "#", "mailto:")):
            continue
        link, _ = urldefrag(urljoin(base_url, href))
        if not rx.search(link):
            continue
        title = a.get_text(" ", strip=True)
        if len(title) < 2:
            continue
        # 같은 링크가 댓글수 링크 등으로 여러 번 나오면 가장 긴 제목을 채택
        if len(title) > len(posts.get(link, "")):
            posts[link] = title
    return posts


def extract_body(html, selector):
    """글 본문 텍스트를 뽑는다. (텍스트, 선택자로 정확히 뽑았는지)

    selector 로 본문 영역을 찾으면 그 안의 글만 쓴다 (사이드바의 인기글 제목 등은 제외).
    못 찾으면 페이지 전체에서 머리글/바닥글/사이드바 등을 걷어낸 텍스트를 쓰며,
    이 경우는 오탐 가능성이 있어 '불확실'로 표시한다.
    """
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    if selector:
        try:
            nodes = soup.select(selector)
        except Exception:
            nodes = []
        text = " ".join(n.get_text(" ", strip=True) for n in nodes).strip()
        if text:
            return text, True
    for t in soup(["nav", "header", "footer", "aside", "form"]):
        t.decompose()
    node = soup.find("article") or soup.find("main") or soup.body or soup
    return node.get_text(" ", strip=True), False


def process_site(site, keywords, seen, fails, deadline, test):
    """사이트 하나를 처리한다. 사이트끼리는 병렬, 한 사이트 안에서는 순차 처리."""
    out = {"log": [], "hits": [], "seen": {}, "fails": {}}
    now = time.time()
    session = requests.Session()
    session.headers.update(HEADERS)
    selector = site.get("body")

    for board_name, url in site["boards"]:
        label = f"{site['name']} / {board_name}"
        # 한도는 게시판마다 따로 (사이트 전체에 걸면 첫 게시판이 다 써서 뒤 게시판은 검사를 못 함)
        budget = TEST_BODY_PER_SITE if test else MAX_BODY_PER_BOARD
        try:
            html = fetch(session, url)
        except Exception as e:  # 한 곳이 실패해도 나머지는 계속
            out["log"].append(f"[실패] {label}: {type(e).__name__}: {str(e)[:100]}")
            continue

        posts = extract_posts(html, url, site["pattern"])
        title_hits = body_hits = checked = fallback = fetch_fail = deferred = old = 0
        sample_msg = None

        for link, title in posts.items():
            if link in seen or link in out["seen"]:
                old += 1
                continue

            kws = find_keywords(title, keywords)
            if kws:
                out["hits"].append((site["name"], board_name, title, ", ".join(kws), "제목", link))
                out["seen"][link] = now
                title_hits += 1
                continue

            if budget <= 0 or time.time() > deadline:
                deferred += 1  # 이번엔 못 열어봄 -> seen에 기록하지 않아 다음 실행에서 다시 시도
                continue

            budget -= 1
            time.sleep(random.uniform(0.4, 1.0))
            try:
                body_html = fetch(session, link, referer=url)
            except Exception as e:
                fetch_fail += 1
                n = fails.get(link, 0) + 1
                if n >= MAX_FETCH_FAILS:
                    out["seen"][link] = now  # 계속 실패하는 글은 포기
                else:
                    out["fails"][link] = n
                if test and sample_msg is None:
                    sample_msg = f"        본문 열기 실패 예) {type(e).__name__}: {str(e)[:80]}"
                continue

            text, precise = extract_body(body_html, selector)
            checked += 1
            if not precise:
                fallback += 1
            bk = find_keywords(text, keywords)
            if bk:
                where = "본문" if precise else "본문(불확실)"
                out["hits"].append((site["name"], board_name, title, ", ".join(bk), where, link))
                body_hits += 1
            out["seen"][link] = now
            if test and sample_msg is None:
                mode = "선택자 OK" if precise else "선택자 미적용(일반 추출)"
                sample_msg = f"        본문 {len(text)}자, {mode}: {text[:40]!r}"

        status = "OK" if posts else "글 0개(패턴/URL 확인 필요 또는 차단)"
        line = (
            f"[{status}] {label}: 글 {len(posts)}개 (기확인 {old}), "
            f"제목 일치 {title_hits}, 본문 확인 {checked}→일치 {body_hits}"
        )
        if fallback:
            line += f", 선택자 미적용 {fallback}"
        if fetch_fail:
            line += f", 본문 열기 실패 {fetch_fail}"
        if deferred:
            line += f", 다음 실행으로 미룸 {deferred}"
        out["log"].append(line)
        if test:
            for t in list(posts.values())[:2]:
                out["log"].append(f"        예) {t[:50]}")
            if sample_msg:
                out["log"].append(sample_msg)
        time.sleep(random.uniform(0.5, 1.2))
    return out


def load_seen():
    try:
        with open(SEEN_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("seen", {}), data.get("fails", {})
    except (FileNotFoundError, ValueError):
        return {}, {}


def save_seen(seen, fails):
    cutoff = time.time() - SEEN_TTL
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    fails = {k: v for k, v in fails.items() if k not in seen}
    tmp = SEEN_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"seen": seen, "fails": fails}, f, ensure_ascii=False)
    os.replace(tmp, SEEN_FILE)


def scan(keywords, seen, fails, test=False):
    """모든 사이트를 훑는다. (hits, 새로 확인한 글, 실패 횟수) 반환"""
    deadline = time.time() + TIME_BUDGET
    active = [s for s in SITES if s.get("enabled", True)]
    off = [s["name"] for s in SITES if not s.get("enabled", True)]
    print(f"감시 중 {len(active)}곳: {', '.join(s['name'] for s in active)}")
    if off:
        print(f"꺼둔 사이트 {len(off)}곳: {', '.join(off)}")

    def work(site):
        try:
            return process_site(site, keywords, seen, fails, deadline, test)
        except Exception as e:  # 사이트 하나의 예외가 전체를 멈추지 않게
            return {
                "log": [f"[실패] {site['name']}: {type(e).__name__}: {str(e)[:100]}"],
                "hits": [], "seen": {}, "fails": {},
            }

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(work, active))

    hits, new_seen, new_fails = [], {}, {}
    for r in results:  # SITES 순서대로 출력
        for line in r["log"]:
            print(line)
        hits += r["hits"]
        new_seen.update(r["seen"])
        new_fails.update(r["fails"])
    return hits, new_seen, new_fails


_SPREADSHEET = None


def _spreadsheet():
    global _SPREADSHEET
    if _SPREADSHEET is None:
        import gspread

        if os.environ.get("GOOGLE_CREDENTIALS"):
            gc = gspread.service_account_from_dict(json.loads(os.environ["GOOGLE_CREDENTIALS"]))
        elif os.environ.get("GOOGLE_CREDENTIALS_FILE"):
            gc = gspread.service_account(filename=os.environ["GOOGLE_CREDENTIALS_FILE"])
        else:
            sys.exit("GOOGLE_CREDENTIALS 또는 GOOGLE_CREDENTIALS_FILE 환경변수가 필요합니다.")
        _SPREADSHEET = gc.open_by_key(os.environ["SHEET_ID"])
    return _SPREADSHEET


def open_worksheet(name=None, header=None):
    """탭을 열고(없으면 만들고) 1행 헤더·고정·필터를 맞춘다."""
    import gspread

    name = name or os.environ.get("WORKSHEET_NAME", "커뮤니티 모니터링")
    header = header or HEADER
    sh = _spreadsheet()
    try:
        ws = sh.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=2000, cols=len(header))
    if ws.col_count < len(header):
        ws.resize(cols=len(header))
    if ws.row_values(1) != header:
        ws.update(values=[header], range_name=f"A1:{chr(64 + len(header))}1")
        ws.freeze(rows=1)
        ws.set_basic_filter()  # 1행에 필터 버튼 생성 -> 열마다 골라 보기
    return ws


def write_new(ws, found):
    existing = set(ws.col_values(LINK_COL)[1:])
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    rows, done = [], set()
    for community, board, title, kws, where, link in found:
        if link in existing or link in done:
            continue
        done.add(link)
        safe_title = title.replace('"', '""')
        safe_link = link.replace('"', "%22")
        rows.append(
            [now, community, board, f'=HYPERLINK("{safe_link}","{safe_title}")', kws, where, link]
        )
    if rows:
        # 최신 글이 맨 위에 오도록 2행에 삽입
        ws.insert_rows(rows, row=2, value_input_option="USER_ENTERED")
    print(f"시트에 새 글 {len(rows)}개 추가")


SEARCH_HEADER = ["발견시각", "작성시각", "사이트", "분류", "제목", "키워드", "링크"]
SEARCH_LINK_COL = 7  # G열


def write_search(ws, found):
    existing = set(ws.col_values(SEARCH_LINK_COL)[1:])
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    rows, done = [], set()
    for site, kind, title, kws, link, when in found:
        if link in existing or link in done:
            continue
        done.add(link)
        safe_title = title.replace('"', '""')
        safe_link = link.replace('"', "%22")
        rows.append(
            [now, when, site, kind, f'=HYPERLINK("{safe_link}","{safe_title}")', kws, link]
        )
    # 작성시각이 최신인 글이 위로 오게 정렬 (작성시각 없는 건 뒤로)
    rows.sort(key=lambda r: r[1] or "", reverse=True)
    if rows:
        ws.insert_rows(rows, row=2, value_input_option="USER_ENTERED")
    print(f"[{ws.title}] 새 글 {len(rows)}개 추가")


def run_search(keywords, test):
    """검색(현재 구글 뉴스) -> '구글 모니터링' 탭. 실패해도 커뮤니티 수집은 계속."""
    if os.environ.get("SEARCH_ENABLED", "1") == "0":
        return
    print("=== 구글 뉴스 ===")
    try:
        from search_sources import search_all

        found = search_all(keywords, test=test)
        if test:
            print(f"[테스트] 검색 일치 {len(found)}개 (시트에는 쓰지 않음)\n")
            return
        name = os.environ.get("SEARCH_WORKSHEET_NAME", "구글 모니터링")
        if found:
            write_search(open_worksheet(name, SEARCH_HEADER), found)
        else:
            print("검색에서 새로 일치한 글 없음")
    except Exception as e:
        print(f"[실패] 검색 수집 전체: {type(e).__name__}: {str(e)[:150]}")
    print()


def run_once(keywords, test):
    run_search(keywords, test)

    print("=== 커뮤니티 ===")
    seen, fails = ({}, {}) if test else load_seen()
    hits, new_seen, new_fails = scan(keywords, seen, fails, test=test)

    if test:
        print(f"\n[테스트 종료] 일치 총 {len(hits)}개 (시트와 {SEEN_FILE}에는 쓰지 않음)")
        return

    if hits:
        write_new(open_worksheet(), hits)  # 실패하면 예외 -> 확인 기록을 저장하지 않아 다음에 다시 시도
    else:
        print("새로 일치한 글 없음")

    seen.update(new_seen)
    for link in new_seen:
        fails.pop(link, None)
    fails.update(new_fails)
    save_seen(seen, fails)
    print(f"확인 기록 {len(seen)}개 저장 ({SEEN_FILE})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="시트에 쓰지 않고 사이트별 상태만 점검")
    ap.add_argument("--loop", type=int, default=0, help="N초마다 반복 실행")
    ap.add_argument("--keywords", default="keywords.txt")
    args = ap.parse_args()

    keywords = load_keywords(args.keywords)
    if not keywords:
        sys.exit("keywords.txt에 키워드를 한 줄에 하나씩 적어주세요.")
    print(f"키워드 {len(keywords)}개: {', '.join(keywords)}\n")

    while True:
        run_once(keywords, args.test)
        if not args.loop or args.test:
            break
        print(f"\n{args.loop}초 대기...\n")
        time.sleep(args.loop)


if __name__ == "__main__":
    main()
