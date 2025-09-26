import os
import streamlit as st
import streamlit.components.v1 as components

# 프런트엔드(정적 html) 폴더 경로
_frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")

# 컴포넌트 선언
_hover_click = components.declare_component(
    "hover_click",
    path=_frontend_dir,  # 빌드 없이 정적 파일에서 바로 로드
)

def hover_click(
    image_b64: str,
    width: int = None,
    radius: int = 40,
    fill_rgba: str = "rgba(255,215,0,0.2)",
    stroke_rgba: str = "rgba(255,215,0,1)",
    stroke_px: int = 2,
    key: str = None,
):
    """
    호버 시 반투명 원, 클릭 시 좌표 반환.
    Returns: dict | None = {"x": int, "y": int, "displayed_width": int, "displayed_height": int}
    """
    return _hover_click(
        image_b64=image_b64,
        width=width,
        radius=radius,
        fill_rgba=fill_rgba,
        stroke_rgba=stroke_rgba,
        stroke_px=stroke_px,
        key=key,
        default=None,
    )