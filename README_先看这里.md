# Q7VPN V5.2 合并优化版（Android 优先）

本工程基于原始 V5.2 与修复版合并。当前优先目标是通过 GitHub Actions 构建安卓测试 APK，不再要求部署网站。

## 这次合并修改
- 图片验证码调整为 4 位，输入框限制为 4 位，验证码图缩小并居中显示。
- 手机端减少持续动画和背景模糊效果，降低 GPU 开销。
- Android 原生节点列表换成轻量水晶玻璃风格。
- TXT 节点本地持久化；后台并发检测 TCP 端口，批量完成后一次刷新界面，移除确认端口不可达的节点。
- 添加 `.github/workflows/android-apk.yml`，推送到 GitHub 后可在 Actions 下载 debug APK。

## 重要说明
**当前 Android 代码还不是独立可用的 VPN。** 它没有 `VpnService` 隧道，也没有 VLESS/SS 协议核心；端口检测不能验证协议认证和真实流量转发。界面会明确说明这一限制，不会假装已经连接。请查看 `ANDROID_STATUS_AND_NEXT_STEPS.md`，其中列出了接入 sing-box/libbox 后成为真正 VPN 所需的工程步骤。

## 在 GitHub 打包
1. 将整个工程上传到 GitHub 仓库（保留 `.github/workflows/android-apk.yml`）。
2. 打开仓库 **Actions**，运行 **Build Q7VPN Android APK**。
3. 工作流成功后进入本次运行记录，在 Artifacts 下载 `Q7VPN-debug-apk`。
4. 这是用于真机测试的 debug APK，不是应用商店正式签名包。

## 华为 Mate 50 Pro
`minSdk 26` 满足基础系统版本要求，但必须在真机测试文件选择器、节点 DNS/端口可达性、后台运行、电池优化和后续 VPN 授权/断连流程。
