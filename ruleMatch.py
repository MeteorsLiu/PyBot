"""
原作者：zake7749
修改人：MeteorLiu

为方便对接修改了部分接口

开源协议：AGPL-3.0 请注意遵守AGPL-3.0

"""

from __future__ import unicode_literals

import jieba
import jieba.posseg as pseg
import os
from gensim import models

def ChineseNumConvert(word):
    cnd = {
            '零':1,
            '一':1, 
            '二':2,
            '两':2,
            '俩':2,
            '仨':3, 
            '三':3,
            '四':4,
            '五':5,
            '六':6,
            '七':7,
            '八':8,
            '九':9,
            '十':10
        }
    if len(word) > 1:
        raise ValueError('太多了')
    if word in cnd:
        return cnd[word]
    else:
        return 1
class Rule(object):
    
    def __init__(self,model_path="word2vec.model"):

        self.name = "ATRI"             # The name of chatbot.
        self.model = None

        print("[Console] Loading the word embedding model...")
        stopword="jieba_dict/stopword.txt"
        #jieba_dic="jieba_dict/dict.txt.big"
        #jieba_user_dic="jieba_dict/userdict.txt"
        #self.init_jieba(jieba_dic,jieba_user_dic)
        jieba.enable_parallel(2)
        self.stopword = self.load_stopword(stopword)

        try:                
            # jieba custom setting.

            self.load_model(model_path)
        except FileNotFoundError as e:
            print("[Console] 請確定詞向量模型有正確配置")
            print(e)
            exit()
        except Exception as e:
            print("[Gensim]")
            print(e)
            exit()


    def load_model(self,path):

        """
        Load a trained word2vec model(binary format only).

        Args:
            path: the path of the model.
        """
        try:
            self.model = models.Word2Vec.load(path)  # current loading method
        except FileNotFoundError as file_not_found_err:
            print("[Gensim] FileNotFoundError", file_not_found_err)
            exit()
        except UnicodeDecodeError as unicode_decode_err:
            print("[Gensim] UnicodeDecodeError", unicode_decode_err)
            self.model = models.KeyedVectors.load_word2vec_format(path, binary=True)  # old loading method
        except Exception as ex:
            print("[Gensim] Exception", ex)
            exit()


    def init_jieba(self, seg_dic, userdic):
        jieba.load_userdict(userdic)
        jieba.set_dictionary(seg_dic)
        jieba.enable_parallel(2)
        with open(userdic,'r',encoding='utf-8') as input:
            for word in input:
                word = word.strip('\n')
                jieba.suggest_freq(word, True)

    def load_stopword(self, path):
        stopword = set()
        with open(path,'r',encoding='utf-8') as stopword_list:
            for sw in stopword_list:
                sw = sw.strip('\n')
                stopword.add(sw)
        return stopword

    def word_segment(self, sentence):
        words = jieba.cut_for_search(sentence)
        #clean up the stopword
        keyword = []
        for word in words:
            if word not in self.stopword:
                keyword.append(word)
        return keyword
    def word_segment_text_bank(self, sentence):
        words = pseg.cut(sentence)
        #clean up the stopword
        keyword = []
        for word,flag in words:
            if word not in self.stopword:
                keyword.append((word,flag))
        return keyword

    #意图匹配
    def smatch(self, _texts, keyword):
        keyword = self.word_segment(keyword)
        avg = 0.0
        avglen = 0.0
        keyerr = []
        avglen = 0
        for text,tf in _texts:
            for word in keyword:
                try:
                    sim = self.model.wv.similarity(text, word)
                    if sim > 0.38:
                        avg += sim
                        if 'm' in tf or 'q' in tf:
                            continue
                        else:
                            _texts.remove((text,tf))
                            avglen += 1
                except KeyError:
                    keyerr.append(text)
                    continue
        if len(keyerr) > 0:
            for k in keyerr:
                for t in k:
                    for word in keyword:
                        try:
                            sim = self.model.wv.similarity(t, word)
                            print(t,word,sim)
                            if sim >= 0.3:
                                avg += sim
                                avglen += 1
                                if (k,tf) in _texts:
                                    _texts.remove((k,tf))
                        except KeyError:
                            continue
        
        if avg > 0:
            if avg/avglen > 0.38:
                return True, _texts
        return False, _texts

    def match(self, texts, keyword, wanted):
        avg = 0.0
        avglen = 0
            # pre process
        ndict = {}
        andict = {}
        for i, (text,tf) in enumerate(texts):
            if tf == 'a':
                #删掉形容词。避免影响结果
                texts.remove((text,tf))
                continue
            for word,wf in keyword:
                try:
                    sim = self.model.wv.similarity(text, word)
                    if sim >= 0.25:
                        avg += sim
                        if 'n' in tf and 'n' in wf and wanted == word:
                            if texts[i-1] in texts:
                                n,f = texts[i-1]
                                if 'm' in f or 'q' in f:
                                    ndict[text] = ChineseNumConvert(n[:-1])
                                else:
                                    ndict[text] = 1 
                            else:
                                ndict[text] = 1  
                except KeyError:
                    continue
        for i, (text,tf) in enumerate(texts):
            if 'n' in tf and text not in ndict:
                if texts[i-1] in texts:
                    n,f = texts[i-1]
                    if 'm' in f or 'q' in f:
                        andict[text] = ChineseNumConvert(n[:-1])
                    else:
                        andict[text] = 1
                else:
                    andict[text] = 1
            if 'm' in tf or 'q' in tf:
                if len(texts) <= i+1:
                    andict["_pic"] = ChineseNumConvert(text[:-1])
                else:
                    _,f = texts[i+1]
                    if 'n' not in f:
                        andict["_pic"] = ChineseNumConvert(text[:-1])
        avglen = len(ndict)
        if avg > 0:
            if avg/avglen > 0.3:
                return True, ndict, andict
        return False, ndict, andict

