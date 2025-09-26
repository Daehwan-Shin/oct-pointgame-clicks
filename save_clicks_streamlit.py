# save_clicks_streamlit.py
import os, glob, io, base64
import streamlit as st
import pandas as pd
from PIL import Image
from hover_click_component import hover_click  # 새 컴포넌트

if st.sidebar.checkbox("🔧 import 테스트"):
    import hover_click_component
    st.write("hover_click_component loaded from:", hover_click_component.__file__)

# ------------------------
# 설정
# ------------------------
IMG_DIR = "test"
OUT_DIR = "clicks"
os.makedirs(OUT_DIR, exist_ok=True)

# ------------------------
# 유틸
# ------------------------
def pil_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

def get_qp():
    qp = getattr(st, "query_params", None)
    if isinstance(qp, dict): return qp
    try: return st.experimental_get_query_params()
    except Exception: return {}

# ------------------------
# 평가자 선택
# ------------------------
DOCTORS = ["Dr. Nam", "Dr. Shin"]
qp = get_qp()
pref = qp.get("user", None)
if isinstance(pref, list): pref = pref[0]
pref_label = None
if pref:
    p = str(pref).lower()
    if p in ["nam","drnam","doctor1","dr.nam"]: pref_label = "Dr. Nam"
    elif p in ["shin","drshin","doctor2","dr.shin"]: pref_label = "Dr. Shin"

with st.sidebar:
    st.header("Rater")
    rater = st.selectbox("Choose evaluator", DOCTORS,
                         index=(DOCTORS.index(pref_label) if pref_label in DOCTORS else 0))
rater_key = "nam" if rater == "Dr. Nam" else "shin"
csv_path = os.path.join(OUT_DIR, f"clicks_{rater_key}.csv")

# ------------------------
# 데이터/상태
# ------------------------
imgs = sorted(glob.glob(os.path.join(IMG_DIR, "*/*.*")))
if not imgs:
    st.error(f"No images found in {IMG_DIR}."); st.stop()

names_all = [os.path.splitext(os.path.basename(p))[0] for p in imgs]
name_to_path = {os.path.splitext(os.path.basename(p))[0]: p for p in imgs}

if "df" not in st.session_state:
    st.session_state.df = pd.read_csv(csv_path) if os.path.exists(csv_path) else pd.DataFrame(columns=["name","click_y","click_x"])
if "done_set" not in st.session_state:
    st.session_state.done_set = set(st.session_state.df["name"].astype(str).tolist())
if "idx" not in st.session_state:
    remaining = [n for n in names_all if n not in st.session_state.done_set]
    st.session_state.idx = (names_all.index(remaining[0]) if remaining else 0)

def save_df(): st.session_state.df.to_csv(csv_path, index=False)
def current_name(): return names_all[st.session_state.idx]
def move_next():
    for j in range(st.session_state.idx+1, len(names_all)):
        if names_all[j] not in st.session_state.done_set:
            st.session_state.idx = j; return
    st.session_state.idx = min(st.session_state.idx+1, len(names_all)-1)

# ------------------------
# 사이드바 도구
# ------------------------
with st.sidebar:
    total = len(names_all); done = len(st.session_state.done_set)
    st.write(f"총 {total} / 완료 {done} / 남음 {total-done}")

    r_px = st.slider("Pointing radius r (px)", 10, 120, 40, step=5)
    disp_w = st.slider("표시 폭 (px)", 400, 1200, 900, step=50)

    st.download_button("CSV 다운로드",
                       st.session_state.df.to_csv(index=False),
                       file_name=f"clicks_{rater_key}.csv")

# ------------------------
# 메인: 호버+클릭(한 화면에서 처리)
# ------------------------
name = current_name()
img_path = name_to_path[name]
img = Image.open(img_path).convert("RGB")
w, h = img.size

st.title(f"OCT Click Collector — {rater}")
st.write(f"현재: **{name}**  ({w}×{h})")

# ① 컴포넌트 호출 (호버 원 미리보기 + 클릭 시 좌표 반환)
ret = hover_click(
    image_b64=pil_to_b64(img),
    width=disp_w,
    radius=r_px,
    fill_rgba="rgba(255,215,0,0.2)",
    stroke_rgba="rgba(255,215,0,1)",
    stroke_px=2,
    key=f"hoverclick_{name}",
)

# ② 좌표 반환 시 → 원본 해상도로 환산 → 즉시 저장 & 다음
if ret and all(k in ret for k in ("x","y","displayed_width","displayed_height")):
    x_disp, y_disp = float(ret["x"]), float(ret["y"])
    dw, dh = float(ret["displayed_width"]), float(ret["displayed_height"])
    scale_x, scale_y = w / dw, h / dh
    x_orig, y_orig = int(round(x_disp * scale_x)), int(round(y_disp * scale_y))

    # 저장
    if name in st.session_state.done_set:
        st.session_state.df.loc[st.session_state.df["name"]==name, ["click_y","click_x"]] = [y_orig, x_orig]
    else:
        st.session_state.df = pd.concat(
            [st.session_state.df, pd.DataFrame([[name, y_orig, x_orig]], columns=["name","click_y","click_x"])],
            ignore_index=True
        )
        st.session_state.done_set.add(name)
    save_df()

    st.toast(f"Saved: {name} → (x={x_orig}, y={y_orig})", icon="✅")
    move_next()
    st.rerun()
