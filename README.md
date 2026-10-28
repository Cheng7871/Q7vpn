# NodeBox

一个适合部署到 Render 的简约节点管理器。

## 支持

- 导入 TXT
- `ss://`
- `vless://`
- 搜索
- 复制节点 URI
- 删除节点
- 手动添加
- 浏览器本地保存

## 本地运行

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

打开 `http://127.0.0.1:10000`

## Render 部署

把整个项目上传到 GitHub，然后在 Render 新建 Web Service。

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
gunicorn app:app
```

也可以直接使用项目里的 `render.yaml`。

## 说明

这是“节点管理/解析”软件，不是 VPN 服务本身。它不会自动建立 VPN 隧道，也不会绕过第三方服务的登录或验证码。
