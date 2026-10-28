# Q7VPN V5：UI 与账户安全优化版

本压缩包分为两个独立工程：

- `web/`：Q7vpn Flask 网站管理器，可部署到 Render。
- `android/`：Android 原生 MVP，导入 TXT、展示节点、做 TCP 端口可达性检测，并可把节点 URI 分享给兼容代理客户端。

## 已实现
- 网站：账户注册/登录、基础找回密码、节点导入/去重/删除/导出、安全事件页面、黑白主题、基础限流与 CSRF；V5 优化了登录/注册视觉、流光 Q7VPN 字标、底部导航、个人账户安全中心、唯一 Q7-数字 ID、ID 或用户名登录，以及当前密码验证后的修改密码流程。
- Android：原生界面、文件选择器、SS/VLESS URI 基础解析、去重、TCP 延迟/可达性测试、节点选择、分享给兼容客户端。

## 未实现（重要）
- Android 内嵌 sing-box/libbox 代理核心。
- Q7vpn 自己的 `VpnService` 隧道生命周期、TUN 文件描述符与核心集成。
- Q7vpn 自己弹出 Android VPN 权限窗口并在应用内完成连接。
- 通过真实 IP 地理数据库确认国家。当前国家显示“未知地区”，不能凭节点名字推断国家。
- 专属 ID 使用数据库用户主键生成，例如 `Q7-0000001`；ID 不是密码，登录仍需输入密码。
- 免费节点的可用性保证。TCP 可达不代表协议握手/认证成功。
- 网站和 Android 之间的账户同步 API、自动下发节点 API。
- 短信验证、生产级找回密码和完整 DDoS 防护。

因此，本版本是可继续开发的工程包，不应被描述为已完成的独立 VPN 产品。Android 的“交给客户端”会打开系统分享菜单，实际 VPN 连接由用户选择的兼容客户端完成。

## Render 部署
在 Render 创建 Web Service，仓库根目录可以设为 `web`，或将 `web/` 内容放在仓库根目录：
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Health Check Path: `/health`

环境变量：
- `SECRET_KEY`: 强随机密钥
- `IP_HASH_SALT`: 独立随机盐
- `RATELIMIT_STORAGE_URI`: 生产环境建议使用 Redis URL
- `Q7VPN_DB_PATH`: 如要使用 SQLite，必须指向已挂载的持久化磁盘路径，例如 `/var/data/q7vpn.sqlite3`

注意：Render 默认文件系统是临时的。持久化磁盘仅在付费 Web Service 等符合条件的服务中可用；生产应用更建议使用 Render Postgres。参考：https://render.com/docs/disks

## Android 构建
用 Android Studio 打开 `android/` 目录，等待 Gradle 同步，再使用 Build > Build APK(s)。当前没有附带 APK，因为生成环境没有 Android SDK 构建工具。

## 下一步
1. 验证网站部署与数据库持久化。
2. 用自有/授权的有效节点测试 Android 导入。
3. 决定内嵌 sing-box/libbox 的版本，并实现 Android 平台回调与 VPN Service 生命周期。
4. 做协议握手、出口 IP、DNS、IPv4/IPv6、断线重连和隐私审查。

## V5.2 视觉升级说明
- 登录/注册页使用 Q7VPN 大字标识、科幻氛围背景和水晶玻璃质感控件。
- 登录后控制台增加动态渐变氛围背景、玻璃卡片和流光按钮。
- 中文/英文、主题、强调色设置位于页面顶部控制区；移动端尽量保留全部入口。
- 原有底部导航继续承载首页、节点、导入、安全中心和退出登录。
- 动画支持系统“减少动态效果”偏好。

注意：本次主要为前端视觉增强，不代表 Android 原生 VPN 隧道已实现，也未代替 Render 线上部署与浏览器验收。
