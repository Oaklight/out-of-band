<h1 align="center">out-of-band</h1>

<p align="center">在 GitHub 够不到的地方跑检查，用签名回执卡住合并。</p>

<p align="center">
  <a href="https://pypi.org/project/out-of-band/"><img src="https://img.shields.io/pypi/v/out-of-band?color=green" alt="PyPI"></a>
  <a href="https://github.com/Oaklight/out-of-band/releases/latest"><img src="https://img.shields.io/github/v/release/Oaklight/out-of-band?color=green" alt="Release"></a>
  <a href="https://github.com/Oaklight/out-of-band/actions/workflows/ci.yml"><img src="https://github.com/Oaklight/out-of-band/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="Apache-2.0"></a>
</p>

<p align="center">
  <a href="README_en.md">English</a> | <a href="README_zh.md">中文</a>
</p>

<p align="center">
  <a href="https://oaklight.github.io/out-of-band/"><strong>先看一遍导览 →</strong></a>
</p>

## 为什么需要它

有些检查，GitHub 的 runner 跑不了：需要某种加速器、有授权的工具链、只能从内网访问的数据库，或者一台几个人共用的实验机。检查本身没问题，只是搬不到 GitHub 上。

把 runner 装到那台机器上，麻烦通常比收益多：

- 自托管 runner 要在共享机器上常驻一个进程，放一份能领任务的 GitHub 凭据，仓库代码还会在那台机器上执行。
- 上传日志和产物，最后变成有人在浏览器里翻文件来决定能不能合并。
- 干脆跳过检查，门禁就成了摆设。

out-of-band 换个做法：检查留在原地，跑完只生成一小段签名记录，写明仓库、commit、job、结果和证据摘要。离开这台机器的只有这段记录。GitHub 那边的 workflow 会对原始字节验签、核对绑定关系，再把结论发成 check run。操作员机器不用开入站端口，也不用存 GitHub 凭据。

还有一种情况，一点也不特殊：测试在 CI 上也能跑，但你已经跑过了。重跑可能比写这次改动还久，可能因为本地没出现的环境问题失败，也可能得到一个略有差别的数字。签名回执让门禁直接采用你手上这次结果。

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
| 缺失或无效 | 2 | `failure` |
| 用法错误或内部错误 | 3 | 不发布，job 失败 |

没有回执就是 `unverified`，不能当成 skip。工具自身出错时，必需的检查会停在 pending，合并照样过不去。所有 unverified 结果的 check 结论都是 `failure`，原因写在标题和 summary 里。

## 安装

```bash
pip install out-of-band
```

需要 Python 3.10+ 和 OpenSSH 8.0+（`ssh-keygen -Y sign`），没有运行时依赖。

## 快速上手

密钥在操作员机器上生成，私钥不出这台机器。

```bash
ssh-keygen -t ed25519 -N "" -C "ci operator" -f ~/.ssh/out-of-band
```

把公钥提交到使用方仓库的 `.github/allowed_signers`：

```
operator ssh-ed25519 AAAA...
```

给某个 commit 签结果。`--commit` 必须是完整的 SHA，本地仓库里得存在；tree 从 commit 读，不看工作区。

```bash
oob sign \
  --job smoke \
  --commit "$(git rev-parse HEAD)" \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/out-of-band \
  --output-file ./check-output.txt
```

`--output-file` 是可选的：把检查打印的内容（最多 4 KiB）一起签进回执（schema
`receipt/v2`），check 页面会在摘要下面折叠展示。不带它，回执仍是 `receipt/v1`。

输出就是回执：一个 HTML 标记、一行 JSON、一段 SSH 签名。贴成 PR 评论，或者通过 `workflow_dispatch` 传进去。

要贴成可读的评论，先渲染：

```bash
oob render --block receipt.md
```

输出一张 Markdown 表格，把原始签名块放进默认折叠的 `<details>` 里。验证方只读块，不读表格。

发出去之前先本地验一遍：

```bash
oob verify --block block.md \
  --allowed-signers .github/allowed_signers \
  --repo owner/name --commit "$SHA" --expect-job smoke
```

## 文档

按场景写的指南在 [docs/](docs/zh/README.md)：补丁门禁、benchmark 记录、不经过 PR 的分支背书、同一个 commit 上的多个 job、离线机器，以及运维。建议先从那里看，再回来看下面这串输入参数。

## 接到自己的仓库

两种接法，验证逻辑相同：action 当 step 用，可复用 workflow 当一个 job 用。差别和输入见 [action 文档](docs/zh/action.md)。

### action

```yaml
  verified:
    needs: policy
    runs-on: ubuntu-latest
    permissions:
      contents: read
      checks: write
      pull-requests: write
    steps:
      - uses: Oaklight/out-of-band@<full-sha> # v0.5.0
        with:
          pr: ${{ needs.policy.outputs.pr }}
          commit: ${{ needs.policy.outputs.commit }}
          job: smoke
          required: ${{ needs.policy.outputs.requires }}
          check-name: smoke-verified
          trusted-authors: operator-login
```

`required` 传进来是字符串 `true` 或 `false`。action 自己声明不了
`permissions`，得由 job 给。

### 可复用 workflow

```yaml
name: receipt gate

on:
  pull_request_target:
    types: [opened, synchronize, reopened, ready_for_review]
  issue_comment:
    types: [created]

permissions:
  contents: read
  checks: write
  pull-requests: write

jobs:
  policy:
    # A receipt arriving as a comment must trigger a fresh run.
    if: >
      github.event_name == 'pull_request_target' ||
      (github.event_name == 'issue_comment' &&
       github.event.issue.pull_request != null &&
       contains(github.event.comment.body, '<!-- receipt:v1 -->'))
    runs-on: ubuntu-latest
    outputs:
      pr: ${{ steps.context.outputs.pr }}
      commit: ${{ steps.context.outputs.commit }}
      requires: ${{ steps.paths.outputs.requires }}
    steps:
      - id: context
        env:
          GH_TOKEN: ${{ github.token }}
          PR_NUMBER: ${{ github.event.pull_request.number || github.event.issue.number }}
        run: |
          commit="$(gh api "repos/$GITHUB_REPOSITORY/pulls/$PR_NUMBER" --jq .head.sha)"
          echo "pr=$PR_NUMBER" >> "$GITHUB_OUTPUT"
          echo "commit=$commit" >> "$GITHUB_OUTPUT"

      - id: paths
        env:
          GH_TOKEN: ${{ github.token }}
          PR: ${{ steps.context.outputs.pr }}
        run: |
          if gh api --paginate "repos/$GITHUB_REPOSITORY/pulls/$PR/files?per_page=100" \
               --jq '.[].filename' | grep -qE '^src/'; then
            echo "requires=true" >> "$GITHUB_OUTPUT"
          else
            echo "requires=false" >> "$GITHUB_OUTPUT"
          fi

  verified:
    needs: policy
    uses: Oaklight/out-of-band/.github/workflows/verify.yml@<full-sha> # v0.4.1
    with:
      pr: ${{ needs.policy.outputs.pr }}
      commit: ${{ needs.policy.outputs.commit }}
      job: smoke
      required: ${{ needs.policy.outputs.requires == 'true' }}
      check-name: smoke-verified
      trusted-authors: operator-login
```

然后在分支保护里把 `smoke-verified` 设为必需检查。check 名称是对外契约，改名等于悄悄改了保护规则。

这里用 `pull_request_target` 而不是 `pull_request`：它跑默认分支上的那份 workflow，PR 改不了审判自己的门。它拿着写权限，fork PR 也一样，所以这个 workflow 里不要 checkout、不要执行 PR 代码。验证器只从默认分支读 `allowed_signers`，并把回执当数据。`policy` 通过 API 解析 head，这样评论触发的运行不会退回成 `github.sha`（那是基分支）。

输入：`pr`、`commit`、`job`、`required`、`check-name`、`receipt`、`allowed-signers`、`trusted-authors`、`evidence-url`、`evidence-file`、`report`、`require-evidence`；输出：`verdict`。action 还多 `version`、`source`、`python-version`、`token` 四个输入。

`uses:` 用完整 commit SHA 固定，并在注释里记下版本（`# v0.4.1`），让 Dependabot 去开升级 PR。tag 是可以被挪动的。

### 证据

默认必须提交证据。打包后，用两种方式之一交给验证方：`evidence-file`（runner 上的文件路径）或 `evidence-url`（HTTPS 地址）。怎么存放由你决定。

```bash
oob pack --evidence-dir ./evidence --out evidence.tgz
# 传 evidence-file，或者上传后把地址签进去：
oob sign ... --claims evidence_url="https://host/evidence.tgz"
```

地址在签名覆盖范围内，所以一条评论就够了。解析顺序是 `evidence-file`、`evidence-url`、`claims.evidence_url`。`require-evidence: false` 恢复只签摘要的模式。

runner 读取或下载、安全解包、重算摘要并比对。两种来源都没有是 `E_NO_EVIDENCE`，对不上是 `E_EVIDENCE_MISMATCH`。一致就作为 `oob-evidence` artifact 上传，并在 run summary 里列出清单和有限的文本预览。GitHub token 只发给 `api.github.com` 和 `github.com`，其他主机必须是公开或自带签名的 URL。

### 回执从哪来

- 传了 `receipt` 输入就用它，适合 `workflow_dispatch`。
- 否则读 PR 的 issue 评论，只认可信作者：配了 `trusted-authors` 就按名单，没配就只认 `OWNER`、`MEMBER`、`COLLABORATOR`。不可信评论里的标记直接忽略，陌生人贴一条也卡不住门禁。
- 指向旧提交的块会被忽略，重跑时可以直接贴新回执，不必先删掉旧的那条。只有指向期望提交的块才算候选。
- 字节完全一致的块算同一条；同一提交的块互相对不上才报 `E_MULTI_BLOCK`。

### 触发方式和 fork

从 fork 来的 `pull_request` 只有只读 token，什么都发布不了。fork 场景用 `pull_request_target`（跑默认分支代码，不 checkout PR）或者 `issue_comment`。另外，`pull_request` 跑的是 PR 自己那份 workflow，贡献者可以借此把门禁改松；这个 job 不要用它。

### 凭据

`sign` 和 `verify` 不需要任何 GitHub 凭据，断网也能跑。发布得用 GitHub App 身份；在 Actions 里，自动签发的 `GITHUB_TOKEN` 就是 Actions App。PAT 只能建 commit status，所以 CLI 里没有 `publish`。

### 离线操作员机器

签名机可以完全没有外网。用 Release 附带的单文件 `oob.pyz`（或 wheel）运行，用 `git bundle` 把代码带进去，回执和证据再手工带出来。具体步骤见 [docs/offline.md](docs/zh/offline.md)。

### 保留期

check 和 workflow run 跟着 Actions 的保留期走（默认 90 天，公开仓库最多 90 天）。要长期留档，靠 PR 评论里的回执；证据目录留在操作员那边。

## 回执能说明什么

它能说明：某个登记过公钥的人用对应的私钥签了这些字节，绑定了一个仓库、commit、tree、job 和证据摘要。

它不能说明 job 跑得对不对、证据和摘要是否一致、机器有没有被入侵。这是一份签名声明，不是正确性证明。详见 [SPEC.md](SPEC.md) 第 8 节。

## 关于名字

out-of-band 说的是检查发生在常规 CI 路径之外。GitHub 仍然收到结果，但任务和签名在别处完成：实验室的机器、HPC 登录节点、租来的 GPU。回来的只有一份签名回执。

命令是 `oob`，就是这几个词的缩写；包名和仓库用全称 `out-of-band`。

## 开发

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
```

`SPEC.md` 是规范（英文）。`docs/zh/validation.md` 记录了操作员机器上的验证。self-test workflow 会签四份回执，断言有效的能过、伪造的过不了。

## 不做什么

不做 runner、不做托管服务、不做 GitHub App、不接 Sigstore、不存产物。
