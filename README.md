# tg-checkin

7 个 Telegram 账号每天 00:01 给 @zakadeep_bot 发 /checkin 签到。

## 用法
1. `pip install -r requirements.txt`
2. 复制 `config.example.yaml` 为 `config.yaml`，填自己的 api_id / api_hash（my.telegram.org 创建）
3. 每个号扫码登录一次：`python qr_login.py account1`，手机 Telegram 设置 → 设备 → 关联桌面设备扫码
4. 测试 1 个号：`python checkin.py account1`
5. 每天 00:01 定时跑：`python checkin.py`（默认 account1..account7，号与号之间随机隔 30-120 秒）

## Web 版账号池（web/）
纯 API + 单页前端，浏览器里管理 7 个号：
1. `cd web && pip install -r requirements.txt`
2. `uvicorn app:app --host 0.0.0.0 --port 8000`，打开页面
3. 页面里先填 api_id / api_hash（只存在服务器 config.yaml 里），再点“扫码登录”，手机 Telegram 设置 → 设备 → 关联桌面设备扫码
4. 点“立即签到全部 7 个号”手动跑，或等每天 00:01 自动跑（号间随机 30-120 秒）
5. 日志在页面里按号、按时间查看

注意：Web 服务要跑在能连 Telegram MTProto 的服务器上（不要用挡 MTProto 的机子），也不要把 `web/config.yaml`、`web/sessions/`、`web/data/` 提交到 GitHub。

## 注意
- `config.yaml`、`sessions/`、`qr_*.png` 不要提交到 GitHub，`.gitignore` 已排除。
- api_id / api_hash 只属于你自己的 App，不要用别人的。
