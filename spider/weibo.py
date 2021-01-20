#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import codecs
import copy
import json
import logging
import logging.config
import math
import os
import random
import sys
import re
import warnings
from collections import OrderedDict
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from time import sleep

import requests
from lxml import etree
from requests.adapters import HTTPAdapter
from tqdm import tqdm

warnings.filterwarnings("ignore")

logging_path = os.path.split(
    os.path.realpath(__file__))[0] + os.sep + 'logging.conf'
logging.config.fileConfig(logging_path)
logger = logging.getLogger('weibo')
config_path = os.path.split(
    os.path.realpath(__file__))[0] + os.sep + 'config.json'


class Weibo(object):
    def __init__(self, config):
        """Weibo类初始化"""
        self.validate_config(config)
        self.filter = config[
            'filter']  # 取值范围为0、1,程序默认值为0,代表要爬取用户的全部微博,1代表只爬取用户的原创微博
        since_date = config['since_date']
        if isinstance(since_date, int):
            since_date = date.today() - timedelta(since_date)
        since_date = str(since_date)
        self.since_date = since_date  # 起始时间，即爬取发布日期从该值到现在的微博，形式为yyyy-mm-dd
        self.write_mode = config[
            'write_mode']  # 结果信息保存类型，为list形式
        cookie = config.get('cookie')  # 微博cookie，可填可不填
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36'
        self.headers = {'User_Agent': user_agent, 'Cookie': cookie}
        user_id_list = config['user_id_list']
        user_config_list = [{
            'user_id': user_id,
            'since_date': self.since_date
        } for user_id in user_id_list]
        self.user_config_list = user_config_list  # 要爬取的微博用户的user_config列表
        self.user_config = {}  # 用户配置,包含用户id和since_date
        self.start_date = ''  # 获取用户第一条微博时的日期
        self.user = {}  # 存储目标微博用户信息
        self.got_count = 0  # 存储爬取到的微博数
        self.weibo = []  # 存储爬取到的所有微博信息
        self.weibo_id_list = []  # 存储爬取到的所有微博id
        self.date_set = set([]) # 存储爬取到的日期

    def validate_config(self, config):
        """验证配置是否正确"""

        # 验证filter
        argument_list = [
            'filter',
        ]
        for argument in argument_list:
            if config[argument] != 0 and config[argument] != 1:
                logger.warning(u'%s值应为0或1,请重新输入', config[argument])
                sys.exit()

        # 验证since_date
        since_date = config['since_date']
        if (not self.is_date(str(since_date))) and (not isinstance(
                since_date, int)):
            logger.warning(u'since_date值应为yyyy-mm-dd形式或整数,请重新输入')
            sys.exit()

        # 验证write_mode
        write_mode = ['json']
        if not isinstance(config['write_mode'], list):
            sys.exit(u'write_mode值应为list类型')
        for mode in config['write_mode']:
            if mode not in write_mode:
                logger.warning(
                    u'%s为无效模式，write_mode应为json',
                    mode)
                sys.exit()

        # 验证user_id_list
        user_id_list = config['user_id_list']
        if (not isinstance(user_id_list,
                           list)) and (not user_id_list.endswith('.txt')):
            logger.warning(u'user_id_list值应为list类型或txt文件路径')
            sys.exit()
        if not isinstance(user_id_list, list):
            if not os.path.isabs(user_id_list):
                user_id_list = os.path.split(
                    os.path.realpath(__file__))[0] + os.sep + user_id_list
            if not os.path.isfile(user_id_list):
                logger.warning(u'不存在%s文件', user_id_list)
                sys.exit()

    def is_date(self, since_date):
        """判断日期格式是否正确"""
        try:
            datetime.strptime(since_date, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    def get_json(self, params):
        """获取网页中json数据"""
        url = 'https://m.weibo.cn/api/container/getIndex?'
        r = requests.get(url,
                         params=params,
                         headers=self.headers,
                         verify=False)
        return r.json()

    def get_weibo_json(self, page):
        """获取网页中微博json数据"""
        params = {
            'containerid': '107603' + str(self.user_config['user_id']),
            'page': page
        }
        js = self.get_json(params)
        return js

    def get_user_info(self):
        """获取用户信息"""
        params = {'containerid': '100505' + str(self.user_config['user_id'])}
        js = self.get_json(params)
        if js['ok']:
            info = js['data']['userInfo']
            user_info = OrderedDict()
            user_info['id'] = self.user_config['user_id']
            user_info['screen_name'] = info.get('screen_name', '')
            user_info['gender'] = info.get('gender', '')
            params = {
                'containerid':
                '230283' + str(self.user_config['user_id']) + '_-_INFO'
            }
            zh_list = [
                u'生日', u'所在地', u'小学', u'初中', u'高中', u'大学', u'公司', u'注册时间',
                u'阳光信用'
            ]
            en_list = [
                'birthday', 'location', 'education', 'education', 'education',
                'education', 'company', 'registration_time', 'sunshine'
            ]
            for i in en_list:
                user_info[i] = ''
            js = self.get_json(params)
            if js['ok']:
                cards = js['data']['cards']
                if isinstance(cards, list) and len(cards) > 1:
                    card_list = cards[0]['card_group'] + cards[1]['card_group']
                    for card in card_list:
                        if card.get('item_name') in zh_list:
                            user_info[en_list[zh_list.index(
                                card.get('item_name'))]] = card.get(
                                    'item_content', '')
            user_info['statuses_count'] = info.get('statuses_count', 0)
            user_info['followers_count'] = info.get('followers_count', 0)
            user_info['follow_count'] = info.get('follow_count', 0)
            user_info['description'] = info.get('description', '')
            user_info['profile_url'] = info.get('profile_url', '')
            user_info['profile_image_url'] = info.get('profile_image_url', '')
            user_info['avatar_hd'] = info.get('avatar_hd', '')
            user_info['urank'] = info.get('urank', 0)
            user_info['mbrank'] = info.get('mbrank', 0)
            user_info['verified'] = info.get('verified', False)
            user_info['verified_type'] = info.get('verified_type', -1)
            user_info['verified_reason'] = info.get('verified_reason', '')
            user = self.standardize_info(user_info)
            self.user = user
            return user

    def get_long_weibo(self, id):
        """获取长微博"""
        for i in range(5):
            url = 'https://m.weibo.cn/detail/%s' % id
            html = requests.get(url, headers=self.headers, verify=False).text
            html = html[html.find('"status":'):]
            html = html[:html.rfind('"hotScheme"')]
            html = html[:html.rfind(',')]
            html = '{' + html + '}'
            js = json.loads(html, strict=False)
            weibo_info = js.get('status')
            if weibo_info:
                weibo = self.parse_weibo(weibo_info)
                return weibo
            sleep(random.randint(6, 10))

    def get_pics(self, weibo_info):
        """获取微博原始图片url"""
        if weibo_info.get('pics'):
            pic_info = weibo_info['pics']
            pic_list = [pic['large']['url'] for pic in pic_info]
            pics = ','.join(pic_list)
        else:
            pics = ''
        return pics

    def get_live_photo(self, weibo_info):
        """获取live photo中的视频url"""
        live_photo_list = []
        live_photo = weibo_info.get('pic_video')
        if live_photo:
            prefix = 'https://video.weibo.com/media/play?livephoto=//us.sinaimg.cn/'
            for i in live_photo.split(','):
                if len(i.split(':')) == 2:
                    url = prefix + i.split(':')[1] + '.mov'
                    live_photo_list.append(url)
            return live_photo_list

    def get_video_url(self, weibo_info):
        """获取微博视频url"""
        video_url = ''
        video_url_list = []
        if weibo_info.get('page_info'):
            if weibo_info['page_info'].get('media_info') and weibo_info[
                    'page_info'].get('type') == 'video':
                media_info = weibo_info['page_info']['media_info']
                video_url = media_info.get('mp4_720p_mp4')
                if not video_url:
                    video_url = media_info.get('mp4_hd_url')
                    if not video_url:
                        video_url = media_info.get('mp4_sd_url')
                        if not video_url:
                            video_url = media_info.get('stream_url_hd')
                            if not video_url:
                                video_url = media_info.get('stream_url')
        if video_url:
            video_url_list.append(video_url)
        live_photo_list = self.get_live_photo(weibo_info)
        if live_photo_list:
            video_url_list += live_photo_list
        return ';'.join(video_url_list)

    def get_location(self, selector):
        """获取微博发布位置"""
        location_icon = 'timeline_card_small_location_default.png'
        span_list = selector.xpath('//span')
        location = ''
        for i, span in enumerate(span_list):
            if span.xpath('img/@src'):
                if location_icon in span.xpath('img/@src')[0]:
                    location = span_list[i + 1].xpath('string(.)')
                    break
        return location

    def get_article_url(self, selector):
        """获取微博中头条文章的url"""
        article_url = ''
        text = selector.xpath('string(.)')
        if text.startswith(u'发布了头条文章'):
            url = selector.xpath('//a/@data-url')
            if url and url[0].startswith('http://t.cn'):
                article_url = url[0]
        return article_url

    def get_topics(self, selector):
        """获取参与的微博话题"""
        span_list = selector.xpath("//span[@class='surl-text']")
        topics = ''
        topic_list = []
        for span in span_list:
            text = span.xpath('string(.)')
            if len(text) > 2 and text[0] == '#' and text[-1] == '#':
                topic_list.append(text[1:-1])
        if topic_list:
            topics = ','.join(topic_list)
        return topics

    def get_at_users(self, selector):
        """获取@用户"""
        a_list = selector.xpath('//a')
        at_users = ''
        at_list = []
        for a in a_list:
            if '@' + a.xpath('@href')[0][3:] == a.xpath('string(.)'):
                at_list.append(a.xpath('string(.)')[1:])
        if at_list:
            at_users = ','.join(at_list)
        return at_users

    def string_to_int(self, string):
        """字符串转换为整数"""
        if isinstance(string, int):
            return string
        elif string.endswith(u'万+'):
            string = int(string[:-2] + '0000')
        elif string.endswith(u'万'):
            string = int(string[:-1] + '0000')
        return int(string)

    def standardize_date(self, created_at):
        """标准化微博发布时间"""
        if u'刚刚' in created_at:
            created_at = datetime.now().strftime('%Y-%m-%d')
        elif u'分钟' in created_at:
            minute = created_at[:created_at.find(u'分钟')]
            minute = timedelta(minutes=int(minute))
            created_at = (datetime.now() - minute).strftime('%Y-%m-%d')
        elif u'小时' in created_at:
            hour = created_at[:created_at.find(u'小时')]
            hour = timedelta(hours=int(hour))
            created_at = (datetime.now() - hour).strftime('%Y-%m-%d')
        elif u'昨天' in created_at:
            day = timedelta(days=1)
            created_at = (datetime.now() - day).strftime('%Y-%m-%d')
        else:
            created_at = created_at.replace('+0800 ', '')
            temp = datetime.strptime(created_at, '%c')
            created_at = datetime.strftime(temp, '%Y-%m-%d')
        return created_at

    def standardize_info(self, weibo):
        """标准化信息，去除乱码"""
        for k, v in weibo.items():
            if 'bool' not in str(type(v)) and 'int' not in str(
                    type(v)) and 'list' not in str(
                        type(v)) and 'long' not in str(type(v)):
                weibo[k] = v.replace(u'\u200b', '').encode(
                    sys.stdout.encoding, 'ignore').decode(sys.stdout.encoding)
        return weibo

    def parse_weibo(self, weibo_info):
        weibo = OrderedDict()
        text_body = weibo_info['text']
        selector = etree.HTML(text_body)
        weibo['text'] = etree.HTML(text_body).xpath('string(.)')
        if weibo_info['user']:
            weibo['user_id'] = weibo_info['user']['id']
            weibo['screen_name'] = weibo_info['user']['screen_name']
        else:
            weibo['user_id'] = ''
            weibo['screen_name'] = ''
        weibo['id'] = int(weibo_info['id'])
        weibo['bid'] = weibo_info['bid']
        weibo['article_url'] = self.get_article_url(selector)
        weibo['pics'] = self.get_pics(weibo_info)
        weibo['video_url'] = self.get_video_url(weibo_info)
        weibo['location'] = self.get_location(selector)
        weibo['created_at'] = weibo_info['created_at']
        weibo['source'] = weibo_info['source']
        weibo['attitudes_count'] = self.string_to_int(
            weibo_info.get('attitudes_count', 0))
        weibo['comments_count'] = self.string_to_int(
            weibo_info.get('comments_count', 0))
        weibo['reposts_count'] = self.string_to_int(
            weibo_info.get('reposts_count', 0))
        weibo['topics'] = self.get_topics(selector)
        weibo['at_users'] = self.get_at_users(selector)
        return self.standardize_info(weibo)

    def get_history_date(self, weibo):
        """
        找出微博中的历史日期，规则如下：
        1、优先匹配出以日期(如：1931年10月1日)开头的微博
        2、如果发博日期为2020.09.02及之前，则发博日期减75
        3、如果发博日期为2020.09.02之后，则发博日期减89
        """
        # 发博时间
        created_at = datetime.strptime(weibo['created_at'], '%Y-%m-%d')
        # 临界时间
        temp_date = datetime.strptime('2020-09-02', '%Y-%m-%d')
        isBefore = created_at > temp_date
        match = re.match(r'(\d{4}年\d{1,2}月\d{1,2}日)', weibo['text'])
        if not match:
            years = 89 if isBefore else 75
            weibo['history_date'] = (
                created_at - relativedelta(years=years)).strftime('%Y年%m月%d日')
        else:
            try:
                weibo['history_date'] = datetime.strptime(
                    match.group(0), '%Y年%m月%d日').strftime('%Y年%m月%d日')
            except:
                years = 89 if isBefore else 75
                weibo['history_date'] = (
                    created_at - relativedelta(years=years)).strftime('%Y年%m月%d日')
        """
        type：
        0、抗日
        1、918
        """
        weibo['type'] = 1 if isBefore else 0
        return weibo

    def print_user_info(self):
        """打印用户信息"""
        logger.info('+' * 100)
        logger.info(u'用户信息')
        logger.info(u'用户id：%s', self.user['id'])
        logger.info(u'用户昵称：%s', self.user['screen_name'])
        gender = u'女' if self.user['gender'] == 'f' else u'男'
        logger.info(u'性别：%s', gender)
        logger.info(u'生日：%s', self.user['birthday'])
        logger.info(u'所在地：%s', self.user['location'])
        logger.info(u'教育经历：%s', self.user['education'])
        logger.info(u'公司：%s', self.user['company'])
        logger.info(u'阳光信用：%s', self.user['sunshine'])
        logger.info(u'注册时间：%s', self.user['registration_time'])
        logger.info(u'微博数：%d', self.user['statuses_count'])
        logger.info(u'粉丝数：%d', self.user['followers_count'])
        logger.info(u'关注数：%d', self.user['follow_count'])
        logger.info(u'url：https://m.weibo.cn/profile/%s', self.user['id'])
        if self.user.get('verified_reason'):
            logger.info(self.user['verified_reason'])
        logger.info(self.user['description'])
        logger.info('+' * 100)

    def print_one_weibo(self, weibo):
        """打印一条微博"""
        try:
            logger.info(u'微博id：%d', weibo['id'])
            logger.info(u'微博正文：%s', weibo['text'])
            logger.info(u'原始图片url：%s', weibo['pics'])
            logger.info(u'微博位置：%s', weibo['location'])
            logger.info(u'发布时间：%s', weibo['created_at'])
            logger.info(u'历史时间：%s', weibo['history_date'])
            logger.info(u'发布工具：%s', weibo['source'])
            logger.info(u'点赞数：%d', weibo['attitudes_count'])
            logger.info(u'评论数：%d', weibo['comments_count'])
            logger.info(u'转发数：%d', weibo['reposts_count'])
            logger.info(u'话题：%s', weibo['topics'])
            logger.info(u'@用户：%s', weibo['at_users'])
            logger.info(u'url：https://m.weibo.cn/detail/%d', weibo['id'])
        except OSError:
            pass

    def print_weibo(self, weibo):
        """打印微博，若为转发微博，会同时打印原创和转发部分"""
        if weibo.get('retweet'):
            logger.info('*' * 100)
            logger.info(u'转发部分：')
            self.print_one_weibo(weibo['retweet'])
            logger.info('*' * 100)
            logger.info(u'原创部分：')
        self.print_one_weibo(weibo)
        logger.info('-' * 120)

    def get_one_weibo(self, info):
        """获取一条微博的全部信息"""
        try:
            weibo_info = info['mblog']
            weibo_id = weibo_info['id']
            retweeted_status = weibo_info.get('retweeted_status')
            is_long = weibo_info.get('isLongText')
            if retweeted_status and retweeted_status.get('id'):  # 转发
                retweet_id = retweeted_status.get('id')
                is_long_retweet = retweeted_status.get('isLongText')
                if is_long:
                    weibo = self.get_long_weibo(weibo_id)
                    if not weibo:
                        weibo = self.parse_weibo(weibo_info)
                else:
                    weibo = self.parse_weibo(weibo_info)
                if is_long_retweet:
                    retweet = self.get_long_weibo(retweet_id)
                    if not retweet:
                        retweet = self.parse_weibo(retweeted_status)
                else:
                    retweet = self.parse_weibo(retweeted_status)
                retweet['created_at'] = self.standardize_date(
                    retweeted_status['created_at'])
                weibo['retweet'] = retweet
            else:  # 原创
                if is_long:
                    weibo = self.get_long_weibo(weibo_id)
                    if not weibo:
                        weibo = self.parse_weibo(weibo_info)
                else:
                    weibo = self.parse_weibo(weibo_info)
            if weibo:
                weibo['created_at'] = self.standardize_date(
                    weibo_info['created_at'])
                weibo = self.get_history_date(weibo)
            return weibo
        except Exception as e:
            logger.exception(e)

    def is_pinned_weibo(self, info):
        """判断微博是否为置顶微博"""
        weibo_info = info['mblog']
        title = weibo_info.get('title')
        if title and title.get('text') == u'置顶':
            return True
        else:
            return False

    def get_one_page(self, page):
        """获取一页的全部微博"""
        try:
            js = self.get_weibo_json(page)
            if js['ok']:
                weibos = js['data']['cards']
                for w in weibos:
                    if w['card_type'] == 9:
                        wb = self.get_one_weibo(w)
                        if wb:
                            if wb['id'] in self.weibo_id_list:
                                continue
                            created_at = datetime.strptime(
                                wb['created_at'], '%Y-%m-%d')
                            since_date = datetime.strptime(
                                self.user_config['since_date'], '%Y-%m-%d')
                            if created_at < since_date:
                                if self.is_pinned_weibo(w):
                                    continue
                                else:
                                    logger.info(u'{}已获取{}({})的第{}页微博{}'.format(
                                        '-' * 30, self.user['screen_name'],
                                        self.user['id'], page, '-' * 30))
                                    return True
                            if (not self.filter) or (
                                    'retweet' not in wb.keys()):
                                self.weibo.append(wb)
                                self.weibo_id_list.append(wb['id'])
                                self.got_count += 1
                                self.print_weibo(wb)
                            else:
                                logger.info(u'正在过滤转发微博')
            logger.info(u'{}已获取{}({})的第{}页微博{}'.format(
                '-' * 30, self.user['screen_name'], self.user['id'], page,
                '-' * 30))
        except Exception as e:
            logger.exception(e)

    def get_page_count(self):
        """获取微博页数"""
        try:
            weibo_count = self.user['statuses_count']
            page_count = int(math.ceil(weibo_count / 10.0))
            return page_count
        except KeyError:
            logger.exception(
                u'程序出错，错误原因可能为以下两者：\n'
                u'1.user_id不正确；\n'
                u'2.此用户微博可能需要设置cookie才能爬取。\n'
                u'解决方案：\n'
                u'请参考\n'
                u'https://github.com/dataabc/weibo-crawler#如何获取user_id\n'
                u'获取正确的user_id；\n'
                u'或者参考\n'
                u'https://github.com/dataabc/weibo-crawler#3程序设置\n'
                u'中的“设置cookie”部分设置cookie信息')

    def get_write_info(self, wrote_count):
        """获取要写入的微博信息"""
        write_info = []
        for w in self.weibo[wrote_count:]:
            wb = OrderedDict()
            for k, v in w.items():
                if k not in ['user_id', 'screen_name', 'retweet']:
                    if 'unicode' in str(type(v)):
                        v = v.encode('utf-8')
                    wb[k] = v
            if not self.filter:
                if w.get('retweet'):
                    wb['is_original'] = False
                    for k2, v2 in w['retweet'].items():
                        if 'unicode' in str(type(v2)):
                            v2 = v2.encode('utf-8')
                        wb['retweet_' + k2] = v2
                else:
                    wb['is_original'] = True
            write_info.append(wb)
        return write_info

    def get_filepath(self, type):
        """获取结果文件路径"""
        try:
            file_dir = os.path.abspath(
                os.path.dirname(os.path.dirname(__file__)))
            if type == 'json':
                file_dir = file_dir + os.path.sep + 'resources'
            if not os.path.isdir(file_dir):
                os.makedirs(file_dir)
            return file_dir
        except Exception as e:
            logger.exception(e)

    def get_posts_path(self):
        """获取文章路径"""
        return os.path.abspath(
            os.path.dirname(os.path.dirname(__file__))) + os.path.sep + 'site' + os.path.sep + 'source' + os.path.sep + '_posts'

    def write_json(self, wrote_count):
        """将爬到的信息写入json文件"""
        weibo_info = self.weibo[wrote_count:]
        path = self.get_filepath('json')
        for wb in weibo_info:
            history_date = wb['history_date']
            self.date_set.add(history_date)
            dir_path = path + os.path.sep + history_date
            if not os.path.isdir(dir_path):
                os.makedirs(dir_path)
            file_path = dir_path + os.path.sep + str(wb['id']) + '.json'
            with codecs.open(file_path, 'w', encoding='utf-8') as f:
                json.dump(wb, f, ensure_ascii=False, indent=4)
        logger.info(u'%d条微博写入json文件完毕,保存路径:', self.got_count)
        logger.info(path)

    def write_md(self):
        """按天分类将微博信息写入md文件"""
        resources_dir = self.get_filepath('json')
        if not os.path.isdir(resources_dir):
            return
        json_list = []
        for dir in self.date_set:
            json_list = []
            dir_path = os.path.join(resources_dir, dir)
            if not os.path.isdir(dir_path):
                continue
            files = os.listdir(dir_path)
            for file_name in files:
                file_path = os.path.join(dir_path, file_name)
                if os.path.isfile(file_path):
                    with codecs.open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        json_list.append(data)
            if len(json_list):
                self.write_md_data(dir, json_list)

    def write_md_data(self, title, list):
        post_dir = self.get_posts_path()
        if not os.path.isdir(post_dir):
            return

        wb = list[0]
        create_date = wb['created_at']
        categories = '全面抗战(1937-1945)' if wb['type'] == 0 else '局部抗战(1931-1937)'
        content = (
            f'---\n'
            f'layout: post\n'
            f'title: \"{title}\"\n'
            f'date: {create_date}\n'
            f'categories: {categories}\n'
            f'---\n\n'
            f'<meta name=\"referrer\" content=\"no-referrer\" />\n\n'
        )

        list.sort(key=lambda x: x['id'], reverse=True)
        for wb in list:
            text = '- ' + wb['text']
            pics = [x for x in wb['pics'].split(',') if x]
            if len(pics):
                text = text + '<br/>'
                for pic in pics:
                    text = text + ('<img src=\"%s\" />' % pic)
            text = text + '\n\n'
            content = content + text

        md_file_path = os.path.join(
            post_dir, ('%s.md' % (title)))
        with codecs.open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def write_data(self, wrote_count):
        """将爬到的信息写入文件"""
        if self.got_count > wrote_count:
            if 'json' in self.write_mode:
                self.write_json(wrote_count)

    def update_config(self):
        """获取config.json文件信息, 默认将since_date调整为两天前"""
        with codecs.open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            config['since_date'] = (
                datetime.now() - relativedelta(days=2)).strftime('%Y-%m-%d')
        with codecs.open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    def get_pages(self):
        """获取全部微博"""
        try:
            self.get_user_info()
            self.print_user_info()
            since_date = datetime.strptime(self.user_config['since_date'],
                                           '%Y-%m-%d')
            today = datetime.strptime(str(date.today()), '%Y-%m-%d')
            if since_date <= today:
                page_count = self.get_page_count()
                wrote_count = 0
                page1 = 0
                random_pages = random.randint(2, 5)
                self.start_date = datetime.now().strftime('%Y-%m-%d')
                for page in tqdm(range(1, page_count + 1), desc='Progress'):
                    is_end = self.get_one_page(page)
                    if is_end:
                        break

                    if page % 20 == 0:  # 每爬20页写入一次文件
                        self.write_data(wrote_count)
                        wrote_count = self.got_count

                    # 通过加入随机等待避免被限制。爬虫速度过快容易被系统限制(一段时间后限
                    # 制会自动解除)，加入随机等待模拟人的操作，可降低被系统限制的风险。默
                    # 认是每爬取2到5页随机等待6到10秒，如果仍然被限，可适当增加sleep时间
                    if (page -
                            page1) % random_pages == 0 and page < page_count:
                        sleep(random.randint(6, 10))
                        page1 = page
                        random_pages = random.randint(2, 5)

                self.write_data(wrote_count)  # 将剩余不足20页的微博写入文件
            logger.info(u'微博爬取完成，共爬取%d条微博', self.got_count)
        except Exception as e:
            logger.exception(e)

    def initialize_info(self, user_config):
        """初始化爬虫信息"""
        self.weibo = []
        self.user = {}
        self.user_config = user_config
        self.got_count = 0
        self.weibo_id_list = []
        self.date_set = set([])

    def start(self):
        """运行爬虫"""
        try:
            for user_config in self.user_config_list:
                self.initialize_info(user_config)
                self.get_pages()
                self.write_md()
                self.update_config()
                logger.info(u'信息抓取完毕')
                logger.info('*' * 100)
        except Exception as e:
            logger.exception(e)


def get_config():
    """获取config.json文件信息"""
    if not os.path.isfile(config_path):
        logger.warning(u'当前路径：%s 不存在配置文件config.json',
                       (os.path.split(os.path.realpath(__file__))[0] + os.sep))
        sys.exit()
    try:
        with open(config_path) as f:
            config = json.loads(f.read())
            return config
    except ValueError:
        logger.error(u'config.json 格式不正确，请参考 '
                     u'https://github.com/dataabc/weibo-crawler#3程序设置')
        sys.exit()


def main():
    try:
        config = get_config()
        wb = Weibo(config)
        wb.start()  # 爬取微博信息
    except Exception as e:
        logger.exception(e)


if __name__ == '__main__':
    main()
