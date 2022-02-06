from email import message
import requests
import json
import base64
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

from random import randrange
from utils import userid

recommendList = None
updateTime = 0

def getImage(picPath):
    headers = {
               'user-agent': 'user-agent: Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1',
               'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
               'sec-fetch-site': 'cross-site',
               'sec-fetch-mode': 'no-cors',
               'sec-fetch-dest': 'image',
               'referer': 'https://www.pixiv.net/',
               'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh-MO;q=0.7,zh;q=0.6'
    }
    r = requests.get(url=picPath, headers=headers)
    return base64.b64encode(r.content).decode('utf-8')

def getList():
    r = requests.get("https://www.pixiv.net/touch/ajax/recommender/top?limit=500&lang=jp")
    message = r.json()
    return message["body"]["related"]

def event_minute_later(event, timeout):
    return event + timeout < time.time()

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

def SearchPainter(id):
    r = requests.get("https://www.pixiv.net/touch/ajax/user/illusts?id={}&type=illust&lang=en".format(id))
    message = r.json()
    if message["error"]:
        return 1
    if int(message["body"]["lastPage"]) > 1:
        r = requests.get("https://www.pixiv.net/touch/ajax/user/illusts?id={}&type=illust&lang=en&p={}".format(id, randrange(1, message["body"]["lastPage"])))
        message = r.json()
    return getImage(message["body"]["illusts"][randrange(0, len(message["body"]["illusts"])-1)]["url"])

def getRandom():
    userlen = len(userid) - 1
    uid = userid[randrange(0, userlen)]
    return SearchPainter(uid)


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

s = HTTPServer( ('172.30.199.164', 6700), Handler )
s.serve_forever()
