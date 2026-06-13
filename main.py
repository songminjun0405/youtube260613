import re
from collections import Counter

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud

from googleapiclient.discovery import build

try:
    from konlpy.tag import Okt
    okt = Okt()
except:
    okt = None

st.set_page_config(
    page_title="유튜브 댓글 심층 분석기",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 유튜브 댓글 심층 분석기")
st.markdown("유튜브 링크를 입력하면 댓글을 수집하고 심층 분석합니다. 🚀")

api_key = st.text_input(
    "🔑 YouTube API Key",
    type="password"
)

youtube_url = st.text_input(
    "📺 유튜브 링크"
)

max_comments = st.slider(
    "댓글 수집 개수",
    100,
    1000,
    300,
    100
)


def extract_video_id(url):
    patterns = [
        r"v=([^&]+)",
        r"youtu\.be/([^?]+)",
        r"shorts/([^?]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def get_comments(api_key, video_id, max_count=300):

    youtube = build(
        "youtube",
        "v3",
        developerKey=api_key
    )

    comments = []

    next_page_token = None

    while len(comments) < max_count:

        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            pageToken=next_page_token,
            textFormat="plainText"
        )

        response = request.execute()

        for item in response["items"]:

            text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]

            likes = item["snippet"]["topLevelComment"]["snippet"]["likeCount"]

            comments.append({
                "comment": text,
                "likes": likes
            })

            if len(comments) >= max_count:
                break

        next_page_token = response.get("nextPageToken")

        if not next_page_token:
            break

    return pd.DataFrame(comments)


def analyze_sentiment(comment):

    positive_words = [
        "좋다", "최고", "감동", "사랑",
        "재밌다", "멋지다", "대박",
        "훌륭", "행복", "감사"
    ]

    negative_words = [
        "별로", "싫다", "최악",
        "실망", "아쉽다",
        "화난다", "짜증"
    ]

    score = 0

    for word in positive_words:
        if word in comment:
            score += 1

    for word in negative_words:
        if word in comment:
            score -= 1

    return score


def extract_keywords(texts):

    if okt:

        nouns = []

        for text in texts:
            nouns.extend(okt.nouns(text))

        nouns = [
            n for n in nouns
            if len(n) >= 2
        ]

        return Counter(nouns)

    text = " ".join(texts)

    words = re.findall(r"[가-힣]{2,}", text)

    return Counter(words)


if st.button("🚀 댓글 분석 시작"):

    if not api_key:
        st.error("API Key를 입력하세요.")
        st.stop()

    video_id = extract_video_id(youtube_url)

    if not video_id:
        st.error("유효한 유튜브 링크가 아닙니다.")
        st.stop()

    with st.spinner("댓글 수집 중..."):

        df = get_comments(
            api_key,
            video_id,
            max_comments
        )

    if df.empty:
        st.warning("댓글을 찾을 수 없습니다.")
        st.stop()

    st.balloons()

    st.success(f"🎉 {len(df)}개의 댓글 분석 완료!")

    # -------------------------
    # 기본 통계
    # -------------------------

    st.header("📊 댓글 통계")

    avg_length = df["comment"].str.len().mean()
    avg_like = df["likes"].mean()

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "총 댓글 수",
        len(df)
    )

    col2.metric(
        "평균 댓글 길이",
        round(avg_length, 1)
    )

    col3.metric(
        "평균 좋아요",
        round(avg_like, 1)
    )

    # -------------------------
    # 감성 분석
    # -------------------------

    st.header("😊 감성 분석")

    df["sentiment"] = df["comment"].apply(
        analyze_sentiment
    )

    positive = (df["sentiment"] > 0).sum()
    neutral = (df["sentiment"] == 0).sum()
    negative = (df["sentiment"] < 0).sum()

    sentiment_df = pd.DataFrame({
        "구분": ["긍정", "중립", "부정"],
        "개수": [positive, neutral, negative]
    })

    st.dataframe(sentiment_df)

    # -------------------------
    # 인기 댓글
    # -------------------------

    st.header("🔥 인기 댓글 TOP 10")

    top_comments = (
        df.sort_values(
            "likes",
            ascending=False
        )
        .head(10)
    )

    st.dataframe(top_comments)

    # -------------------------
    # 키워드 분석
    # -------------------------

    st.header("🔍 핵심 키워드")

    keywords = extract_keywords(
        df["comment"].tolist()
    )

    keyword_df = pd.DataFrame(
        keywords.most_common(30),
        columns=["키워드", "빈도"]
    )

    st.dataframe(keyword_df)

    # -------------------------
    # 워드클라우드
    # -------------------------

    st.header("☁️ 워드클라우드")

    if len(keywords) > 0:

        # Streamlit Cloud용
        # app.py와 같은 폴더에
        # NanumGothic.ttf 업로드 필요

        wc = WordCloud(
            font_path="NanumGothic.ttf",
            width=1200,
            height=600,
            background_color="white"
        )

        img = wc.generate_from_frequencies(
            keywords
        )

        fig, ax = plt.subplots(
            figsize=(12, 6)
        )

        ax.imshow(img)
        ax.axis("off")

        st.pyplot(fig)

    else:
        st.warning(
            "워드클라우드를 생성할 키워드가 없습니다."
        )

    # -------------------------
    # 원본 댓글
    # -------------------------

    st.header("📝 원본 댓글 데이터")

    st.dataframe(df)
