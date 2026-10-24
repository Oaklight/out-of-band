# outboard

在 GitHub 够不到的地方跑检查，用签名回执卡住合并。

<p align="center">
  <a href="https://pypi.org/project/outboard/"><img src="https://img.shields.io/pypi/v/outboard?color=green" alt="PyPI"></a>
  <a href="https://pypi.org/project/outboard/"><img src="https://img.shields.io/pypi/pyversions/outboard?color=blue" alt="Python"></a>
  <a href="https://github.com/Oaklight/outboard/releases/latest"><img src="https://img.shields.io/github/v/release/Oaklight/outboard?color=green" alt="Release"></a>
  <a href="https://github.com/Oaklight/outboard/actions/workflows/ci.yml"><img src="https://github.com/Oaklight/outboard/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="Apache-2.0"></a>
</p>

<p align="center">
  <a href="README_en.md">English</a> | <a href="README_zh.md">中文</a>
</p>

<p align="center">
  <a href="https://oaklight.github.io/outboard/"><strong>先看一遍导览 →</strong></a>
</p>

## 为什么需要它

有些检查，GitHub 的 runner 跑不了：需要某种加速器、有授权的工具链、只能从内网访问的数据库，或者一台几个人共用的实验机。检查本身没问题，只是搬不到 GitHub 上。

把 runner 装到那台机器上，麻烦通常比收益多：

- 自托管 runner 要在共享机器上常驻一个进程，放一份能领任务的 GitHub 凭据，仓库代码还会在那台机器上执行。
- 上传日志和产物，最后变成有人在浏览器里翻文件来决定能不能合并。
- 干脆跳过检查，门禁就成了摆设。

outboard 换个做法：检查留在原地，跑完只生成一小段签名记录，写明仓库、commit、job、结果和证据摘要。离开这台机器的只有这段记录。GitHub 那边的 workflow 会对原始字节验签、核对绑定关系，再把结论发成 check run。操作员机器不用开入站端口，也不用存 GitHub 凭据。

没有有效记录，结论就是 `unverified`，合并继续被挡住。“没跑”和“跑了但失败”始终分开。

```
operator host                          GitHub
─────────────                          ──────
check ──► evidence ──► sign            PR comment / dispatch
                          │                    │
                          └── signed block ────┴──► verify.yml
                                                      │
                                                      ├── check run
                                                      ├── step summary
                                                      └── sticky comment
```

本仓库只管机制（格式、签名、验签、发布）；策略（哪些路径要回执、job 叫什么、用哪把密钥、必选还是可选）留在使用方仓库。

## 三种状态，别混为一谈

| 回执 | 退出码 | check 结论 |
|---|---|---|
| 有效，`result: pass` | 0 | `success` |
| 有效，`result: fail` | 1 | `failure` |
| 缺失或无效 | 2 | `action_required` |
| 用法错误或内部错误 | 3 | 不发布，job 失败 |

没有回执就是 `unverified`，不能当成 skip。工具自身出错时，必需的检查会停在 pending，合并照样过不去。

## 安装

```bash
pip install outboard
```

需要 Python 3.11+ 和 OpenSSH 8.0+（`ssh-keygen -Y sign`），没有运行时依赖。

## 快速上手

密钥在操作员机器上生成，私钥不出这台机器。

```bash
ssh-keygen -t ed25519 -N "" -C "ci operator" -f ~/.ssh/outboard
```

把公钥提交到使用方仓库的 `.github/allowed_signers`：

```
operator ssh-ed25519 AAAA...
```

给某个 commit 签结果。`--commit` 必须是完整的 SHA，本地仓库里得存在；tree 从 commit 读，不看工作区。

```bash
outboard sign \
  --job smoke \
  --commit "$(git rev-parse HEAD)" \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/outboard \
  --output-file ./check-output.txt
```

`--output-file` 是可选的：把检查打印的内容（最多 4 KiB）一起签进回执（schema
`receipt/v2`），check 页面会在摘要下面折叠展示。不带它，回执仍是 `receipt/v1`。

输出就是回执：一个 HTML 标记、一行 JSON、一段 SSH 签名。贴成 PR 评论，或者通过 `workflow_dispatch` 传进去。

发出去之前先本地验一遍：

```bash
outboard verify --block block.md \
  --allowed-signers .github/allowed_signers \
  --repo owner/name --commit "$SHA" --expect-job smoke
```

## 文档

按场景写的指南在 [docs/](docs/README.zh.md)：补丁门禁、benchmark 记录、不经过 PR 的分支背书、同一个 commit 上的多个 job、离线机器，以及运维。建议先从那里看，再回来看下面这串输入参数。

## 接到自己的仓库

```yaml
name: receipt gate

on:
  pull_request:
  issue_comment:
    types: [created]

permissions:
  contents: read
  checks: write
  pull-requests: write

jobs:
  policy:
    runs-on: ubuntu-latest
    outputs:
      requires: ${{ steps.paths.outputs.requires }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - id: paths
        env:
          BASE: ${{ github.event.pull_request.base.sha }}
          HEAD: ${{ github.event.pull_request.head.sha }}
        run: |
          if git diff --quiet "$BASE" "$HEAD" -- src/; then
            echo "requires=false" >> "$GITHUB_OUTPUT"
          else
            echo "requires=true" >> "$GITHUB_OUTPUT"
          fi

  verified:
    needs: policy
    uses: Oaklight/outboard/.github/workflows/verify.yml@<full commit SHA>
    with:
      pr: ${{ github.event.pull_request.number || 0 }}
      commit: ${{ github.event.pull_request.head.sha || github.sha }}
      job: smoke
      required: ${{ needs.policy.outputs.requires == 'true' }}
      check-name: smoke-verified
      trusted-authors: operator-login
```

然后在分支保护里把 `smoke-verified` 设为必需检查。check 名称是对外契约，改名等于悄悄改了保护规则。

输入：`pr`、`commit`、`job`、`required`、`check-name`、`receipt`、`allowed-signers`、`trusted-authors`；输出：`verdict`。

`uses:` 用完整 commit SHA 固定，tag 是可以被挪动的。

### 上传证据

`evidence-url` 留空就维持现状：回执只绑定摘要，不上传任何东西。

把它设成 `outboard pack` 生成的包的 HTTPS 地址，workflow 会下载、安全解包、
重算摘要并比对，一致才作为 `outboard-evidence` artifact 上传；对不上则判为
unverified。

```bash
outboard pack --evidence-dir ./evidence --out evidence.tgz
```

### 回执从哪来

- 传了 `receipt` 输入就用它，适合 `workflow_dispatch`。
- 否则读 PR 的 issue 评论，只认可信作者：配了 `trusted-authors` 就按名单，没配就只认 `OWNER`、`MEMBER`、`COLLABORATOR`。不可信评论里的标记直接忽略，陌生人贴一条也卡不住门禁。
- 指向旧提交的块会被忽略，重跑时可以直接贴新回执，不必先删掉旧的那条。只有指向期望提交的块才算候选。
- 字节完全一致的块算同一条；同一提交的块互相对不上才报 `E_MULTI_BLOCK`。

### 触发方式和 fork

从 fork 来的 `pull_request` 只有只读 token，什么都发布不了。fork 场景用 `pull_request_target`（跑默认分支代码，不 checkout PR）或者 `issue_comment`。

### 凭据

`sign` 和 `verify` 不需要任何 GitHub 凭据，断网也能跑。发布得用 GitHub App 身份；在 Actions 里，自动签发的 `GITHUB_TOKEN` 就是 Actions App。PAT 只能建 commit status，所以 CLI 里没有 `publish`。

### 离线操作员机器

签名机可以完全没有外网。用 Release 附带的单文件 `outboard.pyz`（或 wheel）运行，用 `git bundle` 把代码带进去，回执和证据再手工带出来。具体步骤见 [docs/offline.md](docs/offline.md)。

### 保留期

check 和 workflow run 跟着 Actions 的保留期走（默认 90 天，公开仓库最多 90 天）。要长期留档，靠 PR 评论里的回执；证据目录留在操作员那边。

## 回执能说明什么

它能说明：某个登记过公钥的人用对应的私钥签了这些字节，绑定了一个仓库、commit、tree、job 和证据摘要。

它不能说明 job 跑得对不对、证据和摘要是否一致、机器有没有被入侵。这是一份签名声明，不是正确性证明。详见 [SPEC.md](SPEC.md) 第 8 节。

## 开发

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
```

`SPEC.md` 是规范（英文）。`docs/validation.md` 记录了操作员机器上的验证。self-test workflow 会签四份回执，断言有效的能过、伪造的过不了。

## 不做什么

不做 runner、不做托管服务、不做 GitHub App、不接 Sigstore、不存产物。
