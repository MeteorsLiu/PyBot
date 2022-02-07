import re
import requests



if __name__ == '__main__':
    headers = {
        'authority': 'api.bilibili.com',
        'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="97", "Chromium";v="97"',
        'sec-ch-ua-mobile': '?0',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'accept': '*/*',
        'sec-fetch-site': 'same-site',
        'sec-fetch-mode': 'no-cors',
        'sec-fetch-dest': 'script',
        'referer': 'https://space.bilibili.com/26937150/article',
        'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh-MO;q=0.7,zh;q=0.6',
        "cookie": "buvid3=20516B11-A84C-4665-978D-75DE26D6545C190962infoc; LIVE_BUVID=AUTO5915680244365699; rpdid=|(u|Jk~Rk~Yk0J\'ulY)|kR~l~; sid=4wcv5brc; fingerprint=352932c2da9199d9514693273940bc7b; buvid_fp=20516B11-A84C-4665-978D-75DE26D6545C190962infoc; buvid_fp_plain=20516B11-A84C-4665-978D-75DE26D6545C190962infoc; DedeUserID=81169408; DedeUserID__ckMd5=8e0eaef9e60e33c5; SESSDATA=e0277c4e%2C1655261475%2C85693*c1; bili_jct=84bb812837533b30db8364600b399d65; blackside_state=1; i-wanna-go-back=-1; b_ut=5; CURRENT_QUALITY=80; AMCV_98CF678254E93B1B0A4C98A5%40AdobeOrg=-2121179033%7CMCMID%7C29119062753851439562834007988501425051%7CMCOPTOUT-1641299345s%7CNONE%7CvVersion%7C5.3.0; CURRENT_FNVAL=4048; innersign=0; bp_video_offset_81169408=624103548921183600"
 
    }
    artlist = []
    r = requests.get(url='https://api.bilibili.com/x/space/article?mid=26937150&pn=1&ps=12&sort=publish_time&jsonp=jsonp&callback=' , headers=headers)
    art = r.json()['data']['articles']

    for i in range(1, 100):
        for a in art:
            if "期PIXIV画师推荐" in a['title']:
                ret = re.search("(/[0-9]+)|(=[0-9]+)", a['summary'].strip())
                if ret:
                    artlistid = ret.group().strip("/").strip("=")
                    if artlistid not in artlist:
                        artlist.append(artlistid)
        r = requests.get(url='https://api.bilibili.com/x/space/article?mid=26937150&pn={}&ps=12&sort=publish_time&jsonp=jsonp&callback='.format(i) , headers=headers)
        art = r.json()['data']['articles']

    print(artlist)
