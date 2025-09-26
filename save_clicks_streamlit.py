import os, glob
import streamlit as st
import pandas as pd
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates

# ------------------------
# 설정
# ------------------------
IMG_DIR = "test"      # pointgame_project/test (CNV, DME, DRUSEN, NORMAL 하위 폴더)
OUT_DIR = "clicks"
os.makedirs(OUT_DIR, exist_ok=True)

# ------------------------
# 평가자 선택 (사이드바)
# ------------------------
DOCTORS = ["Dr. Nam", "Dr. Shin"]
# (선택사항) URL 쿼리의 user 값을 기본값으로 사용
qp = st.query_params
pref = qp.get("user", [None])[0]
pref_label = None
if pref:
    # 간단한 매핑 (doctor1 -> Dr. Nam 등 원하는 규칙 추가 가능)
    if pref.lower() in ["nam","drnam","doctor1","dr.nam"]:
        pref_label = "Dr. Nam"
    elif pref.lower() in ["shin","drshin","doctor2","dr.shin"]:
        pref_label = "Dr. Shin"

with st.sidebar:
    st.header("Rater")
    rater = st.selectbox("Choose evaluator", DOCTORS, index=(DOCTORS.index(pref_label) if pref_label in DOCTORS else 0))
    st.caption("선택한 평가자에 따라 별도 CSV로 저장됩니다.")

# 파일명용 키
rater_key = "nam" if rater == "Dr. Nam" else "shin"
csv_path = os.path.join(OUT_DIR, f"clicks_{rater_key}.csv")

# ------------------------
# 이미지 목록 준비
# ------------------------
imgs = sorted(glob.glob(os.path.join(IMG_DIR, "*/*.*")))
if not imgs:
    st.error(f"No images found in {IMG_DIR}. Check working directory and folder structure.")
    st.stop()

# 기존 기록 불러오기(이어하기 지원)
if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)
    done = set(df["name"].astype(str).tolist())
else:
    df = pd.DataFrame(columns=["name","click_y","click_x"])
    done = set()

# 남은 이미지
remaining = [p for p in imgs if os.path.splitext(os.path.basename(p))[0] not in done]

st.title(f"OCT Click Collector — {rater}")
st.write(f"총 **{len(imgs)}**장 중 **{len(done)}**장 완료, **{len(remaining)}**장 남음")

if remaining:
    current = remaining[0]
    name = os.path.splitext(os.path.basename(current))[0]

    # 이미지 로드 (원본 크기)
    img = Image.open(current).convert("RGB")
    w, h = img.size

    st.subheader(f"{name}  ({w}×{h})")

    # 이미지 위 클릭 → 좌표 얻기 (렌더링 크기와 무관하게 원본 좌표로 환산)
    click = streamlit_image_coordinates(img, key="canvas_click", width=None)

    if click and ("x" in click and "y" in click):
        disp_w = click.get("displayed_width", w)
        disp_h = click.get("displayed_height", h)
        scale_x = w / float(disp_w)
        scale_y = h / float(disp_h)

        x_disp = float(click["x"])
        y_disp = float(click["y"])
        x_orig = int(round(x_disp * scale_x))
        y_orig = int(round(y_disp * scale_y))

        st.info(f"📍 클릭(표시 기준): x={int(x_disp)}, y={int(y_disp)}  →  원본: x={x_orig}, y={y_orig}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("저장 & 다음", type="primary"):
                new_row = pd.DataFrame([[name, y_orig, x_orig]], columns=["name","click_y","click_x"])
                df = pd.concat([df, new_row], ignore_index=True)
                df.to_csv(csv_path, index=False)
                st.rerun()
        with col2:
            if st.button("건너뛰기"):
                st.rerun()
    else:
        st.write("이미지 위를 클릭하여 좌표를 찍어주세요.")
else:
    st.success("✅ 모든 이미지 클릭 완료!")
    st.dataframe(df)
    st.download_button(f"CSV 다운로드 ({rater})", df.to_csv(index=False), file_name=f"clicks_{rater_key}.csv")
