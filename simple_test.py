import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates
from PIL import Image
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import glob
import os

st.title("이미지 호버 & 클릭 테스트")

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
    w, h = img.size
    
    # Tab으로 구분하여 두 가지 방법 제공
    tab1, tab2 = st.tabs(["호버 좌표 (Plotly)", "클릭 좌표 (Image Coordinates)"])
    
    with tab1:
        st.subheader("🖱️ 호버로 실시간 좌표 보기")
        
        # 이미지를 numpy 배열로 변환
        img_array = np.array(img)
        
        # Plotly figure 생성
        fig = go.Figure()
        
        # 이미지 추가
        fig.add_trace(go.Image(z=img_array))
        
        # 호버 정보 설정
        fig.update_layout(
            title="마우스를 이미지 위에 올려보세요!",
            width=min(800, w),
            height=min(600, h),
            xaxis=dict(
                title="X 좌표",
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(255,255,255,0.3)',
                range=[0, w]
            ),
            yaxis=dict(
                title="Y 좌표", 
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(255,255,255,0.3)',
                range=[h, 0]  # Y축 뒤집기 (이미지 좌표계에 맞춤)
            ),
            hovermode='closest'
        )
        
        # Plotly 차트 표시 (호버 이벤트와 함께)
        event = st.plotly_chart(fig, key="hover_chart", on_select="rerun", use_container_width=False)
        
        # 호버/클릭 이벤트 표시
        if event.selection:
            st.write("선택된 지점:", event.selection)
    
    with tab2:
        st.subheader("👆 클릭으로 정확한 좌표 저장")
        
        # 기존 클릭 좌표 받기
        value = streamlit_image_coordinates(img, key="image")
        
        # 클릭 결과 표시
        if value is not None:
            st.write("클릭 좌표:", value)
            if "x" in value and "y" in value:
                st.success(f"클릭된 위치: x={value['x']}, y={value['y']}")
                
                # 클릭한 위치의 RGB 값도 보여주기
                try:
                    x, y = int(value['x']), int(value['y'])
                    if 0 <= x < w and 0 <= y < h:
                        rgb = img_array[y, x]
                        st.info(f"RGB 값: R={rgb[0]}, G={rgb[1]}, B={rgb[2]}")
                except:
                    pass
        else:
            st.info("이미지 위를 클릭해주세요!")
        
else:
    st.error("이미지를 찾을 수 없습니다.")