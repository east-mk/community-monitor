"""네이버 / 다음 / 구글 검색 결과에서 '제목'에 키워드가 들어간 글을 모은다.

방식 (키가 있으면 공식 API, 없으면 검색 페이지 HTML을 직접 읽음)
  네이버  뉴스·블로그·카페   NAVER_CLIENT_ID + NAVER_CLIENT_SECRET 있으면 NAVER API HUB 검색 API
                             없으면 search.naver.com 결과 페이지 (작성시각 없음, 막힐 수 있음)
  다음    웹문서·블로그·카페  KAKAO_REST_KEY 있으면 카카오(다음) 검색 API
          뉴스               search.daum.net 결과 페이지 (카카오 API에 뉴스 검색이 없음)
  구글    뉴스               구글 뉴스 RSS (키 필요 없음)

본문은 열지 않는다. 검색 결과의 제목에 키워드가 있을 때만 기록한다.
"""
import html as htmllib
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

KST = timezone(timedelta(hours=9))

# 테스트에서 바꿀 수 있도록 주소를 상수로 둠
# 2026-07-31 이후 네이버 검색 API 키는 NAVER API HUB(네이버 클라우드)에서만 발급됨
NAVER_API = "https://naverapihub.apigw.ntruss.com/search/v1/{kind}"
KAKAO_API = "https://dapi.kakao.com/v2/search/{kind}"
GOOGLE_RSS = "https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
NAVER_WEB = "https://search.naver.com/search.naver?where={where}&query={q}&sort=1"
DAUM_WEB = "https://search.daum.net/search?w={w}&q={q}&sort=recency"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# 실제로 수집할 사이트. 네이버/다음을 다시 켜려면 여기에 이름을 추가하세요. 예: {"구글", "네이버", "다음"}
ENABLED_SITES = {"구글"}

# (사이트, 분류, 방식, 인자)
SOURCES = [
    ("네이버", "뉴스", "naver", {"api": "news", "where": "news", "link": None}),
    ("네이버", "블로그", "naver", {"api": "blog", "where": "blog", "link": r"blog\.naver\.com/"}),
    ("네이버", "카페", "naver", {"api": "cafearticle", "where": "article", "link": r"cafe\.naver\.com/"}),
    ("다음", "뉴스", "daum_web", {"w": "news", "link": None}),
    ("다음", "웹문서", "kakao", {"api": "web"}),
    ("다음", "블로그", "kakao", {"api": "blog", "w": "blog",
                              "link": r"(blog\.naver\.com|tistory\.com|brunch\.co\.kr|blog\.daum\.net)/"}),
    ("다음", "카페", "kakao", {"api": "cafe", "w": "cafe", "link": r"cafe\.daum\.net/"}),
    ("구글", "뉴스", "google_rss", {}),
]

# HTML 방식에서 '뉴스 링크'로 보지 않을 주소 (검색 엔진 자체의 메뉴/광고 등)
NOT_ARTICLE = re.compile(
    r"(search\.naver\.com|search\.daum\.net|help\.naver\.com|nid\.naver\.com|"
    r"ad\.search\.naver\.com|adcr\.naver\.com|policy\.naver\.com|accounts\.kakao\.com|"
    r"www\.naver\.com/?$|www\.daum\.net/?$|keep\.naver\.com|map\.naver\.com)"
)


def _clean(text):
    """API 제목의 <b> 태그, &quot; 같은 엔티티를 정리"""
    text = re.sub(r"<[^>]+>", "", text or "")
    return re.sub(r"\s+", " ", htmllib.unescape(text)).strip()


def _norm(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def _match(title, keywords):
    # 띄어쓰기를 모두 무시하고 비교
    n = re.sub(r"\s+", "", title).lower()
    return [k for k in keywords if re.sub(r"\s+", "", k).lower() in n]


def _fmt(dt):
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M")


def _rfc822(s):
    try:
        return _fmt(parsedate_to_datetime(s))
    except Exception:
        return ""


def _iso(s):
    try:
        return _fmt(datetime.fromisoformat(s.replace("Z", "+00:00")))
    except Exception:
        return ""


def _yyyymmdd(s):
    s = (s or "").strip()
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if re.fullmatch(r"\d{8}", s) else ""


# ------------------------------------------------------------------ 방식별 수집
# 모두 [(제목, 링크, 작성시각)] 반환


def _naver_api(session, kind, query):
    r = session.get(
        NAVER_API.format(kind=kind),
        params={"query": query, "display": 100, "sort": "date"},
        headers={
            "X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLIENT_ID"],
            "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLIENT_SECRET"],
        },
        timeout=15,
    )
    r.raise_for_status()
    out = []
    for it in r.json().get("items", []):
        link = it.get("originallink") or it.get("link") or ""
        when = _rfc822(it["pubDate"]) if it.get("pubDate") else _yyyymmdd(it.get("postdate"))
        out.append((_clean(it.get("title")), link, when))
    return out


def _kakao_api(session, kind, query):
    r = session.get(
        KAKAO_API.format(kind=kind),
        params={"query": query, "sort": "recency", "size": 50},
        headers={"Authorization": f"KakaoAK {os.environ['KAKAO_REST_KEY']}"},
        timeout=15,
    )
    r.raise_for_status()
    return [
        (_clean(d.get("title")), d.get("url", ""), _iso(d.get("datetime", "")))
        for d in r.json().get("documents", [])
    ]


def _google_rss(session, query):
    r = session.get(GOOGLE_RSS.format(q=quote(f'"{query}"')), timeout=15)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    return [
        (_clean(it.findtext("title")), (it.findtext("link") or "").strip(),
         _rfc822(it.findtext("pubDate") or ""))
        for it in root.iter("item")
    ]


def _html_links(session, url, link_pattern):
    """검색 결과 페이지에서 글 링크를 추정해서 뽑는다. 작성시각은 알 수 없음."""
    r = session.get(url, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rx = re.compile(link_pattern) if link_pattern else None
    found = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href.startswith(("http", "/")):
            continue
        link, _ = urldefrag(urljoin(url, href))
        if urlparse(link).scheme not in ("http", "https") or NOT_ARTICLE.search(link):
            continue
        if rx and not rx.search(link):
            continue
        title = a.get_text(" ", strip=True)
        if len(title) < 6:  # 메뉴·버튼 같은 짧은 글자 제외
            continue
        if len(title) > len(found.get(link, "")):
            found[link] = title
    return [(t, l, "") for l, t in found.items()]


# ------------------------------------------------------------------ 전체 실행


def available(method, arg):
    """(사용할 방식 설명, 실행 함수) 또는 (None, 이유)"""
    naver_key = os.environ.get("NAVER_CLIENT_ID") and os.environ.get("NAVER_CLIENT_SECRET")
    kakao_key = os.environ.get("KAKAO_REST_KEY")
    if method == "naver":
        if naver_key:
            return "API", lambda s, q: _naver_api(s, arg["api"], q)
        return "HTML", lambda s, q: _html_links(
            s, NAVER_WEB.format(where=arg["where"], q=quote(q)), arg["link"])
    if method == "kakao":
        if kakao_key:
            return "API", lambda s, q: _kakao_api(s, arg["api"], q)
        if arg.get("w"):
            return "HTML", lambda s, q: _html_links(
                s, DAUM_WEB.format(w=arg["w"], q=quote(q)), arg["link"])
        return None, "KAKAO_REST_KEY 없음 (웹문서는 API로만 수집)"
    if method == "daum_web":
        return "HTML", lambda s, q: _html_links(
            s, DAUM_WEB.format(w=arg["w"], q=quote(q)), arg["link"])
    if method == "google_rss":
        return "RSS", lambda s, q: _google_rss(s, q)
    return None, "알 수 없는 방식"


def search_all(keywords, test=False, pause=0.4):
    """반환: [(사이트, 분류, 제목, 키워드, 링크, 작성시각)]"""
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    hits, done = [], set()

    for site, kind, method, arg in SOURCES:
        if site not in ENABLED_SITES:
            continue
        label = f"{site} / {kind}"
        mode, fn = available(method, arg)
        if mode is None:
            print(f"[건너뜀] {label}: {fn}")
            continue
        total = matched = 0
        errors = []
        sample = None
        for q in keywords:
            try:
                results = fn(session, q)
            except Exception as e:
                errors.append(f"{type(e).__name__}: {str(e)[:80]}")
                time.sleep(pause)
                continue
            total += len(results)
            for title, link, when in results:
                if not link or not title:
                    continue
                kws = _match(title, keywords)
                if not kws:
                    continue  # 제목에 키워드가 없으면 버림 (본문만 걸린 결과)
                if sample is None:
                    sample = title
                if link in done:
                    continue
                done.add(link)
                matched += 1
                hits.append((site, kind, title, ", ".join(kws), link, when))
            time.sleep(pause)

        if errors and len(errors) == len(keywords):
            print(f"[실패] {label} ({mode}): {errors[0]}")
            continue
        status = "OK" if total else "결과 0개(차단 또는 구조 변경 가능)"
        line = f"[{status}] {label} ({mode}): 검색결과 {total}개, 제목 일치 {matched}개"
        if errors:
            line += f", 일부 실패 {len(errors)}회 ({errors[0]})"
        print(line)
        if test and sample:
            print(f"        예) {sample[:60]}")
    return hits
