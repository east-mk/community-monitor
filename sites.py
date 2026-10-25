"""감시 대상 사이트 설정

각 사이트:
  name     시트의 '커뮤니티' 열에 표시될 이름
  boards   [(시트의 '게시판' 열에 표시될 이름, 목록 페이지 URL), ...]
  pattern  '게시글 링크'를 골라내는 정규식 (절대 URL에 적용됨)
  body     글 '본문' 영역의 CSS 선택자 (쉼표로 여러 개 가능).
           본문만 검사해야 사이드바의 인기글 제목 같은 것 때문에 오탐이 안 생깁니다.
           비워 두거나 못 찾으면 페이지 전체에서 추정해서 읽고,
           그때는 시트의 '일치위치'에 '본문(불확실)'로 표시됩니다.
  enabled  False면 건너뜀

주의: 아래 URL/패턴/본문 선택자는 모두 추정값입니다.
`python monitor.py --test` 로 돌려서 아래 항목을 확인하세요.
  - '글 0개'                 -> boards의 URL이나 pattern이 안 맞음 (또는 차단)
  - '선택자 미적용(일반 추출)' -> body 선택자가 안 맞음
게시판을 추가하려면 boards에 (이름, URL)만 한 줄 더 넣으면 됩니다.
"""

SITES = [
    {
               "boards": [
            ("실시간 베스트", "https://gall.dcinside.com/board/lists/?id=dcbest"),
            ("오티켓", "https://gall.dcinside.com/mgallery/board/lists/?id=oticket"),
            ("롯데리아", "https://gall.dcinside.com/board/lists/?id=lotteria"),
        ],
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
        "name": "X(트위터)",
        "enabled": False,
        "note": "무료로 안정적인 수집 방법 없음 (공식 API 유료, 비공식 우회는 차단/약관 문제)",
        "boards": [],
        "pattern": "",
    },
    {
        "name": "에펨코리아",
        "boards": [("포텐터짐", "https://www.fmkorea.com/best")],
        "pattern": r"fmkorea\.com/\d{6,}",
        "body": ".rd_body article, .rd_body .xe_content",
    },
    {
        "name": "아카라이브",
        "boards": [("라이브 채널", "https://arca.live/b/live")],
        "pattern": r"arca\.live/b/\w+/\d+",
        "body": ".article-body .fr-view, .article-body",
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
    {
        "name": "디미토리",
        "boards": [("메인", "https://dmitory.com/")],
        "pattern": r"dmitory\.com/.*\d{5,}",
        "body": "",
    },
    {
        "name": "해연갤",
        "enabled": False,
        "note": "해외연예 갤러리의 갤러리 id를 확인해 boards에 URL을 넣고 enabled를 True로 바꾸세요",
        "boards": [("해외연예", "https://gall.dcinside.com/board/lists/?id=여기에갤러리ID")],
        "pattern": r"gall\.dcinside\.com/(mgallery/|mini/)?board/view/",
        "body": ".write_div",
    },
    {
        "name": "82쿡",
        "boards": [("자유게시판", "https://www.82cook.com/entiz/enti.php?bn=15")],
        "pattern": r"82cook\.com/entiz/read\.php",
        "body": "#articleBody",
    },
    {
        "name": "클리앙",
        "boards": [("전체 인기", "https://www.clien.net/service/group/clien_all")],
        "pattern": r"clien\.net/service/board/\w+/\d+",
        "body": ".post_article, .post_content",
    },
    {
        "name": "다모앙",
        "boards": [("자유게시판", "https://damoang.net/free")],
        "pattern": r"damoang\.net/\w+/\d+",
        "body": "#bo_v_con, .view-content",
    },
    {
        "name": "퀘이사존",
        "boards": [("자유게시판", "https://quasarzone.com/bbs/qf_free")],
        "pattern": r"quasarzone\.com/bbs/\w+/views/\d+",
        "body": ".view-content, #new_contents",
    },
    {
        "name": "쿨엔조이",
        "boards": [("자유게시판", "https://coolenjoy.net/bbs/freeboard")],
        "pattern": r"coolenjoy\.net/bbs/\w+/\d+",
        "body": "#bo_v_con",
    },
    {
        "name": "엠팍",
        "boards": [("불펜", "https://mlbpark.donga.com/mp/b.php?b=bullpen")],
        "pattern": r"mlbpark\.donga\.com/mp/b\.php\?.*id=",
        "body": "#contentDetail, .ar_txt",
    },
    {
        "name": "사커라인",
        "boards": [("자유게시판", "https://soccerline.kr/board/free")],
        "pattern": r"soccerline\.kr/board/\w+/\d+",
        "body": "",
    },
    {
        "name": "NBA매니아",
        "boards": [("자유게시판", "https://mania.kr/g2/bbs/board.php?bo_table=freeboard")],
        "pattern": r"(nbamania\.com|mania\.kr)/.*wr_id=\d+",
        "body": "#bo_v_con",
    },
    {
        "name": "보배드림",
        "boards": [("베스트", "https://www.bobaedream.co.kr/list?code=best")],
        "pattern": r"bobaedream\.co\.kr/view\?code=",
        "body": ".bodyCont, .article-body",
    },
    {
        "name": "SLR클럽",
        "boards": [("자유게시판", "https://www.slrclub.com/bbs/zboard.php?id=free")],
        "pattern": r"slrclub\.com/bbs/vx2\.php",
        "body": "#userct",
    },
    {
        "name": "블라인드",
        "enabled": False,
        "note": "앱/로그인 중심이라 공개 목록 수집이 사실상 불가",
        "boards": [],
        "pattern": "",
    },
    {
        "name": "에브리타임",
        "enabled": False,
        "note": "학교 인증 로그인 필요 (수집 불가)",
        "boards": [],
        "pattern": "",
    },
    {
        "name": "개드립",
        "boards": [("개드립", "https://www.dogdrip.net/dogdrip")],
        "pattern": r"dogdrip\.net/\d{6,}",
        "body": "#article_1, .xe_content",
    },
    {
        "name": "웃긴대학",
        "boards": [("웃긴자료", "https://web.humoruniv.com/board/humor/list.html?table=pds")],
        "pattern": r"humoruniv\.com/board/(humor/)?read\.html",
        "body": "#wrap_copy, .body_editor",
    },
    {
        "name": "이토랜드",
        "boards": [("유머", "https://www.etoland.co.kr/bbs/board.php?bo_table=etohumor01")],
        "pattern": r"etoland\.co\.kr/bbs/board\.php\?.*wr_id=",
        "body": "#bo_v_con, .view_content",
    },
    {
        "name": "오늘의유머",
        "boards": [("베스트오브베스트", "https://www.todayhumor.co.kr/board/list.php?table=bestofbest")],
        "pattern": r"todayhumor\.co\.kr/board/view\.php",
        "body": ".viewContent",
    },
    {
        "name": "PGR21",
        "boards": [("자유게시판", "https://pgr21.com/freedom")],
        "pattern": r"pgr21\.com/\w+/\d+",
        "body": ".ct_wrap, .article_body, article",
    },
]
