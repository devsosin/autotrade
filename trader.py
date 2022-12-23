import os
import json
import requests

from datetime import datetime, time as dt_time

import pandas as pd

class KISTrade:
    '''
    한국투자증권 API
    '''

    def __init__(self, appkey:str, appsecret:str, account:str, mode:str='s') -> None:
        '''
        account: 주식계좌번호 00000000-00
        mode: real(r), simulate(s)
        '''
        self.appkey = appkey
        self.appsecret = appsecret
        self.account = account

        if mode == 'real' or mode == 'r':
            # 실전
            self.mode = 'r'
            self.domain = 'https://openapi.koreainvestment.com:9443'
        else:
            # 모의
            self.mode = 's'
            self.domain = 'https://openapivts.koreainvestment.com:29443'
    
    def getConfigs(self):
        return {
            'appkey':self.appkey,
            'appsecret':self.appsecret
        }
    
    def getAccount(self):
        return {
            'CANO': self.account.split('-')[0], # 계좌번호 (앞 8자리)
            'ACNT_PRDT_CD': self.account.split('-')[1], # 계좌번호 (뒤 2자리)
        }

class KISAuth:
    '''
    인증관리
    '''

    def __init__(self, kis:KISTrade) -> None:
        self.kis = kis
        self.access_token = ''
        
    def getToken(self) -> str:
        try:
            if self.access_token and datetime.now() < self.token_expired_in:
                return self.access_token

            URL = self.kis.domain + '/oauth2/tokenP'
            data = {
                'grant_type': 'client_credentials',
                **self.kis.getConfigs(),
            }
            res_json = requests.post(URL, data=json.dumps(data)).json()

            self.access_token = 'Bearer ' + res_json['access_token']
            self.token_expired_in = datetime.strptime(res_json['access_token_token_expired'], '%Y-%m-%d %H:%M:%S')

            return self.access_token

        except:
            # error 발생
            print('############### 에러발생 ###############')
            print(res_json)
            return ''

    def getHashKey(self, body:dict) -> str:
        try:
            URL = self.kis.domain + '/uapi/hashkey'
            headers = {
                # 'content-type':'application/json; charset=utf-8',
                **self.kis.getConfigs(),
            }
            res_json = requests.post(URL, headers=headers, data=json.dumps(body)).json()
            self.hash = res_json['HASH']

            return self.hash
        except:
            # error 발생
            print('############### 에러발생 ###############')
            print(res_json)
            return ''

class StockInfo:
    '''
    주식 종목코드 관리
    '''

    def __init__(self) -> None:
        pass

    def kospi(self) -> pd.DataFrame:
        '''
        코스피 주식정보
        '''
        if os.path.exists('./kospi_code.xlsx'):
            return pd.read_excel('./kospi_code.xlsx')
        
        from stocks_info import kis_kospi_code_mst
        kis_kospi_code_mst.kospi_master_download()
        df = kis_kospi_code_mst.get_kospi_master_dataframe()
        df.to_excel('kospi_code.xlsx',index=False)
        return df

    def kosdaq(self) -> pd.DataFrame:
        '''
        코스닥 주식정보
        '''
        if os.path.exists('./kosdaq_code.xlsx'):
            return pd.read_excel('./kosdaq_code.xlsx')

        from stocks_info import kis_kosdaq_code_mst
        kis_kosdaq_code_mst.kosdaq_master_download()
        df = kis_kosdaq_code_mst.get_kosdaq_master_dataframe()
        df.to_excel('kosdaq_code.xlsx',index=False)
        return df

class Domestic:
    '''
    국내주식
    '''

    TRAIDING_ID = {
        'r': { # 실전
            'b': 'TTTC0802U', # 매수
            's': 'TTTC0801U', # 매도
            'c': 'TTTC0803U', # 정정 취소
            'a': 'TTTC8434R', # 주식 잔고 조회
            'able': 'TTTC8908R', # 매수 가능 조회
        },
        's': { # 모의
            'b': 'VTTC0802U', # 매수
            's': 'VTTC0801U', # 매도
            'c': 'VTTC0803U', # 정정 취소
            'a': 'VTTC8434R', # 주식 잔고 조회
            'able': 'VTTC8908R', # 매수 가능 조회
        }
    }

    def __init__(self, kis:KISTrade, auth:KISAuth) -> None:
        self.kis = kis
        self.auth = auth
        # 정정취소가능 주문 조회, 상태 관리
        self.order_list = []

    def order_stock(self, stock_id:str, quantity:int, order_division:str='01', price:int=0, order_type='b'):
        '''
        주식 주문
        # 필수값
            stock_id - 종목코드 (6자리)
            quantity: 수량

        # 선택값
            order_division - 주문구분 00-지정가, 01-시장가, 05-장전 시간외, 06-장후 시간외, 07-시간외 단일가
            price: 가격 (시장가 외 필수)
            order_type: buy(b), sell(s)
        '''

        assert len(stock_id) == 6, '주식 종목코드는 6자리입니다.'
        if order_division != '01':
            assert price != 0, '시장가가 아닐 경우 price는 필수값입니다.'

        try:
            URL = self.kis.domain + '/uapi/domestic-stock/v1/trading/order-cash'

            body = {
                **self.kis.getAccount(),
                'PDNO': stock_id, # 종목코드 (6자리)
                'ORD_DVSN': order_division, # 주문구분
                'ORD_QTY': str(quantity).zfill(2), # 주문수량
                'ORD_UNPR': str(price)# 주문단가
            }

            headers = {
                # 'content-type': 'application/json; charset=utf-8',
                'authorization': self.auth.getToken(),
                'tr_id': self.TRAIDING_ID[self.kis.mode][order_type],
                'hashkey': self.auth.getHashKey(body),
                **self.kis.getConfigs(),
            }

            r = requests.post(URL, headers=headers, data=json.dumps(body))
            
            res_json = r.json()
            # print(res_json)
            if not res_json['rt_cd'] == '0':
                print(res_json['msg_cd'])
                print(res_json['msg1'])
                return False

            order_receipt = {
                'status':res_json['rt_cd'] == '0',
                'org_number': res_json['output']['KRX_FWDG_ORD_ORGNO'],
                'order_number': res_json['output']['ODNO'],
                'order_date': datetime.strptime(res_json['output']['ORD_TMD'], '%H%M%S'),
                **body
            }

            return order_receipt

        except:
            # error 발생
            print('############### 에러발생 ###############')
            import traceback
            traceback.print_exc()

            return False
        
    def order_changable(self):
        '''
        정정취소가능 주문 조회 (모의투자 미지원)
        '''
        assert self.kis.mode == 'r', '정정취소가능 주문 조회는 실전투자만 지원합니다.'

        try:
            URL = self.kis.domain + '/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl'
            

            headers = {
                'authorization': self.auth.getToken(),
                'tr_id': 'TTTC8036R',
                **self.kis.getConfigs(),
            }
            params = {
                **self.kis.getAccount(),
                'CTX_AREA_FK100': '',
                'CTX_AREA_NK100': '',
                'INQR_DVSN_1': '0',
                'INQR_DVSN_2': '0',
            }

            r = requests.get(URL, params=params, headers=headers)

            res_json = r.json()

            if not res_json['rt_cd'] == '0':
                print(res_json['msg_cd'])
                print(res_json['msg1'])
                return []

            has_next = 'ctx_area_fk100' in res_json

            result = [{
                'org_id': l['ord_gno_brno'],
                'order_id': l['odno'],
                'original_id': l['orgn_odno'],
                'order_name': l['ord_dvsn_name'],
                'stock_id': l['pdno'],
                'stock_name': l['prdt_name'],
                'quantity': l['ord_qty'],
                'price': l['ord_unpr'],
                'order_date': l['ord_tmd'],
                'change_quantity': l['psbl_qty'],
                'buy_or_sell': l['sll_buy_dvsn_cd'] == '02', # buy, sell
            } for l in res_json['output']]
            
            return result

        except:
            # error 발생
            print('############### 에러발생 ###############')
            import traceback
            traceback.print_exc()

            return []
    
    def order_change(self, org_id: str, order_id: str):
        '''
        주문 정정

        org_id - 한국투자증권 시스템에서 지정된 영업점코드
        order_id - 한국투자증권 시스템에서 채번된 주문번호
        '''
        try:
            URL = self.kis.domain + '/uapi/domestic-stock/v1/trading/order-rvsecncl'
            body = {
                **self.kis.getAccount(),
                'KRX_FWDG_ORD_ORGNO': org_id,
                'ORGN_ODNO': order_id,
                'RVSE_CNCL_DVSN_CD': '01',

                'ORD_DVSN': '',
                'ORD_QTY': '',
                'ORD_UNPR': '',
                'QTY_ALL_ORD_YN': '', # Y, N

            }
            headers = {
                'authorization': self.auth.getToken(),
                'tr_id': self.TRAIDING_ID[self.kis.mode]['c'],
                'hashkey': self.auth.getHashKey(body),
                **self.kis.getConfigs(),
            }


            return

        except:
            # error 발생
            print('############### 에러발생 ###############')
            return False

    def order_cancle(self, org_id: str, order_id: str):
        '''
        주문 취소

        org_id - 한국투자증권 시스템에서 지정된 영업점코드
        order_id - 한국투자증권 시스템에서 채번된 주문번호
        '''
        try:
            URL = self.kis.domain + '/uapi/domestic-stock/v1/trading/order-rvsecncl'
            body = {
                **self.kis.getAccount(),
                'KRX_FWDG_ORD_ORGNO': org_id,
                'ORGN_ODNO': order_id,
                'RVSE_CNCL_DVSN_CD': '02',

                'ORD_QTY': '',
                'QTY_ALL_ORD_YN': '', # Y, N
            }
            headers = {
                    'authorization': self.auth.getToken(),
                    'tr_id': self.TRAIDING_ID[self.kis.mode]['c'],
                    'hashkey': self.auth.getHashKey(body),
                    **self.kis.getConfigs(),
            }
            
            return
            
        except:
            # error 발생
            print('############### 에러발생 ###############')
            return False
    
    def order_asset(self):
        '''
        주식잔고조회
        '''
        try:
            URL = self.kis.domain + '/uapi/domestic-stock/v1/trading/inquire-balance'
            params = {
                **self.kis.getAccount(),
                'AFHR_FLPR_YN': 'N',
                'OFL_YN': '',
                'INQR_DVSN': '02', # 종목별 조회
                'UNPR_DVSN': '01',
                'FUND_STTL_ICLD_YN': 'N',
                'FNCG_AMT_AUTO_RDPT_YN': 'N',
                'PRCS_DVSN': '00',
                'CTX_AREA_FK100': '',
                'CTX_AREA_NK100': ''
            }
            headers = {
                **self.kis.getConfigs(),
                'authorization': self.auth.getToken(),
                'tr_id': self.TRAIDING_ID[self.kis.mode]['a'],
            }
            r = requests.get(URL, params=params, headers=headers, )
            res_json = r.json()
            if not res_json['rt_cd'] == '0':
                print(res_json['msg_cd'])
                print(res_json['msg1'])
                return []
            
            has_next = 'ctx_area_fk100' in res_json

            result = [{
                'stock_number': l['pdno'],
                'stock_name': l['prdt_name'],
                'holding_quantity': l['hldg_qty'],
                'avg_price': l['pchs_avg_pric'],
                'purchase_amount': l['pchs_amt'],
                'eval_amount': l['evlu_amt']
            } for l in res_json['output1']]
            
            if has_next:
                print('이어서 조회')
            
            return result
            
        except:
            # error 발생
            print('############### 에러발생 ###############')
            import traceback
            traceback.print_exc()

            return []
    
    def order_able(self, stock_id: str, target_price: int):
        '''
        매수가능조회
        '''
        try:
            URL = self.kis.domain + '/uapi/domestic-stock/v1/trading/inquire-psbl-order'
            params = {
                **self.kis.getAccount(),
                'PDNO': stock_id,
                'ORD_UNPR': str(target_price),
                'ORD_DVSN': '00',
                'CMA_EVLU_AMT_ICLD_YN': 'N',
                'OVRS_ICLD_YN': 'N',
            }
            headers = {
                **self.kis.getConfigs(),
                'authorization': self.auth.getToken(),
                'tr_id': self.TRAIDING_ID[self.kis.mode]['able'],
            }

            r = requests.get(URL, params=params, headers=headers)
            res_json = r.json()

            if not res_json['rt_cd'] == '0':
                print(res_json['msg_cd'])
                print(res_json['msg1'])
                return False

            result = {
                'max_amount': res_json['output']['max_buy_amt'],
                'max_quantity': res_json['output']['max_buy_qty'],
            }

            return result

        except:
            # error 발생
            print('############### 에러발생 ###############')
            import traceback
            traceback.print_exc()

            return False

marketTime = {
    'open'  : { 'hour': 8, 'minute':30 },
    'close' : { 'hour':15, 'minute':30 }
}

def marketOpen():
    timenow = datetime.now().time()
    if dt_time(**marketTime['open']) <= timenow <= dt_time(**marketTime['close']):
        return True
    return False

import time

def my_print(*msg):
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), *msg)

if __name__ == '__main__':
    
    my_print('한국투자증권 계정 확인')
    configs = {l.split('k=k')[0]:l.split('k=k')[1].rstrip() for l in open('configs', 'r', encoding='utf-8').readlines()}
    kis = KISTrade(configs['APPKey'], configs['APPSecret'], configs['saccount'])
    
    my_print('주식정보 설정')
    # 사용할 수 있는 종목, 사용할 칼럼만 남기기 -> 데이터 확인 필요
    stock_info = StockInfo()
    kospi = stock_info.kospi()
    # if type(kospi) == pd.DataFrame:
    #     print(kospi.head(1))
    
    kosdaq = stock_info.kosdaq()
    # if type(kosdaq) == pd.DataFrame:
    #     print(kosdaq.head(1))
    
    my_print('인증정보 생성')
    auth = KISAuth(kis)
    domestic = Domestic(kis, auth)

    from collections import deque
    signals = deque([])
    # signal_type -> time, price, 
    check_point = True
    asset_check = True

    while True:
        try:
            # 주식장 오픈 체크
            is_open = marketOpen()

            # 장이 열려있는 시간일 경우
            if is_open:

                #################### 매수 매도 Signal 체크
                # Signal 체크 (구매 조건 - 로직 들어가는 부분)

                # # 매수 1회
                # if check_point:
                #     my_print(domestic.order_stock('005930', 1))
                #     check_point=False

                # # 10분마다 잔고조회 (1회만)
                # if datetime.now().minute%10 == 0:
                #     if asset_check:
                #         my_print(domestic.order_asset())
                #         asset_check = False
                # else:
                #     asset_check = True

                my_print(domestic.order_able('005930', 58200))

                # 실전만 제공
                # my_print(domestic.order_changable())

                # # 매도 - 시그널이 왔을 때 처리 방법, 주식잔고에 있어야함
                # if check_point:
                #     my_print(domestic.order_stock('005930', 1, order_type='s'))
                #     check_point=False

                #################### 주문 체크

        except:
            import traceback
            my_print('########## 에러 발생 ##########')
            traceback.print_exc()

        time.sleep(0.5)
