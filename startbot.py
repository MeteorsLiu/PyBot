# -*- coding: utf-8 -*-
from __future__ import unicode_literals
#!/usr/bin/env python

import asyncio
from random import randrange

from torch import real

import websockets
import json
import base64
import requests
from evaluate import *
import unicodedata
import contextvars
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.nlp.v20190408 import nlp_client
from tencentcloud.nlp.v20190408 import models as m
import re
from match import Rule


def parseFilename(filename, test=False):
    filename = filename.split('/')
    dataType = filename[-1][:-4] # remove '.tar'
    parse = dataType.split('_')
    reverse = 'reverse' in parse
    layers, hidden = filename[-2].split('_')
    n_layers = int(layers.split('-')[0])
    hidden_size = int(hidden)
    return n_layers, hidden_size, reverse


zh = None
en = None
rule = None
client = None

def is_all_chinese(strs):
    for _char in strs:
        if '\u4e00' <= _char <= '\u9fa5':
            return True
    return False

def unicodeToAscii(s):
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )

# Lowercase, trim, and remove non-letter characters
def normalizeString(s):
    s = unicodeToAscii(s.lower().strip())
    s = re.sub(r"([.!?])", r" \1", s)
    s = re.sub(r"[^a-zA-Z.!?]+", r" ", s)
    s = re.sub(r"\s+", r" ", s).strip()
    return s
def normalizeChinese(s):
    s = re.sub(r"([。，！？；”“""《》.,!?])", r"", s.replace(" ",""))
    return s
def getRandom():
    r = requests.get("http://172.30.56.22:6700/getrandom")
    return json.loads(r.content.decode('utf-8'))

async def sendRandomPic(websocket, times):
    for _ in range(times):
        print(times)
        r = getRandom()
        if "error" in r:
            await sendMessage(websocket, r["error"])
            return
    
        await websocket.send(
                json.dumps(
                {"action": "send_group_msg", 
                "params": {"group_id": "649451770", 
                "message": "[CQ:image,file=base64://{}]".format(r["b64"])
        }}))
        await sendMessage(websocket, "画师ID:{}, 画师名字: {}".format(r["from"]["uid"], r["from"]["uname"]))

async def searchPicAndSend(websocket, name, times):
    try:
        r = requests.get("http://172.30.56.22:6700/getname?name={}&num={}".format(name, times))
        message = r.json()
        #print(message)
        if "error" in message:
            await sendMessage(websocket, message["error"])
            return
        for m in message:
            await websocket.send(
                json.dumps(
                {"action": "send_group_msg", 
                "params": {"group_id": "649451770", 
                "message": "[CQ:image,file=base64://{}]".format(m["b64"])
            }}))
            await sendMessage(websocket, "画师ID:{}, 画师名字: {}".format(m["from"]["uid"], m["from"]["uname"]))
    except Exception as e:
        raise e

async def sendMessage(websocket, m):
    await websocket.send(
            json.dumps(
            {"action": "send_group_msg", 
            "params": {"group_id": "649451770", 
            "message": m           
    }}))

async def searchPinterest(websocket, word, num):
    r = requests.get("http://172.30.56.22:6700/getpin?name={}&num={}".format(word, num))
    message = r.json()
    if "error" in message:
        await sendMessage(websocket, message["error"])
        return
    for m in message:
        await websocket.send(
                json.dumps(
                {"action": "send_group_msg", 
                "params": {"group_id": "649451770", 
                "message": "[CQ:image,file=base64://{}]".format(m)
        }}))

async def searchPicByID(websocket, ids):
    for id in ids:
        r = requests.get("http://172.30.56.22:6700/getbyid?id={}".format(id))
        message = r.json()
        if "error" in message:
            await sendMessage(websocket, message["error"])
            return
        await websocket.send(
            json.dumps(
            {"action": "send_group_msg", 
            "params": {"group_id": "649451770", 
            "message": "[CQ:image,file=base64://{}]".format(message["b64"])
        }}))
        

async def matchAction(websocket, sentence, e):
    try:
        matched, texts = rule.smatch(sentence, ['获取', '照片'])    
        drawMatched, weedict, andict = rule.match(texts, [('搜索', 'v'), ('动画', 'n'), ('图片', 'n'), ('兽迷', 'n')], '动画')
    except:
        return False
    flag = False
    if len(weedict) > 0 and drawMatched:
        for w in weedict:
            await sendMessage(websocket, "搜索{}{}张照片".format(w,weedict[w]))
            await searchPicAndSend(websocket, w, weedict[w])
        flag = True
    if len(andict) > 0 and matched:
        for a in andict:
            if a != '_pic':
                await sendMessage(websocket, "搜索{}{}张照片".format(a, andict[a]))
                await searchPinterest(websocket, a, andict[a])
        flag = True
    if "_pic" in andict and matched:
        await sendRandomPic(websocket, andict["_pic"])
        flag = True
    if flag:
        e.set()
    return flag
 

async def matchName(websocket, sentence, e):
    matched, _ = rule.smatch(sentence, ['获取', '名字', '个性'])
    if matched:
        await sendMessage(websocket, "我叫Atri噢")
        e.set()
        return True
    return False

async def matchPainter(websocket, sentence, e):
    matched, t = rule.smatch(sentence, ['搜索', '画师', 'id'])
    if matched:
        await searchPicByID(websocket, [i for i,f in t if f == 'eng' and i.isdigit()])
        e.set()
        return True
    return False


def getRobot(sentence):
    r = requests.get("http://api.qingyunke.com/api.php?key=free&appid=0&msg={}".format(sentence))
    return r.json()["content"]

def getTencent(sentence):
    try:
        req = m.ChatBotRequest()
        params = {
            "Query": sentence
        }
        req.from_json_string(json.dumps(params))

        resp = client.ChatBot(req)
    except:
        return "腾讯云接口错误"
    return re.sub('(腾讯)?小龙女', 'Atri', resp.Reply)

async def sendPic(ws, path):
    try:
        with open(path, "rb") as image_file:
            await ws.send(
                json.dumps(
                    {"action": "send_group_msg", 
                    "params": {"group_id": "649451770", 
                    "message": "[CQ:image,file=base64://{}]".format(base64.b64encode(image_file.read()).decode('utf-8'))
                }}))
    except FileNotFoundError:
        print("File not found")
    except websockets.ConnectionClosed:
        print("Connection closed")

async def echo(websocket, path):
    while websocket.open:
        message = await websocket.recv()
        message = json.loads(message)
        if "sender" in message and "message" in message:
            _t = message["message"].lower().strip()
            if "!随机" in message["message"]:
                await sendRandomPic(websocket, 1)
            if "atri" in _t:
                realmessage = re.sub("^atri(。|，|？|！|\?|\!|\.|\,)?", '', _t)
                if "发张图" in realmessage or ("发" in realmessage and "图" in realmessage):
                    await sendRandomPic(websocket, 1)
                isChinese = False
                if is_all_chinese(realmessage):
                    isChinese = True
                    realmessage = normalizeChinese(realmessage)
                else:
                    realmessage = normalizeString(realmessage)
                wordseg = rule.word_segment_text_bank(realmessage)
                event = asyncio.Event()
                ret = await asyncio.gather(
                    matchAction(websocket, wordseg, event),
                    matchName(websocket, wordseg, event),
                    matchPainter(websocket, wordseg, event)
                )
                if event.is_set():
                    event.clear()
                    continue
                try:
                    if isChinese:
                        content = zh(realmessage, "zh")
                    else:
                        content = en(realmessage, "en")
                        content = ' '.join(content)
                except KeyError:
                    #randint = randrange(0,50)
                    #if randint % 2 == 0:
                    #    content = getRobot(realmessage)
                    #else:
                    content = getTencent(realmessage)
                await websocket.send(
                    json.dumps(
                        {"action": "send_group_msg", 
                        "params": {"group_id": "649451770", 
                        "message": content
                }}))

            if "CQ:at" in message["message"] and "2301059398" in message["message"]:
                realmessage = re.sub(r'^\[.*?\]', '', message["message"]).strip()
                if "发张图" in realmessage or ("发" in realmessage and "图" in realmessage):
                    await sendRandomPic(websocket, 1)
                    continue
                try:
                    if is_all_chinese(realmessage):
                        content = zh(realmessage, "zh")
                    else:
                        content = en(realmessage, "en")
                        content = ' '.join(content)
                except KeyError:
                    #randint = randrange(0,50)
                    #if randint % 2 == 0:
                    #    content = getRobot(realmessage)
                    #else:
                    content = getTencent(realmessage)


                await websocket.send(
                    json.dumps(
                        {"action": "send_group_msg", 
                        "params": {"group_id": "649451770", 
                        "message": content
                    }}))




async def main():
    async with websockets.serve(echo, "127.0.0.1", 6750):
        await asyncio.Future()  # run forever



if __name__ == "__main__":
    n_layers, hidden_size, reverse = parseFilename("/home/clean_chat_corpus/pytorch-chatbot/save/model/somefile/1-1_512/10000_backup_bidir_model.tar", False)
    zh = Model(n_layers, hidden_size, "/home/clean_chat_corpus/pytorch-chatbot/save/model/somefile/1-1_512/10000_backup_bidir_model.tar", "/home/clean_chat_corpus/somefile")
    n_layers, hidden_size, reverse = parseFilename("/home/clean_chat_corpus/pytorch-chatbot/save/model/movie_subtitles/1-1_512/50000_backup_bidir_model.tar", False)
    en = Model(n_layers, hidden_size, "/home/clean_chat_corpus/pytorch-chatbot/save/model/movie_subtitles/1-1_512/50000_backup_bidir_model.tar", "/home/clean_chat_corpus/pytorch-chatbot/movie.txt")
    cred = credential.Credential("", "")
    httpProfile = HttpProfile()
    httpProfile.endpoint = "nlp.tencentcloudapi.com"
    rule = Rule()
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    client = nlp_client.NlpClient(cred, "ap-guangzhou", clientProfile)


    try:
        asyncio.get_event_loop().run_until_complete(main())
    except:
        raise

