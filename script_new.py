import argparse
import logging
import os
from dotenv import load_dotenv
from uuid import uuid4
import math
import time

from kucoin_universal_sdk.api import DefaultClient
from kucoin_universal_sdk.generate.spot.market import GetPartOrderBookReqBuilder
from kucoin_universal_sdk.model import ClientOptionBuilder
from kucoin_universal_sdk.model import GLOBAL_API_ENDPOINT, GLOBAL_FUTURES_API_ENDPOINT, \
    GLOBAL_BROKER_API_ENDPOINT
from kucoin_universal_sdk.model import TransportOptionBuilder
from kucoin_universal_sdk.generate.spot.market import GetTickerReqBuilder
from kucoin_universal_sdk.generate.spot.order import AddOrderSyncReqBuilder
from kucoin_universal_sdk.generate.spot.order import GetOrderByOrderIdReqBuilder
from kucoin_universal_sdk.generate.spot.order import GetTradeHistoryReqBuilder
from kucoin_universal_sdk.generate.account.transfer import FlexTransferReqBuilder
from kucoin_universal_sdk.generate.account.withdrawal import WithdrawalV3ReqBuilder
from kucoin_universal_sdk.generate.account.withdrawal import GetWithdrawalQuotasReqBuilder
from kucoin_universal_sdk.generate.account.withdrawal import GetWithdrawalHistoryByIdReqBuilder
from kucoin_universal_sdk.generate.account.account import GetSpotAccountDetailReqBuilder
from kucoin_universal_sdk.generate.account.account import GetSpotAccountListReqBuilder

logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

spot_market_api = None
spot_order_api = None
transfer_api = None
withdraw_api = None
account_api = None

def setup_client():
    load_dotenv("./config.env")

    #  Retrieve API secret information from environment variables
    key = os.getenv("KC_API_KEY", "")
    secret = os.getenv("KC_SECRET", "")
    passphrase = os.getenv("KC_PASSPHRASE", "")
    # global safepal_doge_addr

    # Set specific options, others will fall back to default values
    http_transport_option = (
        TransportOptionBuilder()
        .set_keep_alive(True)
        .set_max_pool_size(10)
        .set_max_connection_per_pool(10)
        .build()
    )

    # Create a client using the specified options
    client_option = (
        ClientOptionBuilder()
        .set_key(key)
        .set_secret(secret)
        .set_passphrase(passphrase)
        .set_spot_endpoint(GLOBAL_API_ENDPOINT)
        .set_futures_endpoint(GLOBAL_FUTURES_API_ENDPOINT)
        .set_broker_endpoint(GLOBAL_BROKER_API_ENDPOINT)
        .set_transport_option(http_transport_option)
        .build()
    )
    client = DefaultClient(client_option)
    
    return client
    
    # Get the Restful Service
    # kucoin_rest_service = client.rest_service()

    # spot_market_api = kucoin_rest_service.get_spot_service().get_market_api()
    """
    # Query for part orderbook depth data. (aggregated by price)
    request = GetPartOrderBookReqBuilder().set_symbol("BTC-USDT").set_size("20").build()
    response = spot_market_api.get_part_order_book(request)
    logging.info(f"time={response.time}, sequence={response.sequence}, "
                 f"bids={response.bids}, asks={response.asks}")
    """

def fetch_price(symbol):

    req = (
        GetTickerReqBuilder()
        .set_symbol(symbol)
        .build()
    )
    resp = spot_market_api.get_ticker(req)
    # print(resp)
    last_price = float(resp.price)

    # logging.info(f"{symbol} = {last_price}")
    return last_price

def create_buy_order_sync(symbol, target_amount):
    """
    symbol like USDT-EUR or DOGE-USDT
    target_amount means the name written in front (like DOGE or USDT when trading USDT-EUR)
    """
    req = (
        AddOrderSyncReqBuilder()
        .set_symbol(symbol)
        .set_type('market')
        .set_side('buy')
        .set_size(str(target_amount))
        .build()
    )

    resp = spot_order_api.add_order_sync(req)
    # logging.info(resp)
    
    return resp

def get_withdrawal_quota(token, chain):
    quota_req = (
        GetWithdrawalQuotasReqBuilder()
        .set_chain(chain)
        .set_currency(token.upper())
        .build()
    )
    quota = withdraw_api.get_withdrawal_quotas(quota_req)

    # available = float(quota.available_amount)
    # print("Available:", available)

    return quota

def buy_usdt(usdt_amount):
    try:
        price_euro = fetch_price("USDT-EUR")

        if price_euro > 0.88:
            logging.error(f"Euro Price is above threshold: ${price_euro}! Bot stopped!")
            exit(1)
        else:
            order_resp = create_buy_order_sync("USDT-EUR", usdt_amount)
            if order_resp.status is not None and order_resp.status.value == 'done':
                # if float(order_resp.deal_size) >= 0.99*float(order_resp.origin_size):
                logging.info(f"I bought {order_resp.deal_size} USDT!")
                
            else:
                logging.error("order failed or is not complete yet!")
                logging.info("Stopping...")
                # check again after a few seconds...
                exit(1)
                    
    except Exception as e:
        logging.error("Order rejected:", e)
        logging.info("Stopping...")
        exit(1)

def buy_token(symbol, usdt_amount, max_allowed_price=None):
    try:
        price = fetch_price(symbol)

        if max_allowed_price is not None and price > max_allowed_price:
            logging.error(f"{symbol} Price is above threshold: ${price}! Bot stopped!")
            exit(1)
        else:
            order_resp = create_buy_order_sync(symbol, math.floor(usdt_amount/price))
            # print(order_resp.status)
            if order_resp.status is not None and order_resp.status.value == "done":
                # if float(order_resp.deal_size) >= 0.99*float(order_resp.origin_size):
                logging.info(f"I bought {order_resp.deal_size} {symbol} (${math.ceil(int(order_resp.deal_size)*price)})!")
            else:
                logging.error("order failed or is not complete yet!")
                logging.info("Stopping...")
                # check again after a few seconds...
                exit(1)
                    
    except Exception as e:
        logging.error("Order rejected:", e)
        logging.info("Stopping...")
        exit(1)

def get_spot_account_detail(token=None, account_type=None):
    req = (
        GetSpotAccountListReqBuilder()
        # .set_type()
        .build()
    )

    resp = account_api.get_spot_account_list(req)

    if resp.data is not None:
        if account_type is not None and token is not None:
            return [d for d in resp.data if d.type.value == account_type.lower() and d.currency.lower() == token.lower()]
        elif account_type is not None:
            return [d for d in resp.data if d.type.value == account_type.lower()]
        elif token is not None:
            return [d for d in resp.data if d.currency.lower() == token.lower()]
    else:
        return None


def move_token_between_accounts(token, from_="TRADE", to_="MAIN", amount='MAX') -> int:
    """
    Use this to move tokens between sub-accounts
    """
    token = token.upper()
    from_ = from_.upper()
    to_ = to_.upper()

    token_price = fetch_price(f"USDT-{token}" if token == 'EUR' else f"{token}-USDT")
    if token == 'EUR':
        token_price = 1/token_price

    detail = get_spot_account_detail(token, account_type=from_)
    if detail is None or len(detail) == 0:
        logging.error("There's no such token in Kucoin")
        return -1
    else:
        available_tokens = float(detail[0].available)
        logging.info(f"There are {available_tokens} {token} in your {from_} account which is worth ${math.floor(available_tokens*token_price)}")
    
    if available_tokens == 0:
        logging.error(f"Nothing to move to the {to_} Account!")
        return 0
    
    transfer_req = (
        FlexTransferReqBuilder()
        .set_client_oid(str(uuid4()))
        .set_type("INTERNAL")
        .set_currency(token)
        .set_amount(str(available_tokens) if amount == 'MAX' else str(amount))
        .set_from_account_type(from_)
        .set_to_account_type(to_)
        .build()
    )

    resp = transfer_api.flex_transfer(transfer_req)

    # logging.info(resp)

    detail = get_spot_account_detail(token, account_type=to_)
    available_tokens = float(detail[0].available)
    if available_tokens > 0:
        logging.info(f"There are {available_tokens} {token} in {to_} account which is worth ${math.floor(available_tokens*token_price)}")
        logging.info(f"Transfer {token} to {to_} account done!")
        return 1
    else:
        return -1

def withdraw_token(token, chain, to_address=None, amount='MAX'):
    token = token.upper()
    chain = chain.lower()

    # 1. Get DOGE withdrawal limits
    quota_req = (
        GetWithdrawalQuotasReqBuilder()
        .set_chain(chain)
        .set_currency(token)
        .build()
    )
    quota = withdraw_api.get_withdrawal_quotas(quota_req)

    # logging.info(quota)
    available = float(quota.available_amount)
    fee = float(quota.withdraw_min_fee)

    logging.info(f"Available {token} Tokens: {available}")

    if amount != 'MAX' and float(amount) > available:
        logging.error('Withdrawal amount greater than available! Stopping...')
        exit(1)

    withdraw_req = (
        WithdrawalV3ReqBuilder()
        .set_currency(token)
        .set_to_address(to_address)
        .set_amount(str(available) if amount == 'MAX' else amount)
        .set_withdraw_type("ADDRESS")
        .set_chain(chain)
        .build()
    )

    resp = withdraw_api.withdrawal_v3(withdraw_req)
    logging.info(f"Withdrawal created, id: {resp.withdrawal_id}")
    return resp.withdrawal_id

def check_withdrawal_status(w_id):
    req = (
        GetWithdrawalHistoryByIdReqBuilder()
        .set_withdrawal_id(w_id)
        .build()
    )

    resp = withdraw_api.get_withdrawal_history_by_id(req)
    return resp

def buy_and_transfer_token(token, chain, usdt_amount):
    token = token.upper()
    chain = chain.lower()
    
    try:
        # 1. check withdrawal fee to see if it's worth it
        token_quota = get_withdrawal_quota(token, chain)
        token_withdrawal_fee = round(float(token_quota.withdraw_min_fee)*fetch_price(f'{token}-USDT'), 2)
        logging.info(f"Token withdrawal fee: ${token_withdrawal_fee}")
        # stop if withdrawal > $0.50
        if token_withdrawal_fee > 0.5:
            logging.info("Token withdrawal > $0.50! Stopping...")
            exit(1)
        
        # 2. check if there's enough EUR in main/trade and move from main to trade
        main_eur_detail = get_spot_account_detail(token='EUR', account_type='main')
        available_tokens = float(main_eur_detail[0].available)
        token_price = fetch_price(f"USDT-EUR")
        available_tokens_in_usdt = math.floor(available_tokens/token_price)
        
        logging.info(f"There are {available_tokens} USDT-EUR in your MAIN account which is worth ${available_tokens_in_usdt}")
        
        if available_tokens_in_usdt < usdt_amount + 0.5:
            logging.error(f"There aren't enough USDT-EUR in your MAIN account! Stopping...")
            exit(1)
 
        # 3. move EUR to trade account 
        if move_token_between_accounts('EUR', 'MAIN', 'TRADE', math.ceil(usdt_amount*token_price)) <= 0:
            logging.error("Something went wrong! Stopping ...")
            exit(1)
        
        time.sleep(2)
        
        # 4. buy new usdt regardless of how much we already have
        buy_usdt(usdt_amount)
        time.sleep(2)

        # 5. buy token
        buy_token(f"{token}-USDT", usdt_amount) # get the amount of token bought to use for moving into MAIN account
        time.sleep(2)

        # 6. move token to MAIN account
        if move_token_between_accounts(token) <= 0:
            logging.info("Stopping...")
            exit(1)
        time.sleep(2)
        
        # 7. withdraw token
        safepal_token_addr = os.getenv(f"SAFEPAL_{token}_ADDR", "")
        if safepal_token_addr == "":
            logging.error("safepal token addr not found. Stopping...")
            exit(1)
        w_id = withdraw_token(token=token, chain=chain, to_address=safepal_token_addr, amount = 'MAX')
        if w_id is None:
            logging.error("Withdrawal id is None. Stopping...")
            exit(1)
        while True:
            resp = check_withdrawal_status(w_id)
            if resp.status is not None and resp.status in ('FAILURE', 'SUCCESS'):
                logging.info(f'Withdrawal {resp.status}')
                break
            elif resp.status is None:
                logging.error("No such withdrawal ID. Stopping...")
                exit(1)
            else:
                logging.info(f'Withdrawal {resp.status}')
                time.sleep(30)

    except Exception as e:
        logging.error("Something Failed!", e)
        logging.info("Stopping...")
        exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Buy and transfer a token from KuCoin")
    parser.add_argument("--token", default="XRP", help="Token symbol to buy and withdraw (for example: XRP or DOGE)")
    parser.add_argument("--chain", default=None, help="Withdrawal chain/network for the token (for example: XRP or doge)")
    parser.add_argument("--usdt-amount", type=float, default=20, help="USDT amount to use for the trade")
    args = parser.parse_args()

    client = setup_client()
    # Get the Restful Service
    kucoin_rest_service = client.rest_service()

    spot_market_api = kucoin_rest_service.get_spot_service().get_market_api()
    spot_order_api = kucoin_rest_service.get_spot_service().get_order_api()
    transfer_api = kucoin_rest_service.get_account_service().get_transfer_api()
    withdraw_api = kucoin_rest_service.get_account_service().get_withdrawal_api()
    account_api = kucoin_rest_service.get_account_service().get_account_api()

    chain = args.chain or args.token.lower()
    buy_and_transfer_token(token=args.token, chain=chain, usdt_amount=args.usdt_amount)
