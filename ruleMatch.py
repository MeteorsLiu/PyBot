"""
原作者：zake7749
修改人：MeteorLiu

为方便对接修改了部分接口

开源协议：AGPL-3.0 请注意遵守AGPL-3.0

"""

from __future__ import unicode_literals

import jieba
import jieba.posseg as pseg
from gensim import models
import math
import re



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
        jieba_dic="jieba_dict/dict.txt.big"
        jieba_user_dic="jieba_dict/userdict.txt"
        self.init_jieba(jieba_dic, jieba_user_dic)
        jieba.enable_parallel(2)
        jieba.enable_paddle()
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
        #jieba.enable_parallel(2)
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
        words = jieba.cut(sentence, HMM=False)
        #clean up the stopword
        keyword = []
        for word in words:
            if word not in self.stopword:
                keyword.append(word)
        return keyword
    def word_segment_text_bank(self, sentence):
        words = pseg.cut(sentence, HMM=False, use_paddle=True)
        #clean up the stopword
        keyword = []
        for word,flag in words:
            if word not in self.stopword:
                keyword.append((word,flag))
        return keyword
    def word_segment_text_bank_no_paddle(self, sentence):
        words = pseg.cut(sentence, HMM=False, use_paddle=False)
        #clean up the stopword
        keyword = []
        for word,flag in words:
            if word not in self.stopword:
                keyword.append((word,flag))
        return keyword
    def get_sim(self, avg, sentence, keyword):
  
        sim = math.exp(self.model.wv.n_similarity(sentence, keyword))
        print('句子相似值: {} 综合关键词命中值: {}'.format(sim, avg))
        dis = self.model.wv.wmdistance(sentence, keyword)
        if dis == 1:
            dis = 0.1
        dis = 1.0 / math.log(dis)
        print('WMD算法估值: {}'.format(dis))
        if dis <= 0:
            dis = 10
        return math.log10(((sim+avg)/2)*dis)
    #意图匹配
    def smatch(self, _texts, keyword):
        if not isinstance(keyword, list):
            keyword = self.word_segment(keyword)
        textCopy = [t for t, f in _texts if 'eng' not in f and 'PER' not in f and 'x' not in f and 'LOC' not in f and 'ORG' not in f]
        avg = 0.0
        avglen = 0
        keyerr = []
        avglen = 0
        for i,(text,tf) in enumerate(_texts):
            for word in keyword:
                try:
                    sim = self.model.wv.similarity(text, word)
                    if sim >= 0.35:
                        print('{} 命中关键词 {}'.format(text, word))
                        """
                        if 'n' in tf or 'PER' in tf or 'x'  in tf or 'LOC' in tf or 'ORG'  in tf:
                            try:
                                w, f = _texts[i-1]
                                if 'm' not in f and 'q' not in f:
                                    #非法名词
                                    if (text,tf) in _texts:
                                        _texts.remove((text,tf))
                                        continue
                            except:
                                continue
                        """
                        if 'm' in tf or 'q' in tf:
                            if len(_texts)+1 < len(_texts):
                                w, f = _texts[i+1]
                                if 'n' not in f and 'PER' not in f and 'x' not in f and 'LOC' not in f and 'ORG' not in f:
                                    #量词后面可能是名词
                                    _texts[i+1] = (w,'n')
                            continue
                        else:
                            if (text,tf) in _texts:
                                avg += sim
                                _texts.remove((text,tf))
                                avglen += 1
                except:
                    keyerr.append(text)
                    continue
        
        if len(keyerr) > 0:
            for k in keyerr:
                for t in k:
                    for word in keyword:
                        try:
                            sim = self.model.wv.similarity(t, word)
                            if sim >= 0.33:
                                avg += sim
                                avglen += 1
                                if (k,tf) in _texts:
                                    print(k,sim)
                                    _texts.remove((k,tf))
                        except:
                            continue
        if avglen == 0:
            avglen = 1
        if len(textCopy) == 0:
            if avg/float(avglen) >= 0.36:
                return True, _texts
        else:
            rs = self.get_sim(avg/float(avglen), textCopy, keyword)
            print("综合估值: {}".format(rs))
            if rs >= 0.7:
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
                        if ('n' in tf and 'n' in wf or 'x' in tf or 'PER' in tf or 'LOC' in tf or 'ORG' in tf) and wanted == word:
                            if texts[i-1] in texts:
                                n,f = texts[i-1]
                                if 'm' in f or 'q' in f:
                                    if len(n) > 1:
                                        ndict[text] = ChineseNumConvert(n[:-1])
                                    else:
                                        ndict[text] = 1
                                elif 'eng' in f and n.isdigit():
                                    if int(n) > 10:
                                        ndict[text] = 10
                                    else:
                                        ndict[text] = int(n)
                            else:
                                ndict[text] = 1
                                    
                except KeyError:
                    continue
        
        for i, (text,tf) in enumerate(texts):
            if text not in ndict:
                if 'n' in tf or 'PER' in tf or 'LOC' in tf or 'ORG' in tf:
                    if texts[i-1] in texts:
                        n,f = texts[i-1]
                        if 'm' in f or 'q' in f:
                            if len(n) > 1:
                                andict[text] = ChineseNumConvert(n[:-1])
                            else:
                                andict[text] = 1
                        elif 'eng' in f and n.isdigit():
                            if int(n) > 10:
                                andict[text] = 10
                            else:
                                andict[text] = int(n)
                    else:
                        andict[text] = 1
                if 'x' in tf:
                    avg += 0.35
                    if texts[i-1] in texts:
                        n,f = texts[i-1]
                        if 'm' in f or 'q' in f:
                            if len(n) > 1:
                                ndict[text] = ChineseNumConvert(n[:-1])
                            else:
                                ndict[text]  = 1
                        elif 'eng' in f and n.isdigit():
                            if int(n) > 10:
                                ndict[text] = 10
                            else:
                                ndict[text] = int(n)
                    else:
                        ndict[text] = 1
            if 'm' in tf or 'q' in tf:
                if len(texts) <= i+1:
                    if len(text) > 1:
                        andict["_pic"] = ChineseNumConvert(text[:-1])
                    else:
                        andict["_pic"] = 1
                else:
                    _,f = texts[i+1]
                    if 'n' not in f and 'x' not in f and 'PER' not in f and 'LOC' not in tf and 'ORG' not in tf:
                        if len(text) > 1:
                            andict["_pic"] = ChineseNumConvert(text[:-1])
                        else:
                            andict["_pic"] = 1
        avglen = len(ndict)
        if avg > 0:
            if avg/float(avglen) >= 0.3:
                return True, ndict, andict
        return False, ndict, andict


