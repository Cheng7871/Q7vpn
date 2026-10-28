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
