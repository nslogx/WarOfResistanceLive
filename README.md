# 抗战直播

**预览地址**：[https://nslog11.github.io/WarOfResistanceLive](https://nslog11.github.io/WarOfResistanceLive/)

**本项目数据来源**：[@抗战直播](https://weibo.com/kzzb)

![](./images/screen.jpg)

## 前言
在目前浮躁的互联网环境下，做一件好事不难，难的是连续8年做一件有意义的事。

在微博上有这样一位博主，从2012年7月7日开始，截至到2020年9月2日，[@抗战直播](https://weibo.com/kzzb) 以图文形式，记录了从**1937年7月7日至1945年8月15日**中华民族全面抗战的这段历史。**2980** 天，从未间断，平均每天 **12** 条，累计 **35214** 篇。

2020年9月18日7时零7分，沉寂了半个月的 [@抗战直播](https://weibo.com/kzzb) 恢复更新，他们将继续以图文的形式记录**1931年9月18日至1937年7月7日**这 `6` 年的抗战历史。

[@抗战直播](https://weibo.com/kzzb)：“我们直播抗战，并非为了鼓动仇恨等负面的情绪，而是想适度唤起遗忘，当我们时刻牢记祖辈们蒙受的苦难、恐惧和屈辱时；当我们体味祖辈们是如何在国家民族危亡之际抛弃前嫌，实现民族和解时，当我们目睹着祖辈们是如何从容慷慨的走向死亡，以身体为这个国家献祭之时，相信我们对于现实将有更加成熟和理性的思考。”

下一个 **6** 年，他们已经在路上。

## 介绍

``` yaml
├── .github/workflows # 工作流配置文件
├── resources # 微博数据
├── site # 博客源码
└── spider # 微博爬虫
```

本项目是一个主要由 `Python` 爬虫 + `Hexo` 博客 + `Github Actions`持续集成服务组成的开源项目，并且部署于 `Github Pages`。目前包含以下功能：

- 每日定时自动同步更新数据
- 查看博主目前所有的微博数据
- 支持`RSS`订阅功能
- 基于`Github Actions`的持续集成服务
- ...

## Python 爬虫

该项目使用的爬虫是基于 [weibo-crawler](https://github.com/dataabc/weibo-crawler) 项目的简化及修改实现(**仅供研究使用**)，感谢作者 [dataabc](https://github.com/dataabc)。

```python
def get_json(self, params):
        """获取网页中json数据"""
        url = 'https://m.weibo.cn/api/container/getIndex?'
        r = requests.get(url,
                         params=params,
                         headers=self.headers,
                         verify=False)
        return r.json()
```

安装依赖：

```shell
pip3 install -r requirements.txt
```

使用：
```shell
python weibo.py
```

更多内容可查看 [weibo-crawler](https://github.com/dataabc/weibo-crawler)。

## Hexo

`Hexo` 是一款基于 `Node.js` 的静态博客框架，依赖少易于安装使用，可以方便的生成静态网页托管在 `GitHub Pages` 上，还有丰富的主题可供挑选。关于如何安装使用 `Hexo` 可详细查看官方文档：[https://hexo.io/zh-cn/docs/](https://hexo.io/zh-cn/docs/)。

RSS订阅地址：

```
https://nslog11.github.io/WarOfResistanceLive/atom.xml
```

## Github Actions 持续集成

`Github Actions` 是由 `Github` 于 `2018年10月` 推出的持续集成服务，在此之前，我们可能更多的使用 `Travis CI` 来实现持续集成服务。以我个人的感觉来看，`Github Actions` 功能非常强大，比 `Travis CI` 的可玩性更高，`Github Actions` 拥有丰富的 `action` 市场，将这些 `action` 组合起来，我们就可以很简单的完成很多很有趣的事情。

该项目使用的 `Action` 有：

- [actions/checkout@v2](https://github.com/actions/checkout)

- [actions/setup-python@v2](https://github.com/actions/setup-python)

- [actions/setup-node@v1](https://github.com/actions/setup-node)

- [actions/cache@v2](https://github.com/actions/cache)

- [EndBug/add-and-commit@v5](https://github.com/EndBug/add-and-commit)

- [ad-m/github-push-action@master](https://github.com/ad-m/github-push-action)

- [peaceiris/actions-gh-pages@v3](https://github.com/peaceiris/actions-gh-pages)

`workflow` 详细配置可查看 [spider.yml](./.github/workflows/spider.yml)

更多关于 `Github Action` 的内容可查看 [官方文档](https://docs.github.com/cn/free-pro-team@latest/actions)

## 许可证

[LICENSE](./LICENSE)
