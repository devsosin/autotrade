import requests

from datetime import datetime
import json

class KISTrade:
    '''
    한국투자증권 API
    '''

    def __init__(self, appkey:str, appsecret:str, account:str, mode:str='s') -> None:
        '''
        account: 주식계좌번호 00000000-00
        mode: real, simulate (r, s)
        '''
        self.appkey = appkey
        self.appsecret = appsecret
        self.account = account

        if mode == 'real' or mode == 'r':
            # 실전
            self.mode = True
            self.domain = 'https://openapi.koreainvestment.com:9443'
        else:
            # 모의
            self.mode = False
            self.domain = 'https://openapivts.koreainvestment.com:29443'
    
    def getConfigs(self):
        return {
            'appkey':self.appkey,
            'appsecret':self.appsecret
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
            URL = self.domain + '/uapi/hashkey'
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

class Domestic:
    '''
    국내주식
    '''

    TRAIDING_ID = {
        'r': { # 실전
            'b': 'TTTC0802U', # 매수
            's': 'TTTC0801U', # 매도
            'c': 'TTTC0803U', # 정정 취소
        },
        's': { # 모의
            'b': 'VTTC0802U', # 매수
            's': 'VTTC0801U', # 매도
            'c': 'VTTC0803U', # 정정 취소
        }
    }

    def __init__(self, kis:KISTrade, auth:KISAuth) -> None:
        self.kis = kis
        self.auth = auth
        self.order_list = []

    def order_stock(self, stock_id:str, quantity:int, order_division:str='01', price:int=0, order_type='b'):
        '''
        주식 주문
        필수값
        stock_id - 종목코드 (6자리)
        order_division - 주문구분 00-지정가, 01-시장가, 05-장전 시간외, 06-장후 시간외, 07-시간외 단일가
        quantity: 수량
        price: 가격 (시장가 외 필수)
        '''

        assert len(stock_id) != 6, '주식 종목코드는 6자리입니다.'
        assert order_division != '01' and price == 0, '시장가가 아닐 경우 price는 필수값입니다.'

        try:
            URL = self.kis.domain + '/uapi/domestic-stock/v1/trading/order-cash'

            body = {
                'CANO': self.kis.account.split('-')[0], # 계좌번호 (앞 8자리)
                'ACNT_PRDT_CD': self.kis.account.split('-')[1], # 계좌번호 (뒤 2자리)
                'PDNO': stock_id, # 종목코드 (6자리)
                'ORD_DVSN': '', # 주문구분
                'ORD_QTY': str(quantity).zfill(2), # 주문수량
                'ORD_UNPR': str(price)# 주문단가
            }

            headers = {
                # 'content-type': 'application/json; charset=utf-8',
                'authorization': self.auth.getToken(),
                'tr_id': self.TRAIDING_ID[self.kis.mode][order_type],
                'hashkey': self.auth.getHashKey(body)
                **self.kis.getConfigs(),
            }

            r = requests.post(URL, headers=headers, data=json.dumps(body))
            res_headers = r.headers
            res_json = r.json()

            # 주문 데이터
            # {
            #     order_number: {
            #         1. body 데이터
            #         2. 처리결과 데이터
            #     }
            # }

            {
                'status':res_json['rd_cd'] == '0',
                'org_number': res_json['output']['KRX_FWDG_ORD_ORGNO'],
                'order_number': res_json['output']['ODNO'],
                'order_date': datetime.strptime(res_json['output']['ORD_TMD'], '%H%M%S')
            }

            return True

        except:
            # error 발생
            print('############### 에러발생 ###############')

            return False
    
    def order_change(self, order_number:str):
        '''
        주문 정정
        '''
        body = {
            # 특정 주문 데이터 (order_number)
            'RVSE_CNCL_DVSN_CD': '01'
        }

        return 

    def order_cancle(self, order_number:str):
        '''
        주문 취소
        '''
        body = {
            # 특정 주문의 데이터 (order_number)
            'RVSE_CNCL_DVSN_CD': '02'
        }
        return 

if __name__ == '__main__':
    configs = {l.split('k=k')[0]:l.split('k=k')[1].rstrip() for l in open('configs', 'r', encoding='utf-8').readlines()}
    kis = KISTrade(configs['APPKey'], configs['APPSecret'], configs['saccount'])

    print(kis.getHashKey())

    print(kis.getToken())

    auth = KISAuth(kis)

    domestic = Domestic(kis, auth)
    print(domestic.order_stock('005630', 1))
