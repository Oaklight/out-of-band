# outboard

面向 CI 门禁的带外回执。

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

## 为什么需要它

设想一个只有一台机器能真正验证的 PR。代码需要特定的加速器、有授权的工具链、
只能从办公网访问的数据库，或者一台几个人共用的实验机。GitHub 的 runner 到不了
那里，检查也搬不走。

把 runner 装到那台机器上，通常比问题本身更糟：

- **self-hosted runner** 意味着共享硬件上常驻一个守护进程、一个能领取任务的
  GitHub 凭据，以及仓库代码会在这台机器上执行。
- **上传日志和 artifact** 把合并决定交给一个人去浏览器标签页里翻文件。
- **跳过检查** 把门禁变成了建议。

outboard 走第四条路。检查留在原地运行，产出一条很小的签名声明：这个仓库、这个
commit、这个 job、这个结果、这份证据摘要。只有这条声明会离开那台机器。托管侧的
workflow 对原始字节验签、核对绑定，并把结论发布成 check run。操作员机器不需要
任何入站路径，也不持有 GitHub 凭据。

如果没有收到有效声明，结果就是 `unverified`，合并保持阻塞。"没跑"和"跑了但失败"
始终是两个不同的状态。

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

分工是刻意的：本仓库负责机制（格式、签名、验签、发布），消费者负责策略（哪些
路径需要回执、job 名称、用哪把密钥、必需还是可选）。

## 三种状态，绝不合并

| 回执 | 退出码 | check 结论 |
|---|---|---|
| 有效，`result: pass` | 0 | `success` |
| 有效，`result: fail` | 1 | `failure` |
| 缺失或无效 | 2 | `action_required` |
| 用法或内部错误 | 3 | 不发布；job 失败 |

缺回执是 **unverified**，绝不是 skip。工具跑不起来时，必需的检查保持 pending，
合并继续被阻塞。

## 安装

```bash
pip install outboard
```

需要 Python 3.11+，以及支持 `ssh-keygen -Y sign` 的 OpenSSH（8.0+）。没有运行时
依赖。

## 快速开始

在操作员机器上生成密钥。它不离开这台机器。

```bash
ssh-keygen -t ed25519 -N "" -C "ci operator" -f ~/.ssh/outboard
```

把公钥提交到消费者仓库的 `.github/allowed_signers`：

```
operator ssh-ed25519 AAAA...
```

为某个 commit 签署结果。`--commit` 必须是本地克隆中存在的完整 SHA；tree 从
commit 读取，而不是工作区。

```bash
outboard sign \
  --job smoke \
  --commit "$(git rev-parse HEAD)" \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/outboard
```

输出是一个块：HTML 标记、一行 JSON、一段 SSH 签名。把它贴成 PR 评论，或传给
`workflow_dispatch` 输入。

发出前先在本地验一遍：

```bash
outboard verify --block block.md \
  --allowed-signers .github/allowed_signers \
  --repo owner/name --commit "$SHA" --expect-job smoke
```

## 接入消费者仓库

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

然后在分支保护里把 `smoke-verified` 设为 required check。check 名称是公开契约：
改名会悄悄改变分支保护的内容。

输入：`pr`、`commit`、`job`、`required`、`check-name`、`receipt`、
`allowed-signers`、`trusted-authors`。输出：`verdict`。

`uses:` 必须按 commit SHA 固定。tag 是可变的。

### 回执收集

- 设置了 `receipt` 输入时以它为准，用于 `workflow_dispatch`。
- 否则 workflow 读取 `pr` 上的 issue 评论，只保留可信作者的评论：设置了
  `trusted-authors` 就用它，否则要求 `OWNER`、`MEMBER` 或 `COLLABORATOR`。
  不可信评论里的标记会被完全忽略，陌生人贴一条也无法卡住门禁。
- 字节完全相同的块视为同一个；互相矛盾的块报 `E_MULTI_BLOCK`。

### 触发方式与 fork

来自 fork 的 `pull_request` 拿到的是只读 token，什么都发布不了。fork 场景请用
`pull_request_target`（跑 default 分支代码，不 checkout PR）或 `issue_comment`。

### 凭据

`sign` 和 `verify` 不需要任何 GitHub 凭据，断网也能工作。发布需要 GitHub App
身份；在 Actions 里自动签发的 `GITHUB_TOKEN` 就是 Actions App。PAT 只能创建
commit status，所以 CLI 没有 publish 命令。

### 保留期

check 和 workflow run 跟随 Actions 的保留期设置（默认 90 天，public 仓库上限
90 天）。PR 评论里的回执才是长期记录，证据目录留在操作员侧。

## 回执能证明什么

它证明：某把已登记密钥的持有者签了这些确切的字节，绑定了一个仓库、commit、
tree、job 和证据摘要。

它不证明 job 跑得对、证据与摘要一致、或机器没有被攻破。它是一份证词，不是正确性
的证明。见 [SPEC.md](SPEC.md) §8。

## 开发

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
```

`SPEC.md` 是规范（英文）。`docs/validation.md` 记录了操作员机器的验证过程。
self-test workflow 会签四份回执，并断言有效的通过、伪造的不通过。

## 非目标

不做 runner、不做托管服务、不做 GitHub App、不接 Sigstore、不存 artifact。
