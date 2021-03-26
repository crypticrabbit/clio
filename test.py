#!/usr/bin/python3

import websockets
import asyncio
import json
import io
import os
import subprocess
import argparse
import time
import threading

def checkAccountInfo(aldous, p2p):
    return isSubset(aldous["object"], p2p["result"]["account_data"])

def isSubset(sub, sup):
    for x in sub:
        if x == "deserialization_time_microsecond":
            continue
        if not x in sup:
            return False
        elif not sub[x] == sup[x]:
            return False
    return True


def compareAccountInfo(aldous, p2p):
    p2p = p2p["result"]["account_data"]
    aldous = aldous["object"]
    if isSubset(p2p,aldous):
        print("Responses match!!")
    else:
        print("Response mismatch")
        print(aldous)
        print(p2p)
def compareTx(aldous, p2p):
    p2p = p2p["result"]
    if aldous["transaction"] != p2p["tx"]:
        print("transaction mismatch")
        print(aldous["transaction"])
        print(p2p["tx"])
        return False
    if aldous["metadata"] != p2p["meta"] and not isinstance(p2p["meta"],dict):
        print("metadata mismatch")
        print("aldous : " + aldous["metadata"])
        print("p2p : " + str(p2p["meta"]))
        return False
    if aldous["ledger_sequence"] != p2p["ledger_index"]:
        print("ledger sequence mismatch")
        print(aldous["ledger_sequence"])
        print(p2p["ledger_index"])
    print("responses match!!")
    return True
    
def compareAccountTx(aldous, p2p):
    print(p2p)
    if "result" in p2p:
        p2p = p2p["result"]
    maxLedger = getMinAndMax(aldous)[1]
    minLedger = getMinAndMax(p2p)[0]
    p2pTxns = []
    p2pMetas = []
    p2pLedgerSequences = []
    for x in p2p["transactions"]:
        p2pTxns.append(x["tx_blob"])
        p2pMetas.append(x["meta"])
        p2pLedgerSequences.append(x["ledger_index"])
    aldousTxns = []
    aldousMetas = []
    aldousLedgerSequences = []
    for x in aldous["transactions"]:
        aldousTxns.append(x["transaction"])
        aldousMetas.append(x["metadata"])
        aldousLedgerSequences.append(x["ledger_sequence"])

    p2pTxns.sort()
    p2pMetas.sort()
    p2pLedgerSequences.sort()
    aldousTxns.sort()
    aldousMetas.sort()
    aldousLedgerSequences.sort()
    if p2pTxns == aldousTxns and p2pMetas == aldousMetas and p2pLedgerSequences == aldousLedgerSequences:
        print("Responses match!!!")
        print(len(aldousTxns))
        print(len(p2pTxns))
    else:
        print("Mismatch responses")
        print(len(aldousTxns))
        print(len(aldous["transactions"]))
        print(len(p2pTxns))
        print(len(p2p["transactions"]))
        print(maxLedger)

def compareLedgerData(aldous, p2p):
    aldous[0].sort()
    aldous[1].sort()
    p2p[0].sort()
    p2p[1].sort()
    if aldous[0] != p2p[0]:
        print("Keys mismatch :(")
        print(len(aldous[0]))
        print(len(p2p[0]))
        return False
    if aldous[1] != p2p[1]:
        print("Objects mismatch :(")
        print(len(aldous[1]))
        print(len(p2p[1]))
        return False
    print("Responses match!!!!")



    





async def account_info(ip, port, account, ledger, binary):
    address = 'ws://' + str(ip) + ':' + str(port)
    print(binary)
    try:
        async with websockets.connect(address) as ws:
            if ledger is None:
                await ws.send(json.dumps({"command":"account_info","account":account, "binary":bool(binary)}))
                res = json.loads(await ws.recv())
                print(json.dumps(res,indent=4,sort_keys=True))
            else:
                await ws.send(json.dumps({"command":"account_info","account":account, "ledger_index":int(ledger), "binary":bool(binary)}))
                res = json.loads(await ws.recv())
                print(json.dumps(res,indent=4,sort_keys=True))
                return res
    except websockets.exceptions.ConnectionClosedError as e:
        print(e)

def getMinAndMax(res):
    minSeq = None
    maxSeq = None
    for x in res["transactions"]:
        print(x)
        seq = None
        if "ledger_sequence" in x:
            seq = int(x["ledger_sequence"])
        else:
            seq = int(x["ledger_index"])
        if minSeq is None or seq < minSeq:
            minSeq = seq
        if maxSeq is None or seq > maxSeq:
            maxSeq = seq
    return (minSeq,maxSeq)
    

async def account_tx(ip, port, account, binary, minLedger=None, maxLedger=None):

    address = 'ws://' + str(ip) + ':' + str(port)
    try:
        async with websockets.connect(address) as ws:
            if minLedger is None or maxLedger is None:
                await ws.send(json.dumps({"command":"account_tx","account":account, "binary":bool(binary),"limit":200}))
            else:
                await ws.send(json.dumps({"command":"account_tx","account":account, "binary":bool(binary),"limit":200,"ledger_index_min":minLedger, "ledger_index_max":maxLedger}))

            res = json.loads(await ws.recv())
            print(json.dumps(res,indent=4,sort_keys=True))
            return res
    except websockets.exceptions.ConnectionClosedError as e:
        print(e)

async def account_tx_full(ip, port, account, binary,minLedger=None, maxLedger=None,numPages=10):
    address = 'ws://' + str(ip) + ':' + str(port)
    try:
        cursor = None
        marker = None
        req = {"command":"account_tx","account":account, "binary":bool(binary),"limit":200}
        results = {"transactions":[]}
        numCalls = 0
        async with websockets.connect(address) as ws:
            while True:
                numCalls = numCalls+1
                if not cursor is None:
                    req["cursor"] = cursor
                if not marker is None:
                    req["marker"] = marker
                if minLedger is not None and maxLedger is not None:
                    req["ledger_index_min"] = minLedger
                    req["ledger_index_max"] = maxLedger
                await ws.send(json.dumps(req))
                res = json.loads(await ws.recv())
                #print(json.dumps(res,indent=4,sort_keys=True))
                if "result" in res:
                    print(len(res["result"]["transactions"]))
                else:
                    print(len(res["transactions"]))
                if "result" in res:
                    results["transactions"].extend(res["result"]["transactions"])
                else:
                    results["transactions"].extend(res["transactions"])
                if "cursor" in res:
                    cursor = {"ledger_sequence":res["cursor"]["ledger_sequence"],"transaction_index":res["cursor"]["transaction_index"]}
                    print(cursor)
                elif "result" in res and "marker" in res["result"]:
                    marker={"ledger":res["result"]["marker"]["ledger"],"seq":res["result"]["marker"]["seq"]}
                    print(marker)
                else:
                    break    
                if numCalls > numPages:
                    break
            return results
    except websockets.exceptions.ConnectionClosedError as e:
        print(e)

async def tx(ip, port, tx_hash, binary):
    address = 'ws://' + str(ip) + ':' + str(port)
    try:
        async with websockets.connect(address) as ws:
            await ws.send(json.dumps({"command":"tx","transaction":tx_hash,"binary":bool(binary)}))
            res = json.loads(await ws.recv())
            print(json.dumps(res,indent=4,sort_keys=True))
            return res
    except websockets.exceptions.connectionclosederror as e:
        print(e)

async def ledger_entry(ip, port, index, ledger, binary):
    address = 'ws://' + str(ip) + ':' + str(port)
    try:
        async with websockets.connect(address) as ws:
            await ws.send(json.dumps({"command":"ledger_entry","index":index,"binary":bool(binary),"ledger_index":int(ledger)}))
            res = json.loads(await ws.recv())
            print(json.dumps(res,indent=4,sort_keys=True))
            if "result" in res:
                res = res["result"]
            if "object" in res:
                return (index,res["object"])
            else:
                return (index,res["node_binary"])
    except websockets.exceptions.connectionclosederror as e:
        print(e)

async def ledger_entries(ip, port,ledger):
    address = 'ws://' + str(ip) + ':' + str(port)
    entries = await ledger_data(ip, port, ledger, 200, True)

    try:
        async with websockets.connect(address) as ws:
            objects = []
            for x,y in zip(entries[0],entries[1]):
                await ws.send(json.dumps({"command":"ledger_entry","index":x,"binary":True,"ledger_index":int(ledger)}))
                res = json.loads(await ws.recv())
                objects.append((x,res["object"]))
                if res["object"] != y:
                    print("data mismatch")
                    return None
            print("Data matches!")
            return objects

    except websockets.exceptions.connectionclosederror as e:
        print(e)

async def ledger_data(ip, port, ledger, limit, binary):
    address = 'ws://' + str(ip) + ':' + str(port)
    try:
        async with websockets.connect(address) as ws:
            await ws.send(json.dumps({"command":"ledger_data","ledger_index":int(ledger),"binary":bool(binary),"limit":int(limit)}))
            res = json.loads(await ws.recv())
            objects = []
            blobs = []
            keys = []
            if "result" in res:
                objects = res["result"]["state"]
            else:
                objects = res["objects"]
            if binary:
                for x in objects:
                    blobs.append(x["data"])
                    keys.append(x["index"])
                    if len(x["index"]) != 64:
                        print("bad key")
                return (keys,blobs)

    except websockets.exceptions.connectionclosederror as e:
        print(e)

def writeLedgerData(data,filename):
    print(len(data[0]))
    with open(filename,'w') as f:
        data[0].sort()
        data[1].sort()
        for k,v in zip(data[0],data[1]):
            f.write(k)
            f.write('\n')
            f.write(v)
            f.write('\n')


async def ledger_data_full(ip, port, ledger, binary, limit):
    address = 'ws://' + str(ip) + ':' + str(port)
    try:
        blobs = []
        keys = []
        async with websockets.connect(address) as ws:
            if int(limit) < 2048:
                limit = 2048
            marker = None
            while True:
                res = {}
                if marker is None:
                    await ws.send(json.dumps({"command":"ledger_data","ledger_index":int(ledger),"binary":binary, "limit":int(limit)}))
                    res = json.loads(await ws.recv())
                    
                else:

                    await ws.send(json.dumps({"command":"ledger_data","ledger_index":int(ledger),"cursor":marker, "marker":marker,"binary":bool(binary), "limit":int(limit)}))
                    res = json.loads(await ws.recv())
                    
                if "error" in res:
                    print(res)
                    continue

                objects = []
                if "result" in res:
                    objects = res["result"]["state"]
                else:
                    objects = res["objects"]
                for x in objects:
                    blobs.append(x["data"])
                    keys.append(x["index"])
                if "cursor" in res:
                    marker = res["cursor"]
                    print(marker)
                elif "result" in res and "marker" in res["result"]:
                    marker = res["result"]["marker"]
                    print(marker)
                else:
                    print("done")
                    return (keys, blobs)


    except websockets.exceptions.connectionclosederror as e:
        print(e)

def compare_offer(aldous, p2p):
    for k,v in aldous.items():
        if k == "deserialization_time_microseconds":
            continue
        if p2p[k] != v:
            print("mismatch at field")
            print(k)
            return False
    return True

def compare_book_offers(aldous, p2p):
    p2pOffers = {}
    for x in p2p:
        for y in aldous:
            if y["index"] == x["index"]:
                if not compare_offer(y,x):
                    print("Mismatched offer")
                    print(y)
                    print(x)
                    return False
    print("offers match!")
    return True
                    
        

async def book_offers(ip, port, ledger, pay_currency, pay_issuer, get_currency, get_issuer, binary, limit):

    address = 'ws://' + str(ip) + ':' + str(port)
    try:
        offers = []
        cursor = None
        async with websockets.connect(address) as ws:
            while True:
                taker_gets = json.loads("{\"currency\":\"" + get_currency+"\"}")
                if get_issuer is not None:
                    taker_gets["issuer"] = get_issuer
                taker_pays = json.loads("{\"currency\":\"" + pay_currency + "\"}")
                if pay_issuer is not None:
                    taker_pays["issuer"] = pay_issuer 
                req = {"command":"book_offers","ledger_index":int(ledger), "taker_pays":taker_pays, "taker_gets":taker_gets, "binary":bool(binary), "limit":int(limit)}
                if cursor is not None:
                    req["cursor"] = cursor
                await ws.send(json.dumps(req))
                res = json.loads(await ws.recv())
                print(json.dumps(res,indent=4,sort_keys=True))
                if "result" in res:
                    res = res["result"]
                for x in res["offers"]:
                    offers.append(x)
                if "cursor" in res:
                    cursor = res["cursor"]
                    print(cursor)
                else:
                    print(len(offers))
                    return offers
                    
    except websockets.exceptions.connectionclosederror as e:
        print(e)

def compareLedger(aldous, p2p):
    p2p = p2p["result"]["ledger"]
    p2pHeader = p2p["ledger_data"]
    aldousHeader = aldous["header"]["blob"]
    if p2pHeader == aldousHeader:
        print("Headers match!!!")
    else:
        print("Header mismatch")
        print(aldousHeader)
        print(p2pHeader)
        return

    p2pTxns = []
    p2pMetas = []
    for x in p2p["transactions"]:
        p2pTxns.append(x["tx_blob"])
        p2pMetas.append(x["meta"])
    aldousTxns = []
    aldousMetas = []
    for x in aldous["transactions"]:
        aldousTxns.append(x["transaction"])
        aldousMetas.append(x["metadata"])



    p2pTxns.sort()
    p2pMetas.sort()
    aldousTxns.sort()
    aldousMetas.sort()
    if p2pTxns == aldousTxns and p2pMetas == aldousMetas:
        print("Responses match!!!")
    else:
        print("Mismatch responses")
        print(aldous)
        print(p2p)


def getHashes(res):
    print(json.dumps(res,indent=4,sort_keys=True))
    if "result" in res:
        res = res["result"]["ledger"]

    hashes = []
    for x in res["transactions"]:
        if "hash" in x:
            hashes.append(x["hash"])
        elif "transaction" in x and "hash" in x["transaction"]:
            hashes.append(x["transaction"]["hash"])
        else:
            hashes.append(x)
    return hashes


async def ledger(ip, port, ledger, binary, transactions, expand):

    address = 'ws://' + str(ip) + ':' + str(port)
    try:
        async with websockets.connect(address) as ws:
            await ws.send(json.dumps({"command":"ledger","ledger_index":int(ledger),"binary":bool(binary), "transactions":bool(transactions),"expand":bool(expand)}))
            res = json.loads(await ws.recv())
            print(json.dumps(res,indent=4,sort_keys=True))
            return res

    except websockets.exceptions.connectionclosederror as e:
        print(e)

async def ledger_range(ip, port):
    address = 'ws://' + str(ip) + ':' + str(port)
    try:
        async with websockets.connect(address) as ws:
            await ws.send(json.dumps({"command":"ledger_range"}))
            res = json.loads(await ws.recv())
            print(json.dumps(res,indent=4,sort_keys=True))
            if "error" in res:
                await ws.send(json.dumps({"command":"server_info"}))
                res = json.loads(await ws.recv())
                rng = res["result"]["info"]["complete_ledgers"]
                idx = rng.find("-")
                return (int(rng[0:idx]),int(rng[idx+1:-1]))
                
            return (res["ledger_index_min"],res["ledger_index_max"])
    except websockets.exceptions.connectionclosederror as e:
        print(e)

async def perf(ip, port):
    res = await ledger_range(ip,port)
    time.sleep(10)
    res2 = await ledger_range(ip,port)
    lps = ((int(res2[1]) - int(res[1])) / 10.0)
    print(lps)

parser = argparse.ArgumentParser(description='test script for xrpl-reporting')
parser.add_argument('action', choices=["account_info", "tx", "account_tx", "account_tx_full","ledger_data", "ledger_data_full", "book_offers","ledger","ledger_range","ledger_entry","ledger_entries","perf"])
parser.add_argument('--ip', default='127.0.0.1')
parser.add_argument('--port', default='8080')
parser.add_argument('--hash')
parser.add_argument('--account')
parser.add_argument('--ledger')
parser.add_argument('--limit', default='200')
parser.add_argument('--taker_pays_issuer',default='rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B')
parser.add_argument('--taker_pays_currency',default='USD')
parser.add_argument('--taker_gets_issuer')
parser.add_argument('--taker_gets_currency',default='XRP')
parser.add_argument('--p2pIp', default='s2.ripple.com')
parser.add_argument('--p2pPort', default='51233')
parser.add_argument('--verify',default=False)
parser.add_argument('--binary',default=True)
parser.add_argument('--expand',default=False)
parser.add_argument('--transactions',default=False)
parser.add_argument('--minLedger',default=-1)
parser.add_argument('--maxLedger',default=-1)
parser.add_argument('--filename',default=None)
parser.add_argument('--index')
parser.add_argument('--numPages',default=3)




args = parser.parse_args()

def run(args):
    asyncio.set_event_loop(asyncio.new_event_loop())
    if(args.ledger is None):
        args.ledger = asyncio.get_event_loop().run_until_complete(ledger_range(args.ip, args.port))[1]
    if args.action == "perf":
        asyncio.get_event_loop().run_until_complete(
                perf(args.ip,args.port))
    elif args.action == "account_info":
        res1 = asyncio.get_event_loop().run_until_complete(
                account_info(args.ip, args.port, args.account, args.ledger, args.binary))
        if args.verify:
            res2 = asyncio.get_event_loop().run_until_complete(
                    account_info(args.p2pIp, args.p2pPort, args.account, args.ledger, args.binary))
            print(compareAccountInfo(res1,res2))
    elif args.action == "ledger_entry":
        asyncio.get_event_loop().run_until_complete(
                ledger_entry(args.ip, args.port, args.index, args.ledger, args.binary))
    elif args.action == "ledger_entries":
        res = asyncio.get_event_loop().run_until_complete(
                ledger_entries(args.ip, args.port, args.ledger))
        if args.verify:
            objects = []
            for x in res:
                res2 = asyncio.get_event_loop().run_until_complete(
                        ledger_entry(args.p2pIp, args.p2pPort,x[0] , args.ledger, True))
                if res2[1] != x[1]:
                    print("mismatch!")
                    return
            print("Data matches!")


    elif args.action == "tx":
        if args.verify:
            args.binary = True
        if args.hash is None:
            args.hash = getHashes(asyncio.get_event_loop().run_until_complete(ledger(args.ip,args.port,args.ledger,False,True,False)))[0]
        res = asyncio.get_event_loop().run_until_complete(
                tx(args.ip, args.port, args.hash, args.binary))
        if args.verify:
            res2 = asyncio.get_event_loop().run_until_complete(
                    tx(args.p2pIp, args.p2pPort, args.hash, args.binary))
            print(compareTx(res,res2))
    elif args.action == "account_tx":
        if args.verify:
            args.binary=True
        if args.account is None:
            args.hash = getHashes(asyncio.get_event_loop().run_until_complete(ledger(args.ip,args.port,args.ledger,False,True,False)))[0]
        
            res = asyncio.get_event_loop().run_until_complete(tx(args.ip,args.port,args.hash,False))
            args.account = res["transaction"]["Account"]
        
        res = asyncio.get_event_loop().run_until_complete(
                account_tx(args.ip, args.port, args.account, args.binary))
        rng = getMinAndMax(res)


        
        if args.verify:
            res2 = asyncio.get_event_loop().run_until_complete(
                    account_tx(args.p2pIp, args.p2pPort, args.account, args.binary,rng[0],rng[1]))
            print(compareAccountTx(res,res2))
    elif args.action == "account_tx_full":
        if args.verify:
            args.binary=True
        if args.account is None:
            args.hash = getHashes(asyncio.get_event_loop().run_until_complete(ledger(args.ip,args.port,args.ledger,False,True,False)))[0]
        
            res = asyncio.get_event_loop().run_until_complete(tx(args.ip,args.port,args.hash,False))
            args.account = res["transaction"]["Account"]
        res = asyncio.get_event_loop().run_until_complete(
                account_tx_full(args.ip, args.port, args.account, args.binary,None,None,int(args.numPages)))
        rng = getMinAndMax(res)
        print(len(res["transactions"]))
        if args.verify:
            print("requesting p2p node")
            res2 = asyncio.get_event_loop().run_until_complete(
                    account_tx_full(args.p2pIp, args.p2pPort, args.account, args.binary, rng[0],rng[1],int(args.numPages)))

            print(compareAccountTx(res,res2))
    elif args.action == "ledger_data":
        res = asyncio.get_event_loop().run_until_complete(
                ledger_data(args.ip, args.port, args.ledger, args.limit, args.binary))
        if args.verify:
            writeLedgerData(res,args.filename)
    elif args.action == "ledger_data_full":
        if args.verify:
            args.limit = 2048
            args.binary = True
            if args.filename is None:
                args.filename = str(args.port) + "." + str(args.ledger)

        res = asyncio.get_event_loop().run_until_complete(
                ledger_data_full(args.ip, args.port, args.ledger, args.binary, args.limit))
        if args.verify:
            writeLedgerData(res,args.filename)

    elif args.action == "ledger":
        
        if args.verify:
            args.binary = True
            args.transactions = True
            args.expand = True
        res = asyncio.get_event_loop().run_until_complete(
                ledger(args.ip, args.port, args.ledger, args.binary, args.transactions, args.expand))
        if args.verify:
            res2 = asyncio.get_event_loop().run_until_complete(
                    ledger(args.p2pIp, args.p2pPort, args.ledger, args.binary, args.transactions, args.expand))
            print(compareLedger(res,res2))
            
    elif args.action == "ledger_range":
        asyncio.get_event_loop().run_until_complete(
                ledger_range(args.ip, args.port))
    elif args.action == "book_offers":
        if args.verify:
            args.binary=True
        res = asyncio.get_event_loop().run_until_complete(
                book_offers(args.ip, args.port, args.ledger, args.taker_pays_currency, args.taker_pays_issuer, args.taker_gets_currency, args.taker_gets_issuer, args.binary,args.limit))
        if args.verify:
            res2 = asyncio.get_event_loop().run_until_complete(
                    book_offers(args.p2pIp, args.p2pPort, args.ledger, args.taker_pays_currency, args.taker_pays_issuer, args.taker_gets_currency, args.taker_gets_issuer, args.binary, args.limit))
            print(compare_book_offers(res,res2))
            
    else:
        print("incorrect arguments")

        


run(args)
