# coding=utf-8

import requests
import threading
import pandas as pd
import time
from queue import Queue
from lxml import etree
from matplotlib import font_manager, use
use('Agg')
from matplotlib import pyplot as plt


class DouyuSpider:
    def __init__(self):
        self.headers = {
            "user-agent":"Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.3", }
        self.Index = "https://www.douyu.com/directory/all"
        self.module_queue = Queue()
        self.module_content_queue = Queue()
        self.module_th_queue = Queue()
        self.main_info_queue = Queue()
        self.plot_info_queue = Queue()

    def parse_url(self, url):
        response = requests.get(url, headers=self.headers)
        return response.content.decode()

    def get_module(self, index_html):
        html = etree.HTML(index_html)
        module_list = html.xpath('''//a[@class="Aside-menu-item"]''')
        for temp in module_list:
            self.module_queue.put(temp)
        print(len(module_list))

    def get_module_content(self):
        while True:
            temp = []
            module = self.module_queue.get()
            title = module.xpath('''./@title''')[0] if len(module.xpath('''./@title''')) > 0 else None
            href = module.xpath('''./@href''')[0] if len(module.xpath('''./@href''')) > 0 else None
            temp.append(title)
            temp.append(href)
            self.module_content_queue.put(temp)
            self.module_queue.task_done()

    def parse_module(self):
        while True:
            module_content = self.module_content_queue.get()
            module_title = module_content[0]
            module_href = "https://www.douyu.com/" + module_content[1]
            ret = self.parse_url(module_href)
            module = {}
            module["title"] = module_title
            module["content"] = ret
            self.module_th_queue.put(module)
            self.module_content_queue.task_done()

    def get_main_info(self):
        while True:
            th = self.module_th_queue.get()
            th_title = th["title"]
            th_str = th["content"]
            html = etree.HTML(th_str)
            div_list = html.xpath('''//div[@class="DyListCover-info"]''')
            name_list = []
            hot_list = []
            for temp in div_list:
                name = temp.xpath('''./h2[@class="DyListCover-user is-template"]//text()''')
                name = name[0] if len(name) > 0 else None
                name_list.append(name)

                hot = temp.xpath('''./span[@class="DyListCover-hot is-template"]/text()''')
                hot = hot[0] if len(hot) > 0 else "0"
                if hot.count('万'):
                    hot = float(hot[0:-1]) * 10000
                    hot_list.append(hot)
                else:
                    hot_list.append(int(hot))
            info = {}
            info["title"] = th_title
            info["name_list"] = name_list
            info["hot_list"] = hot_list
            self.main_info_queue.put(info)
            self.module_th_queue.task_done()

    def deal_info(self):
        while True:
            info_list = self.main_info_queue.get()
            name_list = info_list["name_list"]
            hot_list = info_list["hot_list"]
            title = info_list["title"]
            df = pd.DataFrame({"name": name_list, "hot": hot_list})
            df = df[df["hot"] != 0]
            df = df.set_index("name")
            df = df.sort_values(by="hot", ascending=False)
            df = df.head(20)
            x = df.index
            y = df.values
            y = y.reshape(len(x))
            plot_info = {}
            plot_info["x"] = x
            plot_info["y"] = y
            plot_info["title"] = title
            self.plot_info_queue.put(plot_info)
            self.main_info_queue.task_done()

    def plot_and_save(self):
        i = 1
        while True:
            plot_info = self.plot_info_queue.get()
            t = plot_info["title"]
            x = plot_info["x"]
            y = plot_info["y"]

            plt.figure(figsize=(20, 8), dpi=80)
            my_font1 = font_manager.FontProperties(fname='C:\Windows\Fonts\msyh.ttc', size=18)
            my_font2 = font_manager.FontProperties(fname='C:\Windows\Fonts\msyh.ttc', size=10)
            plt.xlabel('主播名称', fontproperties=my_font1)
            plt.ylabel('主播热度', fontproperties=my_font1)
            plt.grid(alpha=0.3)

            plt.bar(range(len(x)), y, width=0.5, color="orange")
            _x = range(len(x))
            _xticks_label = [i for i in x]
            plt.xticks(_x, _xticks_label, fontproperties=my_font2, rotation=20)
            time_list = list(time.localtime())[3:6]
            time_str = str(time_list[0]) + ":" + str(time_list[1]) + ":" + str(time_list[2])
            plt.title("斗鱼：{}区主播热度排行榜--{}".format(t, time_str), fontproperties=my_font1)
            file_name = "./douyu/斗鱼{}区-热度排行榜.png".format(t)
            plt.savefig(file_name)
            print(t, i)
            i += 1
            self.plot_info_queue.task_done()

    def run(self):
        # 1.向主页发送请求获取响应
        index_html = self.parse_url(self.Index)
        # 2.获取模块的名称和地址
        self.get_module(index_html)

        t_list = []
        for i in range(2):
            t_1 = threading.Thread(target=self.get_module_content)
            t_list.append(t_1)
        # 3.向每个模块发送响应
        for i in range(10):
            t_2 = threading.Thread(target=self.parse_module)
            t_list.append(t_2)
        # 4.提取主要信息
        for i in range(5):
            t_3 = threading.Thread(target=self.get_main_info)
            t_list.append(t_3)
        # 5.进行数据处理
        for i in range(5):
            t_4 = threading.Thread(target=self.deal_info)
            t_list.append(t_4)
        # 6.进行绘图并保存图片
        t_5 = threading.Thread(target=self.plot_and_save)
        t_list.append(t_5)

        for t in t_list:
            t.setDaemon(True)
            t.start()

        for q in [self.module_queue, self.module_content_queue, self.module_th_queue, self.main_info_queue,
                  self.plot_info_queue]:
            q.join()


if __name__ == "__main__":
    t1 = time.time()
    new_module = DouyuSpider()
    new_module.run()
    t2 = time.time()
    print("花费{}s".format(t2 - t1))
