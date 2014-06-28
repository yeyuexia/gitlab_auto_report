#简介
估计没有多少程序员愿意写日报，周报吧？但是在一些公司制度下，日报，周报是必须的。

于是这个项目的目的就是让你从痛苦的写日报/周报中解放出来。
#注意
该项目目前仅限gitlab能使用
#使用方式
安装依赖，在config.py文件里定义自己要连接的gitlab地址，执行下面代码：
```
from gather import Gitlab, stat
git = Gitlab(token)
stat(git.get_contribute_details(git.user, git.email, datetime)
```
就会打印出一份从datetime到现在的报表，方便提交日报, 周报用
#一些细节
其实脚本只是负责采集了每个人在gitlab中的一些操作，然后格式化打印出来。目前还有很多地方需要改进，感谢大家支持。：）
