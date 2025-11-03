# OCT Click Collector

OCT(Optical Coherence Tomography) 의료 이미지에서 관심 지점의 좌표를 수집하는 웹 기반 annotation 도구입니다.

## 주요 기능

- **이미지 클릭 좌표 수집**: OCT 이미지 위를 클릭하여 정확한 픽셀 좌표 저장
- **시각적 피드백**: 클릭한 지점을 원으로 표시하여 시각적 확인 가능
- **다중 평가자 지원**: Dr. Nam, Dr. Shin 등 여러 평가자가 개별적으로 작업 가능
- **진행 상태 추적**: 완료/미완료 이미지 자동 추적 및 표시
- **모바일 최적화**: 모바일 기기에서도 편리하게 사용 가능한 반응형 UI
- **데이터 내보내기/가져오기**: CSV 형식으로 진행 상황 저장 및 공유

## 시작하기

### 필수 요구사항

- Python 3.11+
- Streamlit 1.29.0

### 설치

```bash
pip install -r requirements.txt
```

### 실행

```bash
streamlit run save_clicks_streamlit.py --server.port 5000 --server.address 0.0.0.0
```

앱이 실행되면 브라우저에서 `http://localhost:5000`로 접속하세요.

## 사용 방법

### 1. 평가자 선택
사이드바에서 평가자를 선택합니다. 각 평가자의 데이터는 별도 CSV 파일로 저장됩니다.

### 2. 이미지 클릭
- 화면에 표시된 OCT 이미지에서 관심 지점을 클릭합니다
- 클릭한 위치에 원이 표시됩니다
- 원의 반지름은 사이드바에서 조정할 수 있습니다 (10-120px)

### 3. 좌표 저장
- **저장 & 다음**: 현재 좌표를 저장하고 다음 이미지로 이동
- **건너뛰기**: 현재 이미지를 건너뛰고 다음으로 이동
- **이전(미완)으로**: 이전 미완료 이미지로 돌아가기

### 4. 진행 관리
- **Undo**: 마지막 저장을 취소
- **Reset CSV**: 모든 진행 상황 초기화
- **Jump**: 특정 이미지 인덱스로 이동
- **CSV 다운로드**: 진행 상황을 CSV 파일로 다운로드
- **CSV 업로드**: 이전 진행 상황을 불러오기

## 데이터 구조

### 입력
이미지는 `test/` 디렉토리 아래 하위 폴더에 저장되어야 합니다:
```
test/
├── CNV/
│   ├── CNV-1016042-1.jpeg
│   └── ...
├── DME/
│   ├── DME-1081406-1.jpeg
│   └── ...
├── DRUSEN/
│   ├── DRUSEN-1083159-1.jpeg
│   └── ...
└── NORMAL/
    └── ...
```

### 출력
클릭 좌표는 `clicks/` 디렉토리에 CSV 파일로 저장됩니다:
```
clicks/
├── clicks_nam.csv
└── clicks_shin.csv
```

CSV 형식:
```csv
name,click_y,click_x
CNV-1016042-1,256,384
DME-1081406-1,128,512
```

## 모바일 사용

이 앱은 모바일 기기에 최적화되어 있습니다:
- 이미지가 화면 크기에 맞게 자동 조정
- 터치 친화적인 큰 버튼
- 반응형 레이아웃

모바일에서 사용 시 세로 모드를 권장합니다.

## URL 파라미터

평가자를 URL 파라미터로 지정할 수 있습니다:
```
http://localhost:5000?user=nam
http://localhost:5000?user=shin
```

지원하는 파라미터 값:
- Dr. Nam: `nam`, `drnam`, `doctor1`, `dr.nam`
- Dr. Shin: `shin`, `drshin`, `doctor2`, `dr.shin`

## 기술 스택

- **Streamlit**: 웹 인터페이스
- **Pillow (PIL)**: 이미지 처리 및 오버레이
- **Pandas**: 데이터 관리
- **streamlit-image-coordinates**: 이미지 클릭 좌표 수집

## 배포

Replit Autoscale 배포로 설정되어 있으며, 포트 5000에서 실행됩니다.

## 라이선스

이 프로젝트는 의료 연구 목적으로 개발되었습니다.
