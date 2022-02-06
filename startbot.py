#!/usr/bin/env python

import asyncio
from curses.ascii import isdigit
import websockets
import json
import base64
import requests
from evaluate import *
import unicodedata

import re


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

    
def is_all_chinese(strs):
    for _char in strs:
        if not '\u4e00' <= _char <= '\u9fa5':
            return False
    return True

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


def getRobot(sentence):
    r = requests.get("http://api.qingyunke.com/api.php?key=free&appid=0&msg={}".format(sentence))
    return r.json()["content"]

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
            if "!随机" in message["message"]:
                await websocket.send(
                    json.dumps(
                        {"action": "send_group_msg", 
                        "params": {"group_id": "649451770", 
                        "message": "[CQ:image,file=base64://{}]".format(getRandom())
                    }}))
            if "CQ:at" in message["message"] and "2301059398" in message["message"]:
                realmessage = re.sub(r'^\[.*?\]', '', message["message"]).strip()
                if "发张图" in realmessage:
                    await websocket.send(
                        json.dumps(
                            {"action": "send_group_msg", 
                            "params": {"group_id": "649451770", 
                            "message": "[CQ:image,file=base64://{}]".format(getRandom())
                    }}))
                    return
                try:
                    if is_all_chinese(realmessage):
                        content = zh(realmessage, "zh")
                    else:
                        realmessage = normalizeString(realmessage)
                        content = en(realmessage, "en")
                        content = ' '.join(content)
                except KeyError:
                    content = getRobot(realmessage)

                await websocket.send(
                    json.dumps(
                        {"action": "send_group_msg", 
                        "params": {"group_id": "649451770", 
                        "message": content
                    }}))


def getRandom():
    r = requests.get("http://172.30.199.164:6700/getrandom")
    return r.content.decode('utf-8')

async def main():
    async with websockets.serve(echo, "127.0.0.1", 6750):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    n_layers, hidden_size, reverse = parseFilename("/home/clean_chat_corpus/pytorch-chatbot/save/model/somefile/1-1_512/10000_backup_bidir_model.tar", False)
    zh = Model(n_layers, hidden_size, "/home/clean_chat_corpus/pytorch-chatbot/save/model/somefile/1-1_512/10000_backup_bidir_model.tar", "/home/clean_chat_corpus/somefile")
    n_layers, hidden_size, reverse = parseFilename("/home/clean_chat_corpus/pytorch-chatbot/save/model/movie_subtitles/1-1_512/50000_backup_bidir_model.tar", False)
    en = Model(n_layers, hidden_size, "/home/clean_chat_corpus/pytorch-chatbot/save/model/movie_subtitles/1-1_512/50000_backup_bidir_model.tar", "/home/clean_chat_corpus/pytorch-chatbot/movie.txt")
    
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except:
        raise
