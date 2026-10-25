# 指南：不经过 PR，给推送做背书

[English](../../en/guides/branch-gate.md) | [中文](branch-gate.md)

有些仓库直接从分支部署，或者存放 PR 不会碰的产物：模型、固件镜像、数据集。你仍然想对确切的 commit 有一份签过名的声明。

## 先说清楚限制

必需的 status check 在 PR 合并时生效。直接推送时，GitHub 没法要求一个推送落地之后才跑的 check。所以分支门禁只能是三种之一：

- **建议性**：发布 check，让人看见；
- **事后**：推送落地，操作员 dispatch 一次验证，这个 commit 上的 check 变绿；
- **预防性**：要求走 PR（自己批自己也算），改用[补丁门禁](patch-gate.md)。

想清楚选哪个。把建议性的 check 说成“强制”，还不如没有。

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
    uses: Oaklight/out-of-band/.github/workflows/verify.yml@<full-sha> # v0.5.0
    with:
      pr: "0"
      commit: ${{ inputs.commit }}
      job: release-smoke
      check-name: release-smoke-verified
      receipt: ${{ inputs.receipt }}
      evidence-url: ${{ inputs.evidence-url }}
```

证据默认必需，所以这次 dispatch 要么通过 `evidence-url`（或 `evidence-file`）给归档，要么加 `require-evidence: false`，只留签名摘要。

想让推送也触发同一个调用，加上 `push: branches: [main]`，并传 `commit: ${{ github.sha }}`。第一次跑一定没有回执，结论是 `unverified`；之后 dispatch 补上。

## 提供回执

`receipt` 参数接收整块文本。让 `gh` 从文件读：

```bash
gh workflow run attestation.yml \
  -f commit="$(git rev-parse origin/main)" \
  -F receipt=@receipt.md
```

如果块已经在 shell 里转过一圈，反引号容易出问题，直接走 API，用 JSON：

```bash
jq -n --rawfile r receipt.md --arg c "$(git rev-parse origin/main)" \
  '{ref: "main", inputs: {commit: $c, receipt: $r}}' \
| gh api repos/OWNER/REPO/actions/workflows/attestation.yml/dispatches --input -
```

## 把回执提交进仓库

提交到某个分支的块，可以被调用方读出来传给 `receipt`。它不能放在被测试的那个 commit 里，因为 workflow checkout 的是默认分支。这种做法适合一个专门的 “attestations” 分支，记录验证过什么、什么时候验证的；它不是签名验证的替代品，验证照样跑。除非你需要这份纸面记录，否则不要放进主路径。

## 验证规则一样

不管怎么传，验证方都拿默认分支的 `allowed_signers` 验签，并核对仓库、commit、tree 和 job。为别的 commit 签的回执是 `E_WRONG_COMMIT`。
