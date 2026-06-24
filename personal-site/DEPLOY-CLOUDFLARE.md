# Cloudflare Pages 部署 · clawedactuary.com.cn

站点目录：`personal-site/`  
构建产物：`personal-site/_site/`  
正式地址：**https://clawedactuary.com.cn**

---

## 前提

1. 域名 **clawedactuary.com.cn** 已加入 [Cloudflare](https://dash.cloudflare.com)（注册商处把 **DNS 服务器** 改为 Cloudflare 分配的两条 NS）。
2. 代码在 **GitHub**（或 GitLab）仓库，便于 Cloudflare Pages 自动构建。

本地已配置：

- `_quarto.yml` → `site-url: https://clawedactuary.com.cn`
- `CNAME` → `clawedactuary.com.cn`
- 构建脚本 → `personal-site/scripts/cloudflare-build.sh`

---

## 一、创建 Cloudflare Pages 项目

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com) → **Workers & Pages** → **Create**
2. 选 **Pages** → **Connect to Git**
3. 授权并选择你的仓库（含 `personal-site` 的那个）
4. **Build settings** 按下面填写（路径相对于仓库根目录）：

| 项 | 值 |
|----|-----|
| Production branch | `main` |
| Framework preset | **None** |
| Build command | `bash personal-site/scripts/cloudflare-build.sh` |
| Build output directory | `personal-site/_site` |
| **Deploy command** | **留空**（不要填 `npx wrangler deploy`） |
| Root directory (可选) | 留空（仓库根） |

**重要：** Git 连线的 **Cloudflare Pages（静态站）** 会在构建结束后自动上传 **Build output directory** 里的文件。不需要、也不应再执行 Deploy command。`wrangler deploy` 是给 **Workers** 用的；本仓库 Quarto 产物应走 Pages 静态部署。

5. **Environment variables**（可选）：`QUARTO_VERSION` = `1.6.40`

6. **Save and Deploy**，等待首次构建变绿。

构建日志里应看到 `quarto render` 与 `Output created: _site/index.html`。

---

## 二、绑定自定义域名

1. 进入该 Pages 项目 → **Custom domains** → **Set up a custom domain**
2. 输入：`clawedactuary.com.cn`
3. 若域名已在当前 Cloudflare 账号，会自动添加 DNS 记录；按提示确认即可。
4. 等待 **SSL** 状态为 Active（通常几分钟）。

### 是否加 www？

若希望 `www.clawedactuary.com.cn` 跳转到根域名：

- Custom domains 里再添加 `www.clawedactuary.com.cn`
- **Redirects** 或 **Bulk Redirects** 中设置：`www.clawedactuary.com.cn/*` → `https://clawedactuary.com.cn/$1`（301）

若主站打算用 www，需把 `_quarto.yml` 的 `site-url` 和 `CNAME` 改成 `https://www.clawedactuary.com.cn` 后重新部署。

---

## 三、DNS 检查（域名在 Cloudflare 时）

在 **DNS → Records** 中通常会出现（Pages 自动创建）：

- 类型 **CNAME** 或 **Flattened CNAME**：`clawedactuary.com.cn` → `<项目名>.pages.dev`

**Proxy status** 建议保持 **Proxied（橙色云）**，便于 HTTPS 与 CDN。

---

## 四、推送代码即发布

```bash
git add personal-site/
git commit -m "content: update site"
git push origin main
```

Cloudflare 会自动重新构建；在 Pages 项目 **Deployments** 查看进度。

---

## 五、不用 Git 时：本机构建 + Wrangler 上传

已安装 [Node.js](https://nodejs.org/) 与 Wrangler 时：

```bash
cd personal-site
./rebuild.sh
npx wrangler pages deploy _site --project-name=clawed-actuary
```

（`project-name` 需与 Cloudflare 里 Pages 项目名一致；首次会提示登录 Cloudflare。）

---

## 六、与 GitHub Pages 的关系

仓库内 `.github/workflows/personal-site-pages.yml` 面向 GitHub Pages。  
**只用 Cloudflare 时不必开启** GitHub 仓库的 Pages（Settings → Pages → Source 保持关闭即可），避免两套部署打架。

---

## 七、上线后自检

- [ ] https://clawedactuary.com.cn 可打开首页
- [ ] 文章页底部分享、二维码链接为 `clawedactuary.com.cn`（不是 example.com / localhost）
- [ ] https://clawedactuary.com.cn/blog.xml RSS 可访问
- [ ] 手机微信扫文章页「微信」二维码能打开正式站

---

## 八、常见问题

| 问题 | 处理 |
|------|------|
| Clone 失败：`error occurred while updating repository submodules` | 仓库里存在**子模块指针**（`git ls-files -s` 出现 `160000`）但没有有效 `.gitmodules`。在仓库根执行 `git rm --cached <path>` 去掉错误 gitlink，提交并 push；站点构建不需要 `skills/` 等子目录时可不要重新 `git add` 该路径 |
| Build 找不到 quarto | 确认 Build command 为 `bash personal-site/scripts/cloudflare-build.sh`，且脚本有执行权限（Git 中 `chmod +x` 或 `git update-index --chmod=+x`） |
| 构建成功但 deploy 失败：`Could not detect a directory containing static files` | 在 **Settings → Builds** 里**删掉 Deploy command**（例如误填的 `npx wrangler deploy`），只保留 Build output directory = `personal-site/_site`，然后 **Retry deployment**。本机直传才用 `wrangler pages deploy`（见第五节），不是 `wrangler deploy` |
| 推送代码后线上仍是旧页面（评论/订阅显示占位） | 打开 Pages 项目 → **Deployments**，确认最新 commit 已构建成功；失败则看日志是否缺 `sync_posts.py`；成功但仍旧内容则点 **Retry deployment** 或 **Purge cache**。可用 `curl -s https://clawedactuary.com.cn/ \| grep embed-subscribe` 检查是否已部署新订阅表单 |
| 构建成功但 404 | Build output directory 必须是 `personal-site/_site`（不是 `personal-site`） |
| 域名不在 Cloudflare | 先把 NS 迁到 Cloudflare，或用 DNS 服务商 CNAME 到 `xxx.pages.dev`（见 Pages 自定义域名说明） |
| .com.cn 备案 | 大陆访问如需 ICP 备案，Cloudflare 海外节点不替代备案要求；仅个人学习站请自行评估合规 |
