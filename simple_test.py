import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates
from PIL import Image
import glob
import os

st.title("간단한 이미지 클릭 테스트")

# 이미지 목록 가져오기
IMG_DIR = "test"
imgs = sorted(glob.glob(os.path.join(IMG_DIR, "*/*.*")))

if imgs:
    # 첫 번째 이미지 선택
    img_path = imgs[0]
    img_name = os.path.basename(img_path)
    
    st.write(f"테스트 이미지: {img_name}")
    
    # 이미지 로드
    img = Image.open(img_path).convert("RGB")
    
    # 이미지 클릭 좌표 받기
    value = streamlit_image_coordinates(img, key="image")
    
    # 클릭 결과 표시
    if value is not None:
        st.write("클릭 좌표:", value)
        if "x" in value and "y" in value:
            st.success(f"클릭된 위치: x={value['x']}, y={value['y']}")
    else:
        st.info("이미지 위를 클릭해주세요!")
        
else:
    st.error("이미지를 찾을 수 없습니다.")