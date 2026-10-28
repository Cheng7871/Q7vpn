# Q7vpn V3 (Render-ready starter)

A Flask web starter for account login/registration, persistent sessions, SS/VLESS URI node management, light/dark theme, basic security event logging, CSRF protection and rate limits.

## Deploy on Render
1. Upload the contents of this folder to a GitHub repository.
2. Create a Render Web Service from that repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Health check path: `/health`
6. Add environment variables:
   - `SECRET_KEY`: long random secret (required; do not keep the development fallback)
   - `IP_HASH_SALT`: random secret salt for IP hash identifiers
   - `RATELIMIT_STORAGE_URI`: for production, use a Redis URL supplied by your provider
   - `COOKIE_SECURE`: keep `1` when served over HTTPS
7. Attach a persistent disk and set `Q7VPN_DB_PATH` to a path on that disk, e.g. `/var/data/q7vpn.sqlite3`, if you need account data to survive instance replacement. SQLite on ephemeral storage can be lost on redeploy.

## Important limitations
- This is a starter, not a production-audited identity system.
- Phone number is collected as account recovery metadata only. It does not send SMS. Recovery uses a security answer, which is weaker than verified email/SMS/passkeys; for production, integrate a real verified recovery channel.
- No external login, no real VPN tunnel, no embedded proxy core, and no packet capture engine. Node URI handoff is available through browser share/copy.
- Basic Flask-Limiter limits are not a substitute for CDN/WAF DDoS mitigation. Use a reputable CDN/WAF, managed DDoS protection, persistent Redis-backed rate limiting, monitoring, backups, and security review before exposing this publicly.
- The security page is audit logging, not a claim of blocking all attacks. This code intentionally excludes offensive CC flood, credential stuffing, and unauthorized packet interception features.
- Node URIs may contain secrets. Treat them like passwords and avoid public sharing.


## V5 账户与 UI 更新
- 登录页使用大号 Q7VPN 动态渐变字标，不再使用旧的第三方风格图标。
- 账户创建后生成稳定的 `Q7-数字` ID（由唯一用户主键格式化得到），可用用户名或 ID + 密码登录。
- 安全中心展示当前账户自己的 ID、用户名、手机号、节点数量和注册时间。
- 修改密码需要验证当前密码、新密码至少 10 位且两次输入一致。
- 账户活动按用户 ID 过滤；旧版本中没有账户归属的历史日志不会错误地展示给其他账户。
- 退出登录保留在手机底部导航。

## V5.1 图片验证码与 IP 登录保护
- 登录和注册均要求填写会话绑定的图片验证码（SVG 动态生成，无短信服务依赖），验证码有效期 10 分钟，提交后一次性失效；可点击图片刷新。
- 同一来源 IP 在 15 分钟窗口内累计 5 次登录/注册验证失败后，锁定 5 分钟；页面显示实时倒计时，服务端也会强制阻止请求，不能只靠前端倒计时绕过。
- IP 保护记录保存在 SQLite 的 `auth_ip_guard` 表。生产环境应配置持久化数据库/磁盘，并确保代理只传递可信客户端 IP；若部署多实例，需改用共享数据库/Redis，避免实例间计数不一致。
- IP 级限制可能影响共用同一公网 IP 的多名用户（例如公共 Wi-Fi）；这是按当前需求采用的保护策略。
