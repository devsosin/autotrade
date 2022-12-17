import requests

from datetime import datetime
import json

class KISTrade:
    '''
    한국투자증권 API
    '''

    def __init__(self, appkey:str, appsecret:str, account:str, mode:str='s') -> None:
        '''
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

    def __init__(self, kis:KISTrade):
        self.kis = kis
        self.access_token = None
        
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

    def getHashKey(self, **body):
        try:
            URL = self.domain + '/uapi/hashkey'
            headers = {
                # 'content-type':'application/json; charset=utf-8',
                **self.kis.getConfigs(),
            }
            body = {
                **body,
                "CANO": self.kis.account,
            }
            # 정보확인
            # body = {
            #     "ORD_PRCS_DVSN_CD": "02",
            #     "CANO": self.kis.account,
            #     # "ACNT_PRDT_CD": "03",
            #     # "SLL_BUY_DVSN_CD": "02",
            #     # "SHTN_PDNO": "101S06",
            #     # "ORD_QTY": "1",
            #     # "UNIT_PRICE": "370",
            #     # "NMPR_TYPE_CD": "",
            #     # "KRX_NMPR_CNDT_CD": "",
            #     # "CTAC_TLNO": "",
            #     # "FUOP_ITEM_DVSN_CD": "",
            #     # "ORD_DVSN_CD": "02"
            # }

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
    국내주식 주문
    '''

    TRAIDING_ID = {
        'r': {
            'b': 'TTTC0802U',
            's': 'TTTC0801U'
        },
        's': {
            'b': 'VTTC0802U',
            's': 'VTTC0801U'
        }
    }

    def __init__(self, kis:KISTrade, auth:KISAuth) -> None:
        self.kis = kis
        self.auth = auth

    def stock_order(self, order_type='b'):
        '''
        주식 주문
        '''

        try:
            URL = self.kis.domain + '/uapi/domestic-stock/v1/trading/order-cash'
            headers = {
                # 'content-type': 'application/json; charset=utf-8',
                'authorization': self.auth.getToken(),
                **self.kis.getConfigs(),
                'tr_id': self.TRAIDING_ID[self.kis.mode][order_type],
            }

            requests.post(URL, headers=headers, )

            pass
        except:
            # error 발생
            print('############### 에러발생 ###############')

            return

if __name__ == '__main__':
    configs = {l.split('k=k')[0]:l.split('k=k')[1].rstrip() for l in open('configs', 'r', encoding='utf-8').readlines()}
    kis = KISTrade(configs['APPKey'], configs['APPSecret'], configs['saccount'])

    print(kis.getHashKey())

    print(kis.getToken())

