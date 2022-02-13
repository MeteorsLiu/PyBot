# PyBot


ATRI是一只基于word2vec指令匹配，用seq2seq聊天的，以及对接多方NLP平台智能ai聊天机器人

本项目和 [ATRI](https://github.com/Kyomotoi/ATRI) 无关， 本项目更多的仅为测试，尝试，学习用途，代码写的非常乱，并不是一个可以直接拿来用的项目

关于ATRI，这个名字是由我同学提出的，我和另一个ATRI项目几乎同时开工，没有抄袭对方任何一行代码，本项目是独立项目

英文模型下载：

mkdir -p /home/clean_chat_corpus/pytorch-chatbot/save/model/movie_subtitles/1-1_512/

wget "https://www.space.ntu.edu.tw/webrelay/directdownload/Q8CwBIcCAlotFf7z/?dis=10014&fi=54113350" --no-check-certificate  -O /home/clean_chat_corpus/pytorch-chatbot/save/model/movie_subtitles/1-1_512/50000_backup_bidir_model.tar

不需要解压

wget "https://www.space.ntu.edu.tw/webrelay/directdownload/ijGa2fGe7MbFvals/?dis=10014&fi=54113355" --no-check-certificate  -O /home/clean_chat_corpus/pytorch-chatbot/movie.txt


# 基于Word2Vec匹配原理及相关算法

![Word2vec](https://github.com/MeteorsLiu/PyBot/raw/main/pics/MommyTalk1644679385634.jpg)

f(s) 既最终句子与关键词的分数，建议阈值 f(s) >= 0.7
