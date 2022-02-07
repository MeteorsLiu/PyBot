
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
        'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh-MO;q=0.7,zh;q=0.6'
    }
    artlist = []
    r = requests.get(url='https://api.bilibili.com/x/space/article?mid=26937150&pn=1&ps=12&sort=publish_time&jsonp=jsonp&callback=' , headers=headers)
    art = r.json()['data']['articles']
    for i in range(100):
        for a in art:
            if "PIXIV画师推荐" in a['title']:
                artlist.append(re.sub("^.*\/", '', a['summary'].strip()))
        r = requests.get(url='https://api.bilibili.com/x/space/article?mid=26937150&pn={}&ps=12&sort=publish_time&jsonp=jsonp&callback='.format(i) , headers=headers)
        art = r.json()['data']['articles']

    print(artlist)