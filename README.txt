###后端

先在.env里写入API KEY。

在backend/data/platforms.json里可以增减API平台。

在backend\crawlers\feeds.json里可以增减新闻平台RSS。

然后运行backend/main.py。

###前端

先运行backend/api_server.py启动数据库，

再在另一个终端输入：
cd frontend
npm run dev


详情请看docs
