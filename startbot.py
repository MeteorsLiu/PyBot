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
from collections import Counter
from match import Rule
import jieba

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
loop = asyncio.get_event_loop()

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
    return re.sub(r"([。，！？；”“""《》.,!?])", r"", s)


def getRandom():
    r = requests.get("http://172.30.56.22:6700/getrandom")
    return json.loads(r.content.decode('utf-8'))

def getReplyByQingyunke(sentence):
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

class Robot(object):
    def __init__(self, ws, loop, gid=None, uid=None):
        self.websocket = ws
        self.loop = loop
        self.gid  = gid
        self.uid  = uid
    async def sendImage(self, b64):
        if self.uid:
            await self.websocket.send(
                json.dumps(
                {
                    "action": "send_msg", 
                    "params": {
                        "user_id": self.uid,
                        "message": "[CQ:image,file=base64://{}]".format(b64)
                    }
                }
            ))
        else:
            await self.websocket.send(
                json.dumps(
                {
                    "action": "send_group_msg", 
                    "params": {
                        "group_id": self.gid, 
                        "message": "[CQ:image,file=base64://{}]".format(b64)
                    }
                }
            ))
    async def sendMessage(self, m):
        if self.uid:
            await self.websocket.send(
                json.dumps(
                {
                    "action": "send_msg", 
                    "params": {
                        "user_id": self.uid,
                        "message": m       
                    }
                }
            ))
        else:
            await self.websocket.send(
                json.dumps(
                {
                    "action": "send_group_msg", 
                    "params": {
                        "group_id": self.gid, 
                        "message": m       
                    }
                }
            ))
    async def sendVideo(self, l):
        if self.uid:
            await self.websocket.send(
                    json.dumps(
                    {"action": "send_msg", 
                    "params": {"user_id": self.uid, 
                    "message": "[CQ:video,file={}]".format(l)
            }}))
        else:
            await self.websocket.send(
                    json.dumps(
                    {"action": "send_group_msg", 
                    "params": {"group_id": self.gid, 
                    "message": "[CQ:video,file={}]".format(l)
            }}))
    async def sendRandomPic(self, times):
        for _ in range(times):
            #print(times)
            r = getRandom()
            if "error" in r:
                await self.sendMessage(r["error"])
                return
            await asyncio.gather(
                self.sendImage(r["b64"]),
                self.sendMessage("画师ID:{}, 画师名字: {}".format(r["from"]["uid"], r["from"]["uname"]))
            )

    async def searchPicAndSend(self, name, times):
        try:
            r = requests.get("http://172.30.56.22:6700/getname?name={}&num={}".format(name, times))
            message = r.json()
        except:
            await self.sendMessage("关键词{}无法查找".format(name))
            return
        #print(message)
        if "error" in message:
            await self.sendMessage(message["error"])
            return
        for m in message:
            await asyncio.gather(
                self.sendImage(m["b64"]),
                self.sendMessage("画师ID:{}, 画师名字: {}".format(m["from"]["uid"], m["from"]["uname"]))
            )


    async def searchPinterest(self, word, num):
        try:
            r = requests.get("http://172.30.56.22:6700/getpin?name={}&num={}".format(word, num))
            message = r.json()
        except:
            await self.sendMessage("关键词{}无法查找".format(word))
            return
        if "error" in message:
            await self.sendMessage(message["error"])
            return
        for m in message:
            await self.sendImage(m)

    async def searchPicByID(self, ids):
        for id in ids:
            try:
                r = requests.get("http://172.30.56.22:6700/getbyid?id={}".format(id))
                message = r.json()
            except:
                await self.sendMessage("画师id{}无法查找".format(id))
                continue
            if "error" in message:
                await self.sendMessage(message["error"])
                return
            await self.sendImage(message["b64"])
            
    async def getWeibo(self, l):
        try:
            r = requests.get("http://172.30.56.22:6700/repost?link={}".format(l))
            message = r.json()
            if "error" in message:
                await self.sendMessage(message["error"])
                return
            await self.sendMessage("作者："+message["author"])
            if "content" in message:
                await self.sendMessage("内容："+message["content"])
            if "b64" in message:
                for m in message["b64"]:
                    await self.sendImage(m)
            if "video" in message:
                await self.sendVideo(message["video"])
        except:
            await self.sendMessage("Atri拒绝了该请求")

    async def getTelegram(self, l):
        try:
            r = requests.get("http://172.30.56.22:6700/tg?link={}".format(l))
            message = r.json()
            if "error" in message:
                await self.sendMessage(message["error"])
                return
            await self.sendMessage("作者："+message["author"])
            if "content" in message:
                await self.sendMessage("内容：\n"+message["content"])
            if "b64" in message:
                for m in message["b64"]:
                    await self.sendImage(m)
            if "video" in message:
                await self.sendVideo(message["video"])
            if "link" in message:
                await self.sendMessage("相关链接：\n"+'\n'.join(message["link"]))
        except:
            await self.sendMessage("Atri拒绝了该请求")

    async def getBaidu(self, s):
        ret = await self.loop.run_in_executor(None , rule.word_segment_text_bank, s)
        counter = sum(Counter([f for _, f in ret if 'm' in f or 'q' in f]).values())
        return (ret, counter)

    async def getNonBaidu(self, s):
        ret = await self.loop.run_in_executor(None ,rule.word_segment_text_bank_no_paddle, s)
        counter = sum(Counter([f for _, f in ret if 'm' in f or 'q' in f]).values())
        return (ret, counter)

    async def getF(self, s):
        tup = await asyncio.gather(
            self.getBaidu(s), 
            self.getNonBaidu(s)
        )

        if tup[0][1] > tup[0][1]:
            print(tup[0])
            return tup[0][0]
        else:
            print(tup[1])
            return tup[1][0]

    async def matchAction(self, sentence, e):
        try:
            matched, texts = rule.smatch(sentence, ['获取','查看', '照片', '图片', '图'])    
            drawMatched, weebdict, andict = rule.match(texts, [('搜索', 'v'), ('动画', 'n'), ('图片', 'n'), ('兽迷', 'n')], '动画')
        except:
            print("Match Action Fail!")
            return False
        try:
            flag = False
            if len(weebdict) > 0 and drawMatched and matched:
                for w in weebdict:
                    await self.sendMessage("搜索{}{}张照片".format(w,weebdict[w]))
                    await self.searchPicAndSend(w, weebdict[w])
                flag = True
            if len(andict) > 0 and matched:
                for a in andict:
                    if a != '_pic':
                        await self.sendMessage("搜索{}{}张照片".format(a, andict[a]))
                        await self.searchPinterest(a, andict[a])
                flag = True
            if "_pic" in andict and matched:
                await self.sendRandomPic(andict["_pic"])
                flag = True
            if flag:
                e.set()
        except Exception as ex:
            print(ex)
        return flag
    

    async def matchName(self, sentence, e):
        if '叫' not in sentence or len(sentence) > 7:
            return
        matched, _ = rule.smatch(sentence, ['获取','名字'])
        if matched:
            await self.sendMessage("我叫Atri噢")
            e.set()
            return True
        return False

    async def matchPainter(self, sentence, e):
        matched, t = rule.smatch(sentence, ['搜索', '画师', 'id'])
        if matched:
            await self.searchPicByID([i for i,f in t if (f == 'eng' or f == 'm') and i.isdigit()])
            e.set()
            return True
        return False

    async def matchFreeLink(self, sentence, e):
        try:
            if self.gid != "649451770":
                return
            matched, _ = rule.smatch(sentence, ['获取', '订阅'])
            print("Target match Free link Done")
            if matched:
                await self.sendMessage("Clash输入\n999.tf\n就好咯")
                e.set()
                return True
        except Exception as ex:
            print(ex)
        return False

    async def matchUsage(self, sentence, e):
        if len(sentence) > 10:
            return
        matched, _ = rule.smatch(sentence, ['获取',  '功能'])
        if matched:
            await self.sendMessage("""你可以尝试对我说:
            atri，来张图，或者明确点
            来张雷姆的图，如果你需要多来几张，也可以说
            来五张图，来五张雷姆，或者搜索五张雷姆，这样子都是可以的喔
            咱也支持搜索画师id哒！
            你可以对我说，atri，搜索画师2131231(这串数字替换成你想要的画师id即可)
            你以为我只会干这么点事？
            咱还可以帮你转发电报和微博呢，你只需要对我说：
            转发电报(替换成你的电报链接)
            转发微博(你的微博链接)
            另外捏，咱是开源的，来项目主页给颗star吧
            github.com/MeteorsLiu/PyBot
            爱你喔""")
            e.set()
            return True
        return False

    async def matchParent(self, sentence, e):
        try:
            if len(sentence) > 7:
                return
            matched, _ = rule.smatch(sentence, ['父母'])
            if matched:
                await self.sendMessage("我叫Atri噢")
                e.set()
                return True
        except:
            raise
        return False

    async def sendPic(self, path):
        try:
            with open(path, "rb") as image_file:
                await self.websocket.send(
                    json.dumps(
                        {"action": "send_group_msg", 
                        "params": {"group_id": "649451770", 
                        "message": "[CQ:image,file=base64://{}]".format(base64.b64encode(image_file.read()).decode('utf-8'))
                    }}))
        except FileNotFoundError:
            print("File not found")
        except websockets.ConnectionClosed:
            print("Connection closed")
async def worker(_t, robot: Robot, isPrivate=False):
    #常规指令匹配
    if "!随机" in _t:
        await robot.sendRandomPic(1)
        return
    if "获取功能" in _t:
        await robot.sendMessage(
            """你可以尝试对我说: 
            atri，来张图，或者明确点
            来张雷姆的图，如果你需要多来几张，也可以说
            来五张图，来五张雷姆，或者搜索五张雷姆，这样子都是可以的喔
            咱也支持搜索画师id哒！
            你可以对我说，atri，搜索画师2131231(这串数字替换成你想要的画师id即可)
            你以为我只会干这么点事？
            咱还可以帮你转发电报和微博呢，你只需要对我说：
            转发电报(替换成你的电报链接)
            转发微博(你的微博链接)
            另外捏，咱是开源的，来项目主页给颗star吧
            github.com/MeteorsLiu/PyBot
            爱你喔
            """
        )
        return
    if "转发微博" in _t:
        link = re.sub("转发微博(。|，|？|！|\?|\!|\.|\,|：|:)?", '', _t)
        await robot.getWeibo(link)
        return

    if "转发电报" in _t:
        link = re.sub("转发电报(。|，|？|！|\?|\!|\.|\,|：|:)?", '', _t)
        await robot.getTelegram(link)
        return

    #动态匹配
    realmessage = None
    if "atri" in _t or "亚托莉" in _t:
        realmessage = re.sub("^(atri|亚托莉)(。|，|？|！|\?|\!|\.|\,)?", '', _t).strip()
    if "CQ:at" in _t and "2301059398" in _t:
        realmessage = re.sub(r'\[.*?\]', '', _t).strip()
    if isPrivate:
        if not realmessage:
            realmessage = _t

    if realmessage:
        if "发张图" in realmessage or ("发" in realmessage and "图" in realmessage):
            await robot.sendRandomPic(1)
            return

        isChinese = False
        if is_all_chinese(realmessage):
            isChinese = True
            realmessage = normalizeChinese(realmessage)
            wordseg = await robot.getF(realmessage)
            event = asyncio.Event()
            
            await robot.matchAction(wordseg, event)
            await robot.matchPainter(wordseg, event)
            await robot.matchFreeLink(wordseg, event)
            
            if event.is_set(): 
                event.clear()
                return
        else:
            realmessage = normalizeString(realmessage)

        try:
            if not isChinese:
                content = en(realmessage, "en")
                content = ' '.join(content)
            else:
                content = zh(' '.join(jieba.lcut(realmessage)), "en")
                content = ''.join(content)
        except:
            content = getTencent(realmessage)
            #randint = randrange(0,50)
            #if randint % 2 == 0:
            #    content = getRobot(realmessage)
            #else:
        await robot.sendMessage(content)
        

async def echo(websocket, path):
    robot = Robot(websocket, loop)
    while websocket.open:
        message = await websocket.recv()
        message = json.loads(message)
        if "sender" in message and "message" in message:
            isPrivate = False
            if "CQ" in message["message"]:
                if "CQ:at" not in message["message"] and "CQ:reply" not in message["message"]:
                    #print("Exclude MSG {}".format(message["message"]))
                    continue
            if "user_id" in message and message["message_type"] == 'private' and not "group_id" in message:
                isPrivate = True
                robot.uid = message["user_id"]
            elif "group_id" in message and not isPrivate:
                robot.gid = message["group_id"]
            else:
                continue
            _t = message["message"].strip()
            await worker(_t, robot, isPrivate)
            if isPrivate:
                robot.uid = None

async def main():
    async with websockets.serve(echo, "127.0.0.1", 6750):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    n_layers, hidden_size, reverse = parseFilename("/home/clean_chat_corpus/pytorch-chatbot/save/model/somefile/1-1_512/10000_backup_bidir_model.tar", False)
    zh = Model(n_layers, hidden_size, "save/model/corpus/1-1_512/10000_backup_bidir_model.tar", "corpus.txt")
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
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        loop.stop()
        loop.close()
    except:
        raise


