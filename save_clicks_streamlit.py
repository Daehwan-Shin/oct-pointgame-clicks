import os, glob
import streamlit as st
import pandas as pd
from PIL import Image
import plotly.graph_objects as go
from streamlit_plotly_events import plotly_events

# 페이지 설정
st.set_page_config(layout="wide", page_title="OCT Click Collector")

# ------------------------
# 경로 설정
# ------------------------
IMG_DIR = "test"      # test/CNV, test/DME, test/DRUSEN, test/NORMAL ...
OUT_DIR = "clicks"
os.makedirs(OUT_DIR, exist_ok=True)

# ------------------------
# 평가자 선택 (사이드바)
# ------------------------
DOCTORS = ["Dr. Nam", "Dr. Shin"]

# URL 쿼리로 기본 rater 받기 (?user=nam)
qp = getattr(st, "query_params", {})
pref = None
if isinstance(qp, dict):
    pref = qp.get("user", None)
if isinstance(pref, list):
    pref = pref[0]

pref_label = None
if pref:
    low = str(pref).lower()
    if low in ["nam","drnam","doctor1","dr.nam"]:
        pref_label = "Dr. Nam"
    elif low in ["shin","drshin","doctor2","dr.shin"]:
        pref_label = "Dr. Shin"

with st.sidebar:
    st.header("Rater")
    rater = st.selectbox(
        "Choose evaluator",
        DOCTORS,
        index=(DOCTORS.index(pref_label) if pref_label in DOCTORS else 0)
    )
    st.caption("선택한 평가자에 따라 별도 CSV로 저장됩니다.")

# 파일명용 키/경로
rater_key = "nam" if rater == "Dr. Nam" else "shin"
csv_path = os.path.join(OUT_DIR, f"clicks_{rater_key}.csv")

# ------------------------
# 이미지 목록
# ------------------------
imgs = sorted(glob.glob(os.path.join(IMG_DIR, "*/*.*")))
if not imgs:
    st.error(f"No images found in {IMG_DIR} (expect subfolders: CNV/DME/DRUSEN/NORMAL).")
    st.stop()

names_all = [os.path.splitext(os.path.basename(p))[0] for p in imgs]
name_to_path = {os.path.splitext(os.path.basename(p))[0]: p for p in imgs}

# ------------------------
# 상태 초기화 (평가자별 독립 저장)
# ------------------------
if "df" not in st.session_state or st.session_state.get("rater") != rater:
    if os.path.exists(csv_path):
        st.session_state.df = pd.read_csv(csv_path)
    else:
        st.session_state.df = pd.DataFrame({"name": [], "click_y": [], "click_x": []})

    st.session_state.done_set = set(st.session_state.df["name"].astype(str).tolist())

    remaining_names = [n for n in names_all if n not in st.session_state.done_set]
    st.session_state.idx = (names_all.index(remaining_names[0]) if remaining_names else 0)

    st.session_state.rater = rater
    st.session_state.last_xy = None
    st.session_state.last_name = None

def save_df_to_disk():
    st.session_state.df.to_csv(csv_path, index=False)

def current_name():
    return names_all[st.session_state.idx]

def move_next():
    st.session_state.last_xy = None
    st.session_state.last_name = None
    for j in range(st.session_state.idx+1, len(names_all)):
        if names_all[j] not in st.session_state.done_set:
            st.session_state.idx = j
            return
    st.session_state.idx = min(st.session_state.idx+1, len(names_all)-1)

def move_prev():
    st.session_state.last_xy = None
    st.session_state.last_name = None
    for j in range(st.session_state.idx-1, -1, -1):
        if names_all[j] not in st.session_state.done_set:
            st.session_state.idx = j
            return
    st.session_state.idx = max(st.session_state.idx-1, 0)

def jump_to(k: int):
    st.session_state.last_xy = None
    st.session_state.last_name = None
    k = max(0, min(k, len(names_all)-1))
    st.session_state.idx = k

def record_click(name, y_orig, x_orig, overwrite=True):
    if overwrite and name in st.session_state.done_set:
        st.session_state.df.loc[
            st.session_state.df["name"] == name, ["click_y", "click_x"]
        ] = [y_orig, x_orig]
    else:
        st.session_state.df = pd.concat(
            [st.session_state.df,
             pd.DataFrame({"name": [name], "click_y": [y_orig], "click_x": [x_orig]})],
            ignore_index=True
        )
        st.session_state.done_set.add(name)
    save_df_to_disk()

# ------------------------
# 사이드바: 진행/툴
# ------------------------
with st.sidebar:
    st.subheader("Progress / Tools")
    total = len(names_all); done = len(st.session_state.done_set); remaining = total - done
    st.write(f"총 **{total}** / 완료 **{done}** / 남음 **{remaining}**")

    # 클릭 원 반지름 (원본 픽셀 단위)
    r_px = st.slider("Pointing radius r (px)", 10, 120, 40, step=5,
                     help="클릭 지점을 중심으로 원을 표시 (원본 픽셀 기준)")

    # 점프/이동
    jump_val = st.slider("Index", 0, total-1, st.session_state.idx, key="jump_slider")
    if st.button("Jump"):
        jump_to(jump_val); st.rerun()
    colA, colB = st.columns(2)
    with colA:
        if st.button("◀ 이전(미완)"):
            move_prev(); st.rerun()
    with colB:
        if st.button("다음(미완) ▶"):
            move_next(); st.rerun()

    # Undo
    if st.button("Undo (마지막 저장 취소)"):
        if len(st.session_state.df) > 0:
            last_name = st.session_state.df.iloc[-1]["name"]
            st.session_state.df = st.session_state.df.iloc[:-1].reset_index(drop=True)
            if last_name not in st.session_state.df["name"].values:
                try:
                    st.session_state.done_set.remove(last_name)
                except KeyError:
                    pass
            save_df_to_disk()
            st.success("마지막 저장을 취소했습니다."); st.rerun()
        else:
            st.info("취소할 저장 내역이 없습니다.")

    # Reset
    if st.button("처음부터 다시 시작 (Reset CSV)"):
        st.session_state.df = pd.DataFrame({"name": [], "click_y": [], "click_x": []})
        st.session_state.done_set = set()
        save_df_to_disk()
        st.session_state.idx = 0
        st.session_state.last_xy = None
        st.session_state.last_name = None
        st.success("CSV를 초기화했습니다."); st.rerun()

    # 다운로드 / 업로드
    st.download_button("진행 CSV 다운로드", st.session_state.df.to_csv(index=False),
                       file_name=f"clicks_{rater_key}.csv")
    up = st.file_uploader("CSV 업로드(이어하기/병합)", type=["csv"])
    if up is not None:
        try:
            new_df = pd.read_csv(up)
            assert {"name","click_y","click_x"}.issubset(set(new_df.columns))
            base = st.session_state.df.set_index("name")
            add = new_df.set_index("name")
            merged = base.combine_first(add); merged.update(add)
            st.session_state.df = merged.reset_index()
            st.session_state.done_set = set(st.session_state.df["name"].astype(str).tolist())
            save_df_to_disk()
            rem = [n for n in names_all if n not in st.session_state.done_set]
            if rem:
                st.session_state.idx = names_all.index(rem[0])
            st.success("업로드 CSV를 반영했습니다."); st.rerun()
        except Exception as e:
            st.error(f"CSV 처리 중 오류: {e}")

# ------------------------
# 메인: Plotly로 이미지 클릭 (반응형, 크롭 없음)
# ------------------------
from streamlit_plotly_events import plotly_events
import plotly.graph_objects as go

# ------------------------
# 메인: Plotly로 이미지 클릭 (반응형, 크롭 없음)
# ------------------------
name = current_name()
img_path = name_to_path[name]
img = Image.open(img_path).convert("RGB")
w, h = img.size

col_header1, col_header2 = st.columns([3, 1])
with col_header1:
    st.title(f"OCT Click Collector — {rater}")
with col_header2:
    st.metric("진행률", f"{len(st.session_state.done_set)}/{len(names_all)}")

st.write(f"📋 현재: **{name}** — 원본 {w}×{h}px")
st.caption("이미지를 클릭하면 좌표가 원본 픽셀 단위로 기록됩니다. (마지막 클릭만 표시)")

# 마지막 클릭 좌표 초기화(이미지 바뀔 때)
if st.session_state.get("last_name") != name:
    st.session_state.last_xy = None
    st.session_state.last_name = name

fig = go.Figure()

# 1) 축을 확실히 만들기 위한 투명 trace (도메인/범위 고정용)
#    이게 없으면 일부 환경에서 layout_image가 안 보입니다.
fig.add_trace(
    go.Scatter(
        x=[0, w], y=[0, h],
        mode="markers",
        opacity=0,
        hoverinfo="skip",
        showlegend=False
    )
)

# 2) 배경 이미지 삽입
# y축을 [h,0]으로 뒤집을 것이므로, top-left 정렬을 위해 y=h에 배치합니다.
fig.add_layout_image(
    dict(
        source=img,            # PIL.Image 그대로 사용 가능
        xref="x", yref="y",
        x=0, y=h,              # 좌상단 기준
        sizex=w, sizey=h,
        sizing="stretch",      # 축 크기에 맞춰 정확히 채우기
        layer="below"
    )
)

# 3) 축 설정: 픽셀 좌표계, y축 뒤집기(위가 0 → 클릭 좌표가 원본과 동일)
fig.update_xaxes(visible=False, range=[0, w], constrain="domain")
fig.update_yaxes(visible=False, range=[h, 0], scaleanchor="x", scaleratio=1)

# 4) 마지막 클릭이 있으면 원(shape)으로 표시
if st.session_state.last_xy is not None:
    cx, cy = st.session_state.last_xy
    fig.add_shape(
        type="circle", xref="x", yref="y",
        x0=cx - r_px, y0=cy - r_px, x1=cx + r_px, y1=cy + r_px,
        line=dict(color="gold", width=3),
        fillcolor="rgba(255,255,0,0.28)"
    )

# 배경 투명/여백 제거
fig.update_layout(
    margin=dict(l=0, r=0, t=0, b=0),
    dragmode=False,
    hovermode=False,
    template=None,
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)

# 5) 표시 높이를 적당히 잡아주면 확실히 보입니다 (반응형 유지)
#    가로 800px 기준 비율로 계산 (최소 320px 보장)
override_h = max(320, int(h * min(1.0, 800 / max(w, 1))))

events = plotly_events(
    fig,
    click_event=True,
    hover_event=False,
    select_event=False,
    override_height=override_h,
    override_width=None,     # 컨테이너 폭에 맞춤
    key=f"plt_{name}"
)

# 6) 좌표 처리
if events:
    ex = events[0].get("x")
    ey = events[0].get("y")
    if ex is not None and ey is not None:
        x_orig = int(round(ex))
        y_orig = int(round(ey))
        st.session_state.last_xy = (x_orig, y_orig)

        st.info(f"📍 원본 좌표: x={x_orig}, y={y_orig} / r={r_px}px")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("저장 & 다음"):
                record_click(name, y_orig, x_orig, overwrite=True)
                st.session_state.last_xy = None
                move_next(); st.rerun()
        with c2:
            if st.button("건너뛰기"):
                st.session_state.last_xy = None
                move_next(); st.rerun()
        with c3:
            if st.button("이전(미완)으로"):
                st.session_state.last_xy = None
                move_prev(); st.rerun()
else:
    st.info("👆 이미지를 클릭하여 좌표를 찍어주세요.")
    n1, n2 = st.columns(2)
    with n1:
        if st.button("⏭️ 이 이미지 건너뛰기"):
            move_next(); st.rerun()
    with n2:
        if st.button("⬅️ 이전 이미지로"):
            move_prev(); st.rerun()


with st.expander("이미지 목록 / 진행 현황 보기"):
    show_df = pd.DataFrame({"name": names_all, "done": [n in st.session_state.done_set for n in names_all]})
    st.dataframe(show_df)
