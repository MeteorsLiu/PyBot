from selenium import webdriver 
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.chrome.options import Options 
import re


if __name__ == "__main__":
    options = Options() 
    options.add_argument("--headless")
    options.add_argument("--no-sandbox") 
    driver = webdriver.Chrome(executable_path='/usr/bin/chromedriver', chrome_options=options) 
    namelist = []
    try:
        with open("jieba_dict/userdict.txt", "a") as myfile:
            nextPage = "https://zh.moegirl.org.cn/index.php?title=Category:%E4%BA%BA%E7%89%A9&from=A"
            page = 0
            while nextPage:
                driver.get(nextPage)
                nextPage = None
                page += 1
                namelist.clear()
                print("处理第{}页".format(page))
                elems = driver.find_elements_by_css_selector("div.mw-category-generated div[id=mw-pages] a")
                for i, elem in enumerate(elems):
                    if elem.text != '上一页' and elem.text != '下一页':
                        name = re.sub(r'\(.*\)|[·]|.*:', '', elem.text.strip())
                        if len(name) > 1:
                            namelist.append(name)
                    if elem.text == '下一页' and i == 1:
                        nextPage = elem.get_attribute("href")
                for k in list(dict.fromkeys(namelist)):
                    myfile.write(k+'\n')
        driver.close()
    finally:
        driver.quit()