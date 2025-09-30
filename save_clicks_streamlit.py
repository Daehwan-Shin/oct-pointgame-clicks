import os, glob
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates
from supabase import create_client, Client

# ================================
# 1. Supabase 연결 설정
# ================================
# 🔑 Replit → Secrets (환경변수)에 SUPABASE_URL, SUPABASE_KEY 등록 필요
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================================
# 2. 설정
# ================================
IMG_DIR = "test"

# 평가자 선택
DOCTORS = ["Dr. Nam", "Dr. Shin"]
qp = getattr(st, "query_params", {})
pref = None
if isinstance(qp, dict):
    pref = qp.get("user", None)
if pref and isinstance(pref, list):
    pref = pref[0]
pref_label = None
if pref:
    if str(pref).lower() in ["nam","drnam","doctor1","dr.nam"]:
        pref_label = "Dr. Nam"
    elif str(pref).lower() in ["shin","drshin","doctor2","dr.shin"]:
        pref_label = "Dr. Shin"

with st.sidebar:
    st.header("Rater")
    rater = st.selectbox(
        "Choose evaluator",
        DOCTORS,
        index=(DOCTORS.index(pref_label) if pref_label in DOCTORS else 0)
    )
    st.caption("선택한 평가자에 따라 별도로 DB에 저장됩니다.")

# ================================
# 3. Supabase 헬퍼 함수
# ================================
def record_click(name, x, y, rater):
    data = {
        "rater": rater,
        "name": name,
        "click_x": int(x),
        "click_y": int(y),
    }
    supabase.table("clicks").insert(data).execute()

def load_done_names(rater):
    res = supabase.table("clicks").select("name").eq("rater", rater).execute()
    if res.data:
        return set([row["name"] for row in res.data])
    return set()

def load_all_clicks(rater):
    res = supabase.table("clicks").select("*").eq("rater", rater).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

# ================================
# 4. 이미지 불러오기
# ================================
imgs = sorted(glob.glob(os.path.join(IMG_DIR, "*/*.*")))
if not imgs:
    st.error(f"No images found in {IMG_DIR}. Check working directory and folder structure.")
    st.stop()

names_all = [os.path.splitext(os.path.basename(p))[0] for p in imgs]
name_to_path = {os.path.splitext(os.path.basename(p))[0]: p for p in imgs}

# ================================
# 5. 상태 관리
# ================================
if "done_set" not in st.session_state or st.session_state.get("rater") != rater:
    st.session_state.done_set = load_done_names(rater)
    remaining_names = [n for n in names_all if n not in st.session_state.done_set]
    st.session_state.idx = (names_all.index(remaining_names[0]) if remaining_names else 0)
    st.session_state.rater = rater

def current_name():
    return names_all[st.session_state.idx]

def move_next():
    for j in range(st.session_state.idx+1, len(names_all)):
        if names_all[j] not in st.session_state.done_set:
            st.session_state.idx = j; return
    st.session_state.idx = min(st.session_state.idx+1, len(names_all)-1)

def move_prev():
    for j in range(st.session_state.idx-1, -1, -1):
        if names_all[j] not in st.session_state.done_set:
            st.session_state.idx = j; return
    st.session_state.idx = max(st.session_state.idx-1, 0)

# ================================
# 6. 사이드바
# ================================
with st.sidebar:
    st.subheader("Progress / Tools")
    total = len(names_all)
    done = len(st.session_state.done_set)
    remaining = total - done
    st.write(f"총 **{total}** / 완료 **{done}** / 남음 **{remaining}**")

    r_px = st.slider("Pointing radius r (px)", 10, 120, 40, step=5)

    jump_val = st.slider("Index", 0, total-1, st.session_state.idx, key="jump_slider")
    if st.button("Jump"):
        st.session_state.idx = jump_val
        st.rerun()
    colA, colB = st.columns(2)
    with colA:
        if st.button("◀ 이전(미완)"):
            move_prev(); st.rerun()
    with colB:
        if st.button("다음(미완) ▶"):
            move_next(); st.rerun()

    # CSV 백업 다운로드
    df_all = load_all_clicks(rater)
    st.download_button("진행 CSV 다운로드", df_all.to_csv(index=False), file_name=f"clicks_{rater}.csv")


    # ================================
    # CSV 업로드 (Upsert) - form으로 감싸 자동 초기화
    # ================================
    with st.form("csv_up_form", clear_on_submit=True):
        up = st.file_uploader("CSV 업로드 (Upsert)", type=["csv"], key="csv_up")
        do_upload = st.form_submit_button("업로드 반영(Upsert)")

    if do_upload and up is not None:
        try:
            new_df = pd.read_csv(up)
            assert {"name", "click_x", "click_y"}.issubset(set(new_df.columns))

            if "rater" not in new_df.columns:
                new_df["rater"] = rater

            for _, row in new_df.iterrows():
                payload = {
                    "rater": str(row["rater"]),
                    "name": str(row["name"]),
                    "click_x": int(row["click_x"]),
                    "click_y": int(row["click_y"]),
                }
                # 1차: on_conflict 문자열 방식
                try:
                    supabase.table("clicks").upsert(
                        payload,
                        on_conflict="rater,name",
                        ignore_duplicates=False
                    ).execute()
                except Exception:
                    # 폴백: 동일키 delete 후 insert
                    supabase.table("clicks") \
                        .delete() \
                        .eq("rater", payload["rater"]) \
                        .eq("name", payload["name"]) \
                        .execute()
                    supabase.table("clicks").insert(payload).execute()

            # 진행 상태 갱신
            st.session_state.done_set = load_done_names(rater)
            st.success("CSV 업로드 내용을 Supabase에 반영했습니다. (upsert/폴백)")

            # 👇 폼이 clear_on_submit로 업로더를 비워주므로 별도 X 클릭 불필요
            # 필요 시 진행표 갱신을 위해 리런하고 싶다면 다음 한 줄을 남겨도 됩니다.
            # st.rerun()

        except Exception as e:
            st.error(f"CSV 처리 중 오류: {e}")

# ================================
# 7. 메인 화면
# ================================
name = current_name()
img_path = name_to_path[name]
img = Image.open(img_path).convert("RGB")
w, h = img.size

col_header1, col_header2 = st.columns([3, 1])
with col_header1:
    st.title(f"OCT Click Collector — {rater}")
with col_header2:
    st.metric("진행률", f"{len(st.session_state.done_set)}/{len(names_all)}")

st.write(f"📋 현재: **{name}**")
st.write(f"📐 크기: **{w}×{h}** pixels")

display_img = img
max_width = 800
display_width = min(max_width, w)

click = streamlit_image_coordinates(display_img, key=f"canvas_{name}", width=display_width)

if click and ("x" in click and "y" in click):
    disp_w = click.get("displayed_width", w)
    disp_h = click.get("displayed_height", h)
    scale_x = w / float(disp_w)
    scale_y = h / float(disp_h)

    x_orig = int(round(click["x"] * scale_x))
    y_orig = int(round(click["y"] * scale_y))

    st.info(f"📍 클릭 좌표: {x_orig}, {y_orig} / r={r_px}px")

    overlay = img.convert("RGBA")
    circle_layer = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(circle_layer, "RGBA")
    draw.ellipse(
        [x_orig - r_px, y_orig - r_px, x_orig + r_px, y_orig + r_px],
        outline=(255, 215, 0, 255), width=3,
        fill=(255, 255, 0, 80)
    )
    display_img = Image.alpha_composite(overlay, circle_layer)

    st.image(display_img, caption="클릭 영역 표시")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 저장 & 다음", type="primary"):
            record_click(name, x_orig, y_orig, rater)
            st.session_state.done_set.add(name)
            move_next(); st.rerun()
    with col2:
        if st.button("⏭️ 건너뛰기"):
            move_next(); st.rerun()

    if st.button("⬅️ 이전(미완)으로"):
        move_prev(); st.rerun()
else:
    st.info("👆 이미지 위를 클릭해서 지점을 선택하세요.")
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("⏭️ 이 이미지 건너뛰기"):
            move_next(); st.rerun()
    with col_nav2:
        if st.button("⬅️ 이전 이미지로"):
            move_prev(); st.rerun()

with st.expander("이미지 목록 / 진행 현황 보기"):
    show_df = pd.DataFrame({
        "name": names_all,
        "done": [n in st.session_state.done_set for n in names_all]
    })
    st.dataframe(show_df)
