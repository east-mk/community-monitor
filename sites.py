"""감시 대상 사이트 설정

각 사이트:
  name     시트의 '커뮤니티' 열에 표시될 이름
  boards   [(시트의 '게시판' 열에 표시될 이름, 목록 페이지 URL), ...]
  pattern  '게시글 링크'를 골라내는 정규식 (절대 URL에 적용됨)
  body     글 '본문' 영역의 CSS 선택자 (쉼표로 여러 개 가능).
           본문만 검사해야 사이드바의 인기글 제목 같은 것 때문에 오탐이 안 생깁니다.
           비워 두거나 못 찾으면 페이지 전체에서 추정해서 읽고,
           그때는 시트의 '일치위치'에 '본문(불확실)'로 표시됩니다.
  enabled  False면 건너뜀 (생략하면 켜짐)

주의: 아래 URL/패턴/본문 선택자는 모두 추정값입니다.
`python monitor.py --test` 로 돌려서 아래 항목을 확인하세요.
  - '글 0개'                 -> boards의 URL이나 pattern이 안 맞음 (또는 차단)
  - '선택자 미적용(일반 추출)' -> body 선택자가 안 맞음
게시판을 추가하려면 boards에 (이름, URL)만 한 줄 더 넣으면 됩니다.
"""

SITES = [
    {
        "name": "디시인사이드",
        "boards": [
            ("실시간 베스트", "https://gall.dcinside.com/board/lists/?id=dcbest"),
            ("오티켓", "https://gall.dcinside.com/mgallery/board/lists/?id=oticket"),
            ("롯데리아", "https://gall.dcinside.com/board/lists/?id=lotteria"),
            ("롯데시네마", "https://gall.dcinside.com/mgallery/board/lists/?id=cinemalotte"),
        ],
        "pattern": r"gall\.dcinside\.com/(mgallery/|mini/)?board/view/",
        "body": ".write_div",
    },
    {
        "name": "뽐뿌",
        "boards": [
            ("핫게시글", "https://www.ppomppu.co.kr/hot.php"),
            ("자유게시판", "https://www.ppomppu.co.kr/zboard/zboard.php?id=freeboard"),
        ],
        "pattern": r"ppomppu\.co\.kr/.*view\.php",
        "body": "td.board-contents, #realArticleContents",
    },
    {
        "name": "더쿠",
        "boards": [("핫이슈", "https://theqoo.net/hot"), ("스퀘어", "https://theqoo.net/square")],
        "pattern": r"theqoo\.net/(hot/|square/)?\d{6,}",
        "body": ".rd_body .xe_content, article .xe_content",
    },
    {
        "name": "인스티즈",
        "boards": [("인기글", "https://www.instiz.net/pt"), ("익명잡담", "https://www.instiz.net/name")],
        "pattern": r"instiz\.net/(pt|name|name_enter)/\d+",
        "body": "#memo_content_1, .memo_content",
    },
    {
        "name": "인벤",
        "boards": [("오픈이슈", "https://www.inven.co.kr/board/webzine/2097")],
        "pattern": r"inven\.co\.kr/board/.+/\d+/\d+",
        "body": "#powerbbsContent, .articleContent",
    },
    {
        "name": "루리웹",
        "boards": [("유머 베스트", "https://bbs.ruliweb.com/best/humor")],
        "pattern": r"ruliweb\.com/.+/read/\d+",
        "body": ".view_content, article .row .col",
    },
    {
        "name": "네이트판",
        "boards": [("랭킹", "https://pann.nate.com/talk/ranking")],
        "pattern": r"pann\.nate\.com/talk/\d+",
        "body": "#contentArea, .posting",
    },
]
