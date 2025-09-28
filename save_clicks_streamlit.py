import os, glob
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates

# ------------------------
# 설정
# ------------------------
IMG_DIR = "test"
OUT_DIR = "clicks"
os.makedirs(OUT_DIR, exist_ok=True)

# ------------------------
# 평가자 선택 (사이드바)
# ------------------------
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
    st.caption("선택한 평가자에 따라 별도 CSV로 저장됩니다.")

# 파일명용 키/경로
rater_key = "nam" if rater == "Dr. Nam" else "shin"
csv_path = os.path.join(OUT_DIR, f"clicks_{rater_key}.csv")

# ------------------------
# 이미지 목록
# ------------------------
imgs = sorted(glob.glob(os.path.join(IMG_DIR, "*/*.*")))
if not imgs:
    st.error(f"No images found in {IMG_DIR}. Check working directory and folder structure.")
    st.stop()

names_all = [os.path.splitext(os.path.basename(p))[0] for p in imgs]
name_to_path = {os.path.splitext(os.path.basename(p))[0]: p for p in imgs}

# ------------------------
# 상태 초기화
# ------------------------
if "df" not in st.session_state or st.session_state.get("rater") != rater:
    if os.path.exists(csv_path):
        st.session_state.df = pd.read_csv(csv_path)
    else:
        st.session_state.df = pd.DataFrame({"name": [], "click_y": [], "click_x": []})

    st.session_state.done_set = set(st.session_state.df["name"].astype(str).tolist())

    # 다음 시작 index = 완료하지 않은 이미지 중 첫 번째
    remaining_names = [n for n in names_all if n not in st.session_state.done_set]
    st.session_state.idx = (names_all.index(remaining_names[0]) if remaining_names else 0)

    # 현재 rater를 기록해서, rater가 바뀌면 다시 초기화
    st.session_state.rater = rater

def save_df_to_disk():
    st.session_state.df.to_csv(csv_path, index=False)

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

def jump_to(k: int):
    k = max(0, min(k, len(names_all)-1)); st.session_state.idx = k

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
# 사이드바: 진행/툴 + 원 반지름 설정
# ------------------------
with st.sidebar:
    st.subheader("Progress / Tools")
    total = len(names_all); done = len(st.session_state.done_set); remaining = total - done
    st.write(f"총 **{total}** / 완료 **{done}** / 남음 **{remaining}**")

    # 원 반지름
    r_px = st.slider("Pointing radius r (px)", 10, 120, 40, step=5,
                     help="클릭 지점을 중심으로 원을 표시")

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
                try: st.session_state.done_set.remove(last_name)
                except KeyError: pass
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
            st.session_state.idx = (names_all.index(rem[0]) if rem else st.session_state.idx)
            st.success("업로드 CSV를 반영했습니다."); st.rerun()
        except Exception as e:
            st.error(f"CSV 처리 중 오류: {e}")

# ------------------------
# 메인: 이미지 + 클릭 → 마지막 클릭만 원 표시
# ------------------------
# 현재 이미지
name = current_name()
img_path = name_to_path[name]
img = Image.open(img_path).convert("RGB")
w, h = img.size

st.title(f"OCT Click Collector — {rater}")
st.write(f"현재: **{name}**  ({w}×{h})")

# 원본으로 시작
display_img = img

# 클릭 좌표 읽기 (이전 프레임에서 얻어옴)
click = streamlit_image_coordinates(display_img, key=f"canvas_{name}", width=None)

if click and ("x" in click and "y" in click):
    disp_w = click.get("displayed_width", w)
    disp_h = click.get("displayed_height", h)
    scale_x = w / float(disp_w)
    scale_y = h / float(disp_h)

    x_orig = int(round(click["x"] * scale_x))
    y_orig = int(round(click["y"] * scale_y))

    st.info(f"📍 클릭 좌표: {x_orig}, {y_orig} / r={r_px}px")

    # 오버레이 합성
    overlay = img.convert("RGBA")
    circle_layer = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(circle_layer, "RGBA")
    draw.ellipse(
        [x_orig - r_px, y_orig - r_px, x_orig + r_px, y_orig + r_px],
        outline=(255, 215, 0, 255),
        width=3,
        fill=(255, 255, 0, 80)
    )
    display_img = Image.alpha_composite(overlay, circle_layer)

    # 클릭된 overlay 이미지를 다시 표시 (같은 자리)
    st.image(display_img, caption="클릭 영역 표시")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("저장 & 다음", type="primary"):
            record_click(name, y_orig, x_orig, overwrite=True)
            move_next(); st.rerun()
    with col2:
        if st.button("건너뛰기"):
            move_next(); st.rerun()
    with col3:
        if st.button("이전(미완)으로"):
            move_prev(); st.rerun()
else:
    st.write("이미지 위를 클릭하여 좌표를 찍어주세요.")

with st.expander("이미지 목록 / 진행 현황 보기"):
    show_df = pd.DataFrame({
        "name": names_all,
        "done": [n in st.session_state.done_set for n in names_all]
    })
    st.dataframe(show_df)
