import logging
import os
from dotenv import load_dotenv
from uuid import uuid4

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

logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def setup_client():
    load_dotenv("./config.env")

    #  Retrieve API secret information from environment variables
    key = os.getenv("KC_API_KEY", "")
    secret = os.getenv("KC_SECRET", "")
    passphrase = os.getenv("KC_PASSPHRASE", "")

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

def fetch_price(spot_market_api, symbol):

    req = (
        GetTickerReqBuilder()
        .set_symbol(symbol)
        .build()
    )
    resp = spot_market_api.get_ticker(req)
    # print(resp)
    last_price = float(resp.price)

    logging.info(f"{symbol} = {last_price}")

def create_buy_order_sync(spot_order_api, symbol, amount):
    req = (
        AddOrderSyncReqBuilder()
        .set_symbol(symbol)
        .set_type('market')
        .set_side('buy')
        .set_size(amount)
        .build()
    )

    resp = spot_order_api.add_order_sync(req)
    logging.info(resp)
    
    return resp

def buy_usdt(spot_market_api):
    try:
        price_euro = fetch_price(spot_market_api, "USDT-EUR")

        if price_euro > 0.86:
            logging.error(f"Euro Price is above threshold: ${price_euro}! Bot stopped!")
            exit(1)
        else:
            order_resp = create_buy_order_sync(spot_order_api, "USDT-EUR", '10')
            if order_resp and order_resp.status == 'done':
                if float(order_resp.deal_size) >= 0.99*float(order_resp.origin_size):
                    logging.info(f"I bought {order_resp.deal_size} USDT!")
                else:
                    logging.error("order is not complete yet!")
                    logging.info("Stopping...")
                    # check again after a few seconds...
                    exit(1)
            else:
                logging.error("order failed or is not complete yet!")
                logging.info("Stopping...")
                # check again after a few seconds...
                exit(1)
                    
    except Exception as e:
        logging.error("Order rejected:", e)
        logging.info("Stopping...")
        exit(1)

def move_token_to_funding(transfer_api, symbol, amount):
    transfer_req = (
        FlexTransferReqBuilder()
        .set_client_oid(str(uuid4()))
        .set_type("INTERNAL")
        .set_currency(symbol)
        .set_amount(amount)
        .set_from_account_type("TRADE")
        .set_to_account_type("MAIN")
        .build()
    )

    resp = transfer_api.flex_transfer(transfer_req)

    logging.info(resp)
    logging.info(f"Transfering {symbol} to funding account done!")

def withdraw_doge(withdraw_api, amount):
    # 1. Get DOGE withdrawal limits
    quota_req = (
        GetWithdrawalQuotasReqBuilder()
        .set_chain('doge')
        .set_currency('DOGE')
        .build()
    )
    quota = withdraw_api.get_withdrawal_quotas(quota_req)

    logging.info(quota)
    available = float(quota.available_amount)
    fee = float(quota.withdraw_min_fee)

    print("Available:", available)
    print("Fee:", fee)

    # withdraw_req = (
    #     WithdrawalV3ReqBuilder()
    #     .set_currency("DOGE")
    #     .set_to_address("Dxxxxxxxxxxxxxxxxxxxxxxxx")
    #     .set_amount(amount)
    #     .set_withdraw_type("ADDRESS")
    #     .set_chain("doge")
    #     .build()
    # )

    # resp = withdraw_api.withdrawal_v3(withdraw_req)

    # print(resp)

if __name__ == "__main__":

    # 1. check withdrawal fee to see if it's worth it
    # 2. buy USDT
    # 3. buy Token
    # 4. move token to funding account
    # 5. withdraw to wallet

    client = setup_client()
    # Get the Restful Service
    kucoin_rest_service = client.rest_service()

    spot_market_api = kucoin_rest_service.get_spot_service().get_market_api()
    spot_order_api = kucoin_rest_service.get_spot_service().get_order_api()
    transfer_api = kucoin_rest_service.get_account_service().get_transfer_api()
    withdraw_api = kucoin_rest_service.get_account_service().get_withdrawal_api()
    
    try:
        # buy_usdt(spot_market_api)
        # buy_token() # get the amount of token bought to use for moving into funding account
        # move_token_to_funding(transfer_api, 'USDT', '10')
        withdraw_doge(withdraw_api, '100')
    
    except Exception as e:
        logging.error("Something Failed!", e)
        logging.info("Stopping...")
        exit(1)
    # req = (
    #     GetTradeHistoryReqBuilder()
    #     .set_symbol('USDT-EUR')
    #     .set_limit(10)
    #     .build()
    # )
    # resp = spot_order_api.get_trade_history(req)
    # print(resp)
