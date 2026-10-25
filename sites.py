"""감시 대상 사이트 설정

각 사이트:
  name     시트의 '커뮤니티' 열에 표시될 이름
  boards   [(시트의 '게시판' 열에 표시될 이름, 목록 페이지 URL), ...]
  pattern  '게시글 링크'를 골라내는 정규식 (절대 URL에 적용됨)
  enabled  False면 건너뜀

주의: 아래 URL/패턴은 대표 게시판 기준의 추정값입니다.
`python monitor.py --test` 로 돌려서 '글 0개'로 나오는 곳은
브라우저로 해당 게시판 주소를 확인해 boards의 URL과 pattern을 고쳐주세요.
게시판을 추가하려면 boards에 (이름, URL)만 한 줄 더 넣으면 됩니다.
"""

SITES = [
    {
        "name": "디시인사이드",
        "boards": [("실시간 베스트", "https://gall.dcinside.com/board/lists/?id=dcbest")],
        "pattern": r"gall\.dcinside\.com/(mgallery/|mini/)?board/view/",
    },
    {
        "name": "뽐뿌",
        "boards": [
            ("핫게시글", "https://www.ppomppu.co.kr/hot.php"),
            ("자유게시판", "https://www.ppomppu.co.kr/zboard/zboard.php?id=freeboard"),
        ],
        "pattern": r"ppomppu\.co\.kr/.*view\.php",
    },
    {
        "name": "더쿠",
        "boards": [("핫이슈", "https://theqoo.net/hot"), ("스퀘어", "https://theqoo.net/square")],
        "pattern": r"theqoo\.net/(hot/|square/)?\d{6,}",
    },
    {
        "name": "인스티즈",
        "boards": [("인기글", "https://www.instiz.net/pt"), ("익명잡담", "https://www.instiz.net/name")],
        "pattern": r"instiz\.net/(pt|name|name_enter)/\d+",
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
    },
    {
        "name": "아카라이브",
        "boards": [("라이브 채널", "https://arca.live/b/live")],
        "pattern": r"arca\.live/b/\w+/\d+",
    },
    {
        "name": "인벤",
        "boards": [("오픈이슈", "https://www.inven.co.kr/board/webzine/2097")],
        "pattern": r"inven\.co\.kr/board/.+/\d+/\d+",
    },
    {
        "name": "루리웹",
        "boards": [("유머 베스트", "https://bbs.ruliweb.com/best/humor")],
        "pattern": r"ruliweb\.com/.+/read/\d+",
    },
    {
        "name": "네이트판",
        "boards": [("랭킹", "https://pann.nate.com/talk/ranking")],
        "pattern": r"pann\.nate\.com/talk/\d+",
    },
    {
        "name": "디미토리",
        "boards": [("메인", "https://dmitory.com/")],
        "pattern": r"dmitory\.com/.*\d{5,}",
    },
    {
        "name": "해연갤",
        "enabled": False,
        "note": "해외연예 갤러리의 갤러리 id를 확인해 boards에 URL을 넣고 enabled를 True로 바꾸세요",
        "boards": [("해외연예", "https://gall.dcinside.com/board/lists/?id=여기에갤러리ID")],
        "pattern": r"gall\.dcinside\.com/(mgallery/|mini/)?board/view/",
    },
    {
        "name": "82쿡",
        "boards": [("자유게시판", "https://www.82cook.com/entiz/enti.php?bn=15")],
        "pattern": r"82cook\.com/entiz/read\.php",
    },
    {
        "name": "클리앙",
        "boards": [("전체 인기", "https://www.clien.net/service/group/clien_all")],
        "pattern": r"clien\.net/service/board/\w+/\d+",
    },
    {
        "name": "다모앙",
        "boards": [("자유게시판", "https://damoang.net/free")],
        "pattern": r"damoang\.net/\w+/\d+",
    },
    {
        "name": "퀘이사존",
        "boards": [("자유게시판", "https://quasarzone.com/bbs/qf_free")],
        "pattern": r"quasarzone\.com/bbs/\w+/views/\d+",
    },
    {
        "name": "쿨엔조이",
        "boards": [("자유게시판", "https://coolenjoy.net/bbs/freeboard")],
        "pattern": r"coolenjoy\.net/bbs/\w+/\d+",
    },
    {
        "name": "엠팍",
        "boards": [("불펜", "https://mlbpark.donga.com/mp/b.php?b=bullpen")],
        "pattern": r"mlbpark\.donga\.com/mp/b\.php\?.*id=",
    },
    {
        "name": "사커라인",
        "boards": [("자유게시판", "https://soccerline.kr/board/free")],
        "pattern": r"soccerline\.kr/board/\w+/\d+",
    },
    {
        "name": "NBA매니아",
        "boards": [("자유게시판", "https://nbamania.com/g2/bbs/board.php?bo_table=freeboard")],
        "pattern": r"nbamania\.com/.*wr_id=\d+",
    },
    {
        "name": "보배드림",
        "boards": [("베스트", "https://www.bobaedream.co.kr/list?code=best")],
        "pattern": r"bobaedream\.co\.kr/view\?code=",
    },
    {
        "name": "SLR클럽",
        "boards": [("자유게시판", "https://www.slrclub.com/bbs/zboard.php?id=free")],
        "pattern": r"slrclub\.com/bbs/vx2\.php",
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
    },
    {
        "name": "웃긴대학",
        "boards": [("웃긴자료", "https://web.humoruniv.com/board/humor/list.html?table=pds")],
        "pattern": r"humoruniv\.com/board/(humor/)?read\.html",
    },
    {
        "name": "이토랜드",
        "boards": [("유머", "https://www.etoland.co.kr/bbs/board.php?bo_table=etohumor01")],
        "pattern": r"etoland\.co\.kr/bbs/board\.php\?.*wr_id=",
    },
    {
        "name": "오늘의유머",
        "boards": [("베스트오브베스트", "https://www.todayhumor.co.kr/board/list.php?table=bestofbest")],
        "pattern": r"todayhumor\.co\.kr/board/view\.php",
    },
    {
        "name": "PGR21",
        "boards": [("자유게시판", "https://pgr21.com/freedom")],
        "pattern": r"pgr21\.com/\w+/\d+",
    },
]
