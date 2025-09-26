# save_clicks_streamlit.py
import os, glob, io, base64
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates
import streamlit.components.v1 as components

# ------------------------
# 설정
# ------------------------
IMG_DIR = "test"      # pointgame_project/test (CNV, DME, DRUSEN, NORMAL)
OUT_DIR = "clicks"
os.makedirs(OUT_DIR, exist_ok=True)

# ------------------------
# 유틸: 호버 오버레이(노란 원) 렌더링
# ------------------------
def render_hover_overlay(pil_image, r_px=40, disp_w=None,
                         fill_rgba="rgba(255,215,0,0.2)", stroke_rgba="rgba(255,215,0,1)", stroke_px=2):
    """
    이미지 위에 마우스 호버 위치에 반투명 원을 실시간으로 그려주는 캔버스.
    클릭 이벤트는 처리하지 않음(아래 streamlit_image_coordinates가 담당).
    """
    w, h = pil_image.size
    if disp_w is None:
        disp_w = min(w, 900)
    disp_h = int(h * (disp_w / float(w)))

    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    html = f"""
    <div id="hover-wrap" style="position:relative; display:inline-block;">
      <img id="bg" src="data:image/png;base64,{b64}" style="display:block; width:{disp_w}px; height:auto;"/>
      <canvas id="overlay" style="position:absolute; left:0; top:0; pointer-events:none;"></canvas>
    </div>
    <script>
      const img = document.getElementById("bg");
      const canvas = document.getElementById("overlay");
      const ctx = canvas.getContext("2d");

      function fit() {{
        const rect = img.getBoundingClientRect();
        canvas.width = Math.round(rect.width);
        canvas.height = Math.round(rect.height);
        canvas.style.width = rect.width + "px";
        canvas.style.height = rect.height + "px";
        canvas.style.left = "0px";
        canvas.style.top = "0px";
      }}
      window.addEventListener("resize", fit);
      img.addEventListener("load", fit);
      fit();

      img.addEventListener("mousemove", (e) => {{
        const rect = img.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        ctx.clearRect(0,0,canvas.width,canvas.height);
        ctx.beginPath();
        ctx.arc(x, y, {r_px}, 0, 2*Math.PI);
        ctx.fillStyle = "{fill_rgba}";
        ctx.strokeStyle = "{stroke_rgba}";
        ctx.lineWidth = {stroke_px};
        ctx.fill();
        ctx.stroke();
      }});

      img.addEventListener("mouseleave", () => {{
        ctx.clearRect(0,0,canvas.width,canvas.height);
      }});
    </script>
    """
    components.html(html, height=min(900, disp_h + 10), scrolling=False)
    return disp_w  # 아래 클릭 위젯에도 동일 폭을 주기 위함

# ------------------------
# 평가자 선택 (사이드바)
# ------------------------
DOCTORS = ["Dr. Nam", "Dr. Shin"]

# Streamlit 버전별 쿼리 파라미터 처리
pref = None
qp = getattr(st, "query_params", None)
if isinstance(qp, dict):
    pref = qp.get("user", None)
    if isinstance(pref, list):
        pref = pref[0]
else:
    try:
        qp = st.experimental_get_query_params()
        pref = qp.get("user", [None])[0]
    except Exception:
        pref = None

pref_label = None
if pref:
    p = str(pref).lower()
    if p in ["nam","drnam","doctor1","dr.nam"]:
        pref_label = "Dr. Nam"
    elif p in ["shin","drshin","doctor2","dr.shin"]:
        pref_label = "Dr. Shin"

with st.sidebar:
    st.header("Rater")
    rater = st.selectbox("Choose evaluator", DOCTORS,
                         index=(DOCTORS.index(pref_label) if pref_label in DOCTORS else 0))
    st.caption("선택한 평가자에 따라 별도 CSV로 저장됩니다.")

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
if "df" not in st.session_state:
    if os.path.exists(csv_path):
        st.session_state.df = pd.read_csv(csv_path)
    else:
        st.session_state.df = pd.DataFrame(columns=["name","click_y","click_x"])
if "done_set" not in st.session_state:
    st.session_state.done_set = set(st.session_state.df["name"].astype(str).tolist())
if "idx" not in st.session_state:
    remaining_names = [n for n in names_all if n not in st.session_state.done_set]
    st.session_state.idx = (names_all.index(remaining_names[0]) if remaining_names else 0)

def save_df_to_disk():
    st.session_state.df.to_csv(csv_path, index=False)

def current_name():
    return names_all[st.session_state.idx]

def move_next():
    for j in range(st.session_state.idx + 1, len(names_all)):
        if names_all[j] not in st.session_state.done_set:
            st.session_state.idx = j; return
    st.session_state.idx = min(st.session_state.idx + 1, len(names_all) - 1)

def move_prev():
    for j in range(st.session_state.idx - 1, -1, -1):
        if names_all[j] not in st.session_state.done_set:
            st.session_state.idx = j; return
    st.session_state.idx = max(st.session_state.idx - 1, 0)

def jump_to(k: int):
    k = max(0, min(k, len(names_all) - 1)); st.session_state.idx = k

def record_click(name, y_orig, x_orig, overwrite=True):
    if overwrite and name in st.session_state.done_set:
        st.session_state.df.loc[st.session_state.df["name"] == name, ["click_y", "click_x"]] = [y_orig, x_orig]
    else:
        st.session_state.df = pd.concat(
            [st.session_state.df, pd.DataFrame([[name, y_orig, x_orig]], columns=["name", "click_y", "click_x"])],
            ignore_index=True
        )
        st.session_state.done_set.add(name)
    save_df_to_disk()

# ------------------------
# 사이드바: 진행/툴 + 미리보기 설정
# ------------------------
with st.sidebar:
    st.subheader("Progress / Tools")
    total = len(names_all); done = len(st.session_state.done_set); remaining = total - done
    st.write(f"총 **{total}** / 완료 **{done}** / 남음 **{remaining}**")

    # 원 반지름 (px) & 표시 폭 (px)
    r_px = st.slider("Pointing radius r (px)", 10, 120, 40, step=5,
                     help="원 중심은 클릭 지점, 반지름 r(px)로 미리보기 표시")
    disp_w = st.slider("표시 폭 (px)", 400, 1200, 900, step=50,
                       help="호버 미리보기와 클릭 캡처 이미지를 같은 폭으로 렌더링")

    # 점프/이동
    jump_val = st.slider("Index", 0, total - 1, st.session_state.idx, key="jump_slider")
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
        st.session_state.df = pd.DataFrame(columns=["name","click_y","click_x"])
        st.session_state.done_set = set()
        save_df_to_disk()
        st.session_state.idx = 0
        st.success("CSV를 초기화했습니다."); st.rerun()

    # 진행 다운로드 / 업로드 병합
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
# 메인: 호버 미리보기 + 클릭 저장
# ------------------------
name = current_name()
img_path = name_to_path[name]
img = Image.open(img_path).convert("RGB")
w, h = img.size

st.title(f"OCT Click Collector — {rater}")
st.write(f"현재: **{name}**  ({w}×{h})")

# ① 위: 호버 미리보기(노란 원)
_ = render_hover_overlay(img, r_px=r_px, disp_w=disp_w,
                         fill_rgba="rgba(255,215,0,0.2)",
                         stroke_rgba="rgba(255,215,0,1)", stroke_px=2)

st.caption("위 이미지는 마우스 이동에 따라 반투명 원(r)이 실시간 미리보기로 표시됩니다. 아래 이미지에서 클릭을 저장하세요.")

# ② 아래: 실제 클릭 캡처 (동일 표시 폭으로 정렬)
click = streamlit_image_coordinates(img, key=f"canvas_{name}", width=disp_w)

if click and ("x" in click and "y" in click):
    # 표시 크기 → 원본 좌표 환산
    disp_w_eff = click.get("displayed_width", disp_w)
    disp_h_eff = click.get("displayed_height", int(h * (disp_w / float(w))))
    scale_x = w / float(disp_w_eff)
    scale_y = h / float(disp_h_eff)

    x_disp = float(click["x"]); y_disp = float(click["y"])
    x_orig = int(round(x_disp * scale_x))
    y_orig = int(round(y_disp * scale_y))

    st.info(f"📍 클릭(표시 기준): x={int(x_disp)}, y={int(y_disp)}  →  원본: x={x_orig}, y={y_orig} / r={r_px}px")

    # (선택) 저장 전 정적 프리뷰
    overlay = img.convert("RGBA")
    draw = ImageDraw.Draw(overlay, "RGBA")
    draw.ellipse([x_orig - r_px, y_orig - r_px, x_orig + r_px, y_orig + r_px],
                 outline=(0, 153, 255, 255), width=3, fill=(255, 215, 0, 60))
    st.image(overlay, caption=f"Preview (click fixed): (x={x_orig}, y={y_orig}), r={r_px}px", width=disp_w)

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
    st.write("아래 이미지 위를 클릭하여 좌표를 찍어주세요.")

with st.expander("이미지 목록 / 진행 현황 보기"):
    show_df = pd.DataFrame({"name": names_all, "done": [n in st.session_state.done_set for n in names_all]})
    st.dataframe(show_df)
