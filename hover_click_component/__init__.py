import os
import streamlit.components.v1 as components

# frontend/index.html 경로
_frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")

# 컴포넌트 선언
_hover_click = components.declare_component(
    "hover_click",
    path=_frontend_dir,
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
    OCT 이미지를 base64로 넣으면, 브라우저에서 호버 미리보기 + 클릭 좌표를 반환합니다.
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
