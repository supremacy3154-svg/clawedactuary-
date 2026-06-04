# 个人站上线指南

正式域名：**https://clawedactuary.com.cn**

- **Cloudflare Pages（当前推荐）** → 见 **[DEPLOY-CLOUDFLARE.md](./DEPLOY-CLOUDFLARE.md)**
- GitHub Pages（备选）→ 见下文

本站为 Quarto 静态站，产物在 `personal-site/_site/`。

---

## 一、上线前必改配置

### 1. 站点根地址

编辑 `personal-site/_quarto.yml`：

```yaml
website:
  site-url: https://你的域名.com   # 建议与最终访问的主域名一致（带 https，无末尾斜杠）
```

保存后本地执行：

```bash
cd personal-site
./rebuild.sh
```

`site-url` 会影响 RSS、分享二维码里的 canonical 链接等。

### 2. GitHub Pages 用的 CNAME（自定义域名时）

在 `personal-site/` 下新建文件 **`CNAME`**（仅一行，不要 `https://`）：

```text
你的域名.com
```

或若你用 www 作为主站：

```text
www.你的域名.com
```

Quarto 构建时会把它复制到 `_site/CNAME`，GitHub Pages 才能绑定该域名。

---

## 二、GitHub Pages 部署（推荐）

### 步骤 1：代码推到 GitHub

若仓库还在本机、未关联远程：

```bash
cd /Users/mac/.openclaw/workspace-yanghailin
git add personal-site/ .github/workflows/personal-site-pages.yml
git commit -m "feat: personal site with GitHub Pages deploy"
# 在 GitHub 新建空仓库后：
git remote add origin git@github.com:<你的用户名>/<仓库名>.git
git push -u origin main
```

### 步骤 2：开启 Pages

1. 打开 GitHub 仓库 → **Settings** → **Pages**
2. **Build and deployment** → **Source** 选 **GitHub Actions**（不要选 “Deploy from branch”）
3. 推送 `personal-site/` 或工作流文件后，Actions 会自动跑 **Deploy personal site (GitHub Pages)**
4. 在 **Actions** 页确认 workflow 绿色通过

首次部署成功后，临时地址一般为：

`https://<用户名>.github.io/<仓库名>/`

（若仓库名是 `<用户名>.github.io`，则在根路径 `https://<用户名>.github.io/`。）

### 步骤 3：绑定自定义域名

1. 仍在 **Settings → Pages** → **Custom domain**
2. 填入：`你的域名.com` 或 `www.你的域名.com`
3. 勾选 **Enforce HTTPS**（证书签发可能要等几分钟到 48 小时）

### 步骤 4：域名服务商 DNS

在注册商（阿里云、腾讯云、Cloudflare、GoDaddy 等）添加记录。

**方案 A：根域名 `你的域名.com`（GitHub 当前推荐）**

| 类型 | 主机记录 | 记录值 |
|------|----------|--------|
| A | @ | `185.199.108.153` |
| A | @ | `185.199.109.153` |
| A | @ | `185.199.110.153` |
| A | @ | `185.199.111.153` |
| AAAA | @ | `2606:50c0:8000::153` 等（见 GitHub Pages 文档最新 4 条） |

GitHub 会提示最新 IP，以 Pages 设置页为准。

**方案 B：www 子域名**

| 类型 | 主机记录 | 记录值 |
|------|----------|--------|
| CNAME | www | `<用户名>.github.io` |

根域名若要跳转到 www，可在注册商做 URL 转发，或同时按 GitHub 文档配置 A + CNAME。

DNS 生效通常 **几分钟～几小时**，国内偶发更久。

### 步骤 5：验证

- 浏览器打开 `https://你的域名.com`
- 首页精选、文章页、底部分享二维码链接应为正式域名（不是 `example.com`）

---

## 三、不用 GitHub 时（备选）

将 `personal-site/_site/` **目录内全部文件**（含 `.nojekyll`、`CNAME`）上传到：

- 腾讯云 COS / 阿里云 OSS（静态网站托管，绑定 CDN + 域名）
- Cloudflare Pages（连 GitHub 自动构建，或上传 `_site`）

上传前同样先 `./rebuild.sh`，并改好 `site-url`。

---

## 四、上线后更新文章

1. 改 `personal-site/posts/*.qmd`
2. `git push` 到 `main`
3. GitHub Actions 自动重新构建发布（约 1～3 分钟）

本地预览仍用：

```bash
cd personal-site && quarto preview --port 4343
```

---

## 五、常见问题

| 现象 | 处理 |
|------|------|
| 打开仍是 example.com 链接 | 改 `_quarto.yml` 的 `site-url` 后 push，或本地 `./rebuild.sh` |
| Pages 404 | 确认 Source 是 **GitHub Actions**，且 workflow 成功 |
| 自定义域名不生效 | 检查 `personal-site/CNAME` 与 DNS；等待传播 |
| 国内访问慢 | 域名接入 Cloudflare 或国内 CDN 回源 GitHub Pages / OSS |

---

## 六、微信分享说明

分享按钮用**当前浏览器地址**生成二维码。上线后务必用 **HTTPS 正式域名** 打开文章再分享，否则扫码仍是本地或错误地址。
