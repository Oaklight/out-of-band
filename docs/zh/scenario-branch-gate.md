# 场景：不经过 PR，为推送背书

[English](../en/scenario-branch-gate.md) | [中文](scenario-branch-gate.md)

有些仓库直接从分支部署，或者存放不走 PR 的产物：模型、固件、数据集。你仍然想对确切的 commit 留一份签名声明。

## 先说实话

必须的状态检查是在 PR 合并时生效的。直接推送时，GitHub 没法要求一个"推送之后才跑"的 check。所以分支门禁通常是这三种之一：

- **提示性**：照常发布 check，让大家看见；
- **事后补**：推送先落地，操作员再手动触发验证，check 在那个 commit 上变绿；
- **真正拦住**：要求走 PR（自己给自己批也行），用[补丁门禁](scenario-patch-gate.md)。

选哪个要想清楚。把提示性的 check 说成"强制"，比没有还糟。

## 接法

```yaml
name: attestation

on:
  workflow_dispatch:
    inputs:
      commit:
        required: true
      receipt:
        required: true
      evidence-url:
        default: ""

permissions:
  contents: read
  checks: write
  pull-requests: write

jobs:
  verified:
    uses: Oaklight/outboard/.github/workflows/verify.yml@<full-sha>
    with:
      pr: "0"
      commit: ${{ inputs.commit }}
      job: release-smoke
      check-name: release-smoke-verified
      receipt: ${{ inputs.receipt }}
      evidence-url: ${{ inputs.evidence-url }}
```

想让推送也触发，加 `push: branches: [main]`，传 `commit: ${{ github.sha }}`。第一次跑必然是 unverified，因为回执还不存在；之后再用 dispatch 补上。

## 提交回执

`receipt` 输入就是整块文本。让 `gh` 从文件读：

```bash
gh workflow run attestation.yml \
  -f commit="$(git rev-parse origin/main)" \
  -F receipt=@receipt.md
```

如果回执已经过了一道 shell、里面的反引号看着不对劲，就直接调 API，它收 JSON：

```bash
jq -n --rawfile r receipt.md --arg c "$(git rev-parse origin/main)" \
  '{ref: "main", inputs: {commit: $c, receipt: $r}}' \
| gh api repos/OWNER/REPO/actions/workflows/attestation.yml/dispatches --input -
```

## 把回执提交进仓库

放在某个分支里的回执，可以由调用方读出来再传给 `receipt`。它不能放在被测的那个 commit 里，因为 workflow 检出的是默认分支。这种做法适合专门存证的 "attestations" 分支，记录什么时候验证了什么；它不能替代验签，验签照跑。除非确实需要这份纸面记录，否则别把它放进主路径。

## 验证没有区别

不管怎么送达，验证方都用默认分支的 `allowed_signers` 验签，都核对仓库、commit、tree 和 job。commit 对不上就是 `E_WRONG_COMMIT`。
