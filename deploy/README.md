# 生产部署参考（未执行）

目标：在已有服务器独立运行图库，不复用智能客服数据库、不开放 PostgreSQL 的公网端口。所有模板须结合服务器实际目录、用户和 OpenResty 配置审阅后使用。

## PostgreSQL

由 1Panel 或数据库管理员创建一个专用登录角色与空数据库 cloud_gallery，角色只拥有这个新库。密码不要写入仓库或聊天。无需 pgvector。不要把配置指向 robot_rag 或博客库。

将 production.env.example 的配置保存为 /etc/cloud-gallery.env，权限 0600，数据库 URL 中含特殊字符的密码要 URL 编码。设置 GALLERY_ENV=production 和 COOKIE_SECURE=true，填写实际站点 Origin。

用服务相同的环境变量运行：
```bash
python -m app.cli init-db
python -m app.cli create-user 你的用户名
```
账户创建会隐藏询问密码。命令需要从 backend 目录执行；可把同一份环境复制为 backend/.env（0600），执行后移除副本。生产 init-db 创建新表，不迁移已有表。首次上线前在独立测试库运行上传、权限和备份恢复检查。

## 前后端

后端放 /opt/cloud-gallery/backend，建立 venv，安装 requirements-lock.txt。创建不可登录的 cloud-gallery 服务用户，创建归其所有的 /var/lib/cloud-gallery/images。按照 cloud-gallery.service 安装服务，运行单 worker、最多 16 个并发连接、768 MiB 内存上限。CPUQuota=100% 表示最多使用一个逻辑 CPU。

前端从 frontend 构建：
```bash
VITE_BASE_PATH=/gallery/ npm run build
```
把 dist 内容复制到 /var/www/cloud-gallery/gallery/，将 openresty-gallery.conf 的两个 location 合入 gallery.example.com 的 HTTPS server。先备份现有配置，再 nginx -t，通过后 reload。不要覆盖整个站点配置。

公网只开放现有 HTTPS；FastAPI 绑定 127.0.0.1:8200，数据库保留本机访问。设置防火墙时先读取现状，避免影响已有博客。

如果 OpenResty 运行在 Docker 中，必须确认其网络模式。模板中的 127.0.0.1 只适用于它能访问宿主机回环端口的情况；桥接网络需要调整容器到 API 的连接方式，不能直接照抄地址，也不要为此把 API 无保护地暴露到公网。

## 备份与升级

暂停图库写入，备份独立 PostgreSQL 数据库与 /var/lib/cloud-gallery/images，备份环境文件应加密并限制访问。恢复时数据库和图片须来自同一备份时点。

升级先在测试库验证，备份数据与上一版源代码及前端构建产物。以后涉及已有表的变更必须增加版本化数据库迁移；不能仅执行 create_all。

图片删除的数据库操作和磁盘删除无法形成跨系统事务，异常停机可能留有孤立文件。正式投入多人使用前应补充离线文件对账与监控。

如希望整个网站只自己使用，可在图库的网页与 API 两个 location 同时增加 HTTP Basic Auth，并配合 HTTPS；不要只保护前端页面。当前应用默认允许匿名浏览明确设为公开的空间，个人新建空间默认私有。
