# 필요한 라이브러리 임포트
import streamlit as st # 웹 앱 UI 구축 라이브러리
import FinanceDataReader as fdr # 금융 데이터 로드 라이브러리 (주식, 코인 등)
from datetime import datetime, timedelta # 날짜 및 시간 처리 관련 라이브러리
import mplfinance as mpf # 금융 차트 (특히 캔들 차트) 생성 라이브러리
import matplotlib.pyplot as plt # Matplotlib 기본 라이브러리 (mplfinance와 연동)
import pandas as pd # 데이터 처리 및 분석 라이브러리

# Streamlit 페이지 설정
st.set_page_config(layout="wide") # 페이지 레이아웃을 'wide'로 설정하여 넓게 사용

# 이동 평균선(MAV) 설정
MAV_COLORS_MAP = {
    5: 'red',
    10: 'green',
    20: 'blue',
    30: 'purple',
    60: 'orange',
    120: 'brown'
} # 각 이동 평균 일수별 차트 표시 색상 정의
DEFAULT_MAV_SETTING = [5, 10, 20] # 앱 실행 시 기본으로 선택될 이동 평균선 일수

@st.cache_data # Streamlit 캐싱 데코레이터: 동일한 입력에 대해 데이터를 다시 불러오지 않고 캐시된 데이터를 사용
def load_list(symbol = 'KRX'):
    """
    선택된 거래소(KRX, NASDAQ 등)의 종목 목록을 불러오는 함수
    """
    if symbol in ['KRX', 'KOSPI', 'KOSDAQ', 'KONEX']:
        lis = fdr.StockListing(symbol) # 한국 거래소 종목 목록 불러오기
        lis_selected = lis.loc[:, ['Code', 'Name']]
        lis_indexed = lis_selected.set_index('Name') # 종목명을 인덱스로 설정
    elif symbol in ['NASDAQ', 'NYSE', 'AMEX', 'S&P500']:
        lis = fdr.StockListing(symbol) # 미국 거래소 종목 목록 불러오기
        lis_selected = lis.loc[:, ['Symbol', 'Name']]
        lis_indexed = lis_selected.set_index('Name') # 종목명을 인덱스로 설정
    else:
        # 'CRYPTO' 선택 시 기본 암호화폐 목록 수동 정의
        lis = {'Code': ['BTC/KRW', 'ETH/KRW', 'XRP/KRW', 'BTC/USD', 'ETH/USD', 'XRP/USD']}
        lis_indexed = pd.DataFrame(lis, index = ['비트코인/빗썸', '이더리움/빗썸', '리플/빗썸', '비트코인/Bitfinex', '이더리움/Bitfinex', '리플/Bitfinex'])
        lis_indexed.index.name = 'Name'
    return lis_indexed

@st.cache_data # Streamlit 캐싱 데코레이터
def load_stock(symbol, subsymbol, datestart, dateend):
    """
    선택된 종목의 특정 기간 동안의 일별 주가/시세 데이터를 불러오는 함수
    """
    try:
        df = fdr.DataReader(subsymbol, datestart, dateend) # FinanceDataReader로 데이터 요청
        
        # 불필요한/중복된 컬럼 정리 (데이터프레임 정제)
        if 'Change' in df.columns:
            df = df.drop(columns='Change')
            
        if 'Adj Close' in df.columns:
             df = df.drop(columns='Adj Close')
        
        if 'Volume_USDT' in df.columns:
            df = df.rename(columns={'Volume_USDT': 'Volume'}) # 볼륨 컬럼명 통일
        
        return df
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}. 코드를 확인해 주세요: {subsymbol}")
        return pd.DataFrame() # 오류 발생 시 빈 데이터프레임 반환


# --- Streamlit 사이드바 UI 구성 ---
with st.sidebar:
    st.title('종목 및 차트 설정 ⚙️')
    
    # 거래소 선택 Selectbox
    symbol = st.selectbox('거래소 선택', ['KRX','KOSPI', 'KOSDAQ', 'KONEX', 'NASDAQ', 'NYSE', 'AMEX', 'CRYPTO'])
    lis = load_list(symbol) # 선택된 거래소에 따라 종목 목록 로드
    
    if lis.empty:
        st.error("종목 목록을 불러올 수 없습니다.")
        st.stop() # 목록 로드 실패 시 앱 실행 중지

    name_list = lis.index.tolist()
    st.markdown('---')
    
    # 종목 선택 Selectbox
    name = st.selectbox('종목 선택', name_list)
    
    # 선택된 종목의 코드 추출
    row = lis.loc[name]
    sub_symbol = row.iloc[0] if isinstance(row, pd.Series) else row['Code'].iloc[0] 
    st.markdown('---')
    
    st.markdown('**기간 선택**')
    # 날짜 입력 위젯 (기본값: 오늘로부터 90일 전 ~ 오늘)
    datestart = st.date_input('시작 날자', value = datetime.today()-timedelta(days=90))
    dateend = st.date_input('종료 날자')                                             
    st.markdown('---')
    
    st.markdown('**차트 옵션**')
    # 체크박스 위젯 (거래량, 볼린저 밴드 표시 여부)
    show_volume = st.checkbox('거래량 표시', value=True)
    show_bollinger_bands = st.checkbox('볼린저 밴드 표시', value=True)

# --- 메인 영역 데이터 처리 및 차트 준비 ---

# 선택된 설정으로 주가 데이터 불러오기
df = load_stock(symbol, sub_symbol, datestart, dateend)

# 데이터 유효성 검사
if df.empty or len(df) < 5:
    st.error("선택된 기간에 충분한 데이터가 없습니다. 기간을 다시 선택해 주세요.")
    st.stop() # 데이터 부족 시 실행 중지
    
# 인덱스 이름이 'Date'인지 확인 및 설정
if df.index.name != 'Date':
    df.index.name = 'Date'

st.header("주식/가상화폐 데이터 및 캔들 차트 시각화")

# 이동 평균선 선택을 위한 컬럼 분할
mav_col1, mav_col2 = st.columns([1, 4])

with mav_col1:
    # 멀티셀렉트 위젯으로 원하는 MAV 일수 선택
    selected_mavs = st.multiselect(
        "**이동 평균선(MAV) 선택 (일):**",
        options=sorted(MAV_COLORS_MAP.keys()),
        default=DEFAULT_MAV_SETTING
    )
    sorted_mav_settings = sorted(selected_mavs) # 선택된 MAV 일수를 정렬
    mav_colors = [MAV_COLORS_MAP[m] for m in sorted_mav_settings] # 정렬된 일수에 맞는 색상 지정


chart_style = 'default' # mplfinance 기본 스타일
marketcolors = mpf.make_marketcolors(up='red', down='blue') # 양봉/음봉 색상 설정 (빨강/파랑)
mpf_style = mpf.make_mpf_style(base_mpf_style=chart_style, marketcolors=marketcolors) # 최종 차트 스타일 정의

with mav_col2:
    st.markdown('**🌈 선택된 이동 평균선 정보**')
    if sorted_mav_settings:
        # 선택된 MAV 정보 및 색상을 HTML로 표시
        mav_info_html = ""
        for day, color in zip(sorted_mav_settings, mav_colors):
            mav_info_html += f'<span style="color: {color}; font-weight: bold;">{day}일 MAV</span> &nbsp; '
        st.markdown(mav_info_html, unsafe_allow_html=True)
    else:
        st.info("선택된 이동평균선이 없습니다.")

# 볼린저 밴드 계산
window = 20
df['MB'] = df['Close'].rolling(window=window).mean() # 중간 밴드 (20일 이동평균)
df['STD'] = df['Close'].rolling(window=window).std() # 표준편차
df['Upper'] = df['MB'] + 2 * df['STD'] # 상단 밴드 (중간밴드 + 2*표준편차)
df['Lower'] = df['MB'] - 2 * df['STD'] # 하단 밴드 (중간밴드 - 2*표준편차)

addplots = []
if show_bollinger_bands:
    # 볼린저 밴드를 추가 플롯 리스트에 추가
    addplots.extend([
        mpf.make_addplot(df['Upper'], color='blue', linestyle='--'),
        mpf.make_addplot(df['MB'], color='orange', linestyle='--'),
        mpf.make_addplot(df['Lower'], color='blue', linestyle='--')
    ])


st.subheader(f"🕯️ {name} ({sub_symbol}) 캔들 차트")

# mplfinance를 사용하여 최종 차트 생성 및 렌더링
fig, ax = mpf.plot(
    data=df,                                 # 사용할 데이터프레임
    volume=show_volume,                      # 거래량 표시 여부 (체크박스 설정 따름)
    type='candle',                           # 차트 유형: 캔들 차트
    style=mpf_style,                         # 위에서 정의한 스타일 적용
    figsize=(12,6),                          # 차트 사이즈
    addplot=addplots,                        # 볼린저 밴드 등 추가 플롯 설정
    fontscale=1.1,                           # 폰트 크기 배율을 설정합니다.
    mav=tuple(sorted_mav_settings),          # 선택된 이동 평균선 설정 적용
    mavcolors=mav_colors,                    # 이동 평균선 색상 적용
    returnfig=True                           # Figure 객체를 반환받아 Streamlit에 표시
)

# 생성된 Matplotlib Figure 객체를 Streamlit 앱에 표시
st.pyplot(fig, use_container_width=True)

st.markdown('---')