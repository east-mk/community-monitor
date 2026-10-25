#!/usr/bin/env python3
"""커뮤니티 키워드 감시 봇 -> 구글 시트 기록

사용법
  python monitor.py --test            # 시트 없이 사이트별 접속/파싱 상태만 점검
  python monitor.py                   # 1회 실행 (GitHub Actions용)
  python monitor.py --loop 300        # 300초마다 반복 실행 (내 PC/서버용)

환경변수
  SHEET_ID                 구글 시트 주소의 /d/ 와 /edit 사이 문자열
  GOOGLE_CREDENTIALS       서비스 계정 JSON 내용 전체 (GitHub Secret용)
  GOOGLE_CREDENTIALS_FILE  또는 서비스 계정 JSON 파일 경로 (로컬용)
  WORKSHEET_NAME           (선택) 탭 이름, 기본 "감시결과"
"""
import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urldefrag, urljoin

import requests
from bs4 import BeautifulSoup

from sites import SITES

KST = timezone(timedelta(hours=9))
HEADER = ["발견시각", "커뮤니티", "게시판", "제목", "키워드", "링크"]
LINK_COL = 6  # F열
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5",
}


def load_keywords(path="keywords.txt"):
    kws = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                kws.append(line)
    return kws


def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
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


def match_keywords(title, keywords):
    low = title.lower()
    return [k for k in keywords if k.lower() in low]


def scan(keywords, test=False):
    """모든 사이트를 훑어서 [(커뮤니티, 게시판, 제목, 키워드, 링크)] 반환"""
    found = []
    for site in SITES:
        if not site.get("enabled", True):
            print(f"[건너뜀] {site['name']}: {site.get('note', '비활성')}")
            continue
        for board_name, url in site["boards"]:
            label = f"{site['name']} / {board_name}"
            try:
                html = fetch(url)
                posts = extract_posts(html, url, site["pattern"])
                hits = 0
                for link, title in posts.items():
                    kws = match_keywords(title, keywords)
                    if kws:
                        hits += 1
                        found.append((site["name"], board_name, title, ", ".join(kws), link))
                status = "OK" if posts else "글 0개(패턴/URL 확인 필요 또는 차단)"
                print(f"[{status}] {label}: 글 {len(posts)}개, 키워드 일치 {hits}개")
                if test and posts:
                    for t in list(posts.values())[:3]:
                        print(f"        예) {t[:50]}")
            except Exception as e:  # 한 곳이 실패해도 나머지는 계속
                print(f"[실패] {label}: {type(e).__name__}: {str(e)[:100]}")
            time.sleep(random.uniform(1.0, 2.5))
    return found


def open_worksheet():
    import gspread

    if os.environ.get("GOOGLE_CREDENTIALS"):
        gc = gspread.service_account_from_dict(json.loads(os.environ["GOOGLE_CREDENTIALS"]))
    elif os.environ.get("GOOGLE_CREDENTIALS_FILE"):
        gc = gspread.service_account(filename=os.environ["GOOGLE_CREDENTIALS_FILE"])
    else:
        sys.exit("GOOGLE_CREDENTIALS 또는 GOOGLE_CREDENTIALS_FILE 환경변수가 필요합니다.")
    sh = gc.open_by_key(os.environ["SHEET_ID"])
    name = os.environ.get("WORKSHEET_NAME", "감시결과")
    try:
        ws = sh.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=2000, cols=len(HEADER))
    if ws.row_values(1) != HEADER:
        ws.update(values=[HEADER], range_name="A1:F1")
        ws.freeze(rows=1)
        ws.set_basic_filter()  # 1행에 필터 버튼 생성 -> 커뮤니티/게시판 열에서 골라 보기
    return ws


def write_new(ws, found):
    existing = set(ws.col_values(LINK_COL)[1:])
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    rows, seen = [], set()
    for community, board, title, kws, link in found:
        if link in existing or link in seen:
            continue
        seen.add(link)
        safe = title.replace('"', '""')
        rows.append([now, community, board, f'=HYPERLINK("{link}","{safe}")', kws, link])
    if rows:
        # 최신 글이 맨 위에 오도록 2행에 삽입
        ws.insert_rows(rows, row=2, value_input_option="USER_ENTERED")
    print(f"시트에 새 글 {len(rows)}개 추가")


def run_once(keywords, test):
    found = scan(keywords, test=test)
    if test:
        print(f"\n[테스트 종료] 키워드 일치 총 {len(found)}개 (시트에는 쓰지 않음)")
        return
    if not found:
        print("새로 일치한 글 없음")
        return
    write_new(open_worksheet(), found)


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
