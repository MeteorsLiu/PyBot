# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import requests
import json
import base64
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import re
from random import randrange
from utils import userid
from urllib import parse
recommendList = None
updateTime = 0

"""
获取Pixiv图片Base64值

参数：picPath，Pixiv图片链接
返回：图片base64 string

"""
def getImage(picPath):
    headers = {
               'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1',
               'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
               'sec-fetch-site': 'cross-site',
               'sec-fetch-mode': 'no-cors',
               'sec-fetch-dest': 'image',
               'referer': 'https://www.pixiv.net/',
               'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh-MO;q=0.7,zh;q=0.6'
    }
    r = requests.get(url=picPath, headers=headers)
    return base64.b64encode(r.content).decode('utf-8')
"""
获取图片Base64值
参数：url，任意图片链接
返回：图片base64 string

"""
def getPin(url):
    r = requests.get(url)
    return base64.b64encode(r.content).decode('utf-8')
"""
获取Pixiv日排行榜
"""
def getList():
    r = requests.get("https://www.pixiv.net/touch/ajax/recommender/top?limit=500&lang=jp")
    message = r.json()
    return message["body"]["related"]
"""
检测多少分钟后
"""
def event_minute_later(event, timeout):
    return event + timeout < time.time()

"""
获取Pixiv日排行榜前500个随机一个图片Base64 String值
"""
def getTop():
    global updateTime 
    global recommendList
    if recommendList:
        if updateTime != 0:
            if event_minute_later(updateTime, 1440):    
                updateTime = time.time()
                recommendList = getList()
    else:
        updateTime = time.time()
        recommendList = getList()
    
    id = recommendList[randrange(0, 499)]
    r = requests.get("https://www.pixiv.net/touch/ajax/illust/details/many?illust_ids[]={}&lang=jp".format(id))
    message = r.json()
    return getImage(message["body"]["illust_details"][0]["url"])

"""
获取指定画师id随机一个画作图片Base64 值
返回：JSON_OBJECT(
    "b64"：画作Base64值
    "uid": 画师id
    "uname": 画师名称
)
"""
def SearchPainter(id):
    r = requests.get("https://www.pixiv.net/touch/ajax/user/illusts?id={}&type=illust&lang=en".format(id))
    message = r.json()
    if message["error"]:
        return json.dumps({"error": "画师{}不存在！".format(id)})
    if int(message["body"]["lastPage"]) > 1:
        r = requests.get("https://www.pixiv.net/touch/ajax/user/illusts?id={}&type=illust&lang=en&p={}".format(id, randrange(1, message["body"]["lastPage"])))
        message = r.json()
    
    randlink = message["body"]["illusts"][randrange(0, len(message["body"]["illusts"])-1)]
    return json.dumps({
        "b64": getImage(randlink["url"]), 
        "from": {
            "uid": randlink["author_details"]["user_id"],
            "uname": randlink["author_details"]["user_name"]
        }
    })

"""
从指定画师id List中抽取一个并获取随机画作
"""
def getRandom():
    userlen = len(userid) - 1
    uid = userid[randrange(0, userlen)]
    return SearchPainter(uid)

"""
根据关键词搜索Pixiv，并抽取随机一个画作，返回其Base64 值
"""
def getName(name, num):
    r = requests.get(url='https://www.pixiv.net/touch/ajax/search/illusts?include_meta=0&type=illust_and_ugoira&s_mode=s_tag_full&word={}&lang=en'.format(name))
    message = r.json()
    b64lists = []
    if int(message["body"]["lastPage"]) > 1:
        r = requests.get(url='https://www.pixiv.net/touch/ajax/search/illusts?include_meta=0&type=illust_and_ugoira&s_mode=s_tag_full&word={}&lang=en&p={}'.format(name, randrange(1, message["body"]["lastPage"])))
        message = r.json()
    #print(message)
    for _ in range(int(num)):
        randlink = message["body"]["illusts"][randrange(0, len(message["body"]["illusts"])-1)]
        b64lists.append({
        "b64":    getImage(randlink["url"]),
        "from": {
            "uid": randlink["author_details"]["user_id"],
            "uname": randlink["author_details"]["user_name"]
            }
        })
    return json.dumps(b64lists)

"""
根据关键词搜索Pinterest，并随机抽取一个，返回其Base64值
"""
def getPinterest(name, num):
    payload = json.dumps(
        {
            "options": {
                "query":name,
                "scope": "pins",
                "page_size":100,
                "no_fetch_context_on_resource": False
            },
            "context": {}
        }
    )
    sourceurl = "/search/pins/?q={}&rs=sitelinks_searchbox".format(name)
    r = requests.get('https://www.pinterest.com/resource/BaseSearchResource/get/?data={}'.format(payload))
    message = r.json()
    #print(message)
    b64list = []
    if "resource_response" in message:
        for _ in range(int(num)):
            try:
                b64list.append(getPin(message["resource_response"]["data"]["results"][randrange(0,len(message["resource_response"]["data"]["results"])-1)]["images"]["orig"]["url"]))
            except:
                return json.dumps({"error": "关键词{}不存在！".format(name)})
    return json.dumps(b64list)
"""
解析微博链接，返回作者姓名，内容，图片，及视频

返回格式：
JSON_OBJECT(
    "author": 作者姓名
    "content": 内容
    "b64": JSON_ARRAY(
        图片Base64值
    )
    "video"：视频地址
)
"""
def getWeibo(link):
    if "weibo.com" in link:
        link = re.sub(r"(www\.)?weibo\.com", "m.weibo.cn", link)
    r = requests.get(link)
    if 'Location' in r.headers:
        r = requests.get(r.headers['Location'])
    ret = {}
    try:
        message = json.loads(re.search(r"\$render_data.*(\[((.|\n)*)}\])", r.content.decode('utf-8')).group().strip("$render_data = "))
        ret["author"] = message[0]["status"]["user"]["screen_name"]
        ret["content"] = re.sub(r'<br \/>','\n',message[0]["status"]["text"])
        ret["content"] = re.sub(r'<.*?>','',ret["content"])
        if "pics" in message[0]["status"]:
            ret["b64"] = []
            for p in message[0]["status"]["pics"]:
                ret["b64"].append(getPin(p["large"]["url"]))

        if "page_info" in message[0]["status"]:
            if "urls" in message[0]["status"]["page_info"]:
                ret["video"] = list(message[0]["status"]["page_info"]["urls"].values())[0]
    except:
        return json.dumps({"error": "微博链接不合法"})
    return json.dumps(ret)



class Handler(BaseHTTPRequestHandler) :
        # A new Handler is created for every incommming request tho do_XYZ
        # methods correspond to different HTTP methods.
        def _set_headers(self, len):
            self.send_response(200)
            self.send_header('Content-type','text/plain; charset=utf-8')
            self.send_header('Content-length', str(len))
            self.end_headers()
        def do_GET(self) :
            if "getrandom" in self.path:
                message = getRandom()
                self._set_headers(len(message))
                self.wfile.write(message.encode('utf-8'))
            if "getname" in self.path:
                query = parse.parse_qs(parse.urlparse(parse.unquote(self.path)).query)
                if len(query) == 0:
                    self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
                message = getName(query["name"][0], query["num"][0])
                self._set_headers(len(message))
                self.wfile.write(message.encode('utf-8'))
            if "getpin" in self.path:
                query = parse.parse_qs(parse.urlparse(parse.unquote(self.path)).query)
                if len(query) == 0:
                    self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
                message = getPinterest(query["name"][0], query["num"][0])
                self._set_headers(len(message))
                self.wfile.write(message.encode('utf-8'))
            if "getbyid" in self.path:
                query = parse.parse_qs(parse.urlparse(parse.unquote(self.path)).query)
                if len(query) == 0:
                    self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
                message = SearchPainter(query["id"][0])
                self._set_headers(len(message))
                self.wfile.write(message.encode('utf-8'))
            if "repost" in self.path:
                query = parse.parse_qs(parse.urlparse(parse.unquote(self.path)).query)
                if len(query) == 0:
                    self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
                if "weibo" not in query["link"][0]:
                    self.wfile.write(json.dumps({"error": "参数错误"}).encode('utf-8'))
                message = getWeibo(query["link"][0])
                self._set_headers(len(message))
                self.wfile.write(message.encode('utf-8'))

s = HTTPServer( ('172.30.56.22', 6700), Handler )
s.serve_forever()
