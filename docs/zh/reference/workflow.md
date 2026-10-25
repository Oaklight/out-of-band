# 可复用 workflow

[English](../../en/reference/workflow.md) | [中文](workflow.md)

`.github/workflows/verify.yml` 把验证器做成独立的 job。它只声明 `workflow_call`，触发条件由调用方决定。

想要独立 job、自带超时和并发，或者不想把验证步骤混进自己的 job，选它。想验证就在已有 job 里完成，选 [action](action.md)。

## 它做什么

1. 用 `persist-credentials: false` checkout 调用方的**默认分支**。
2. 按固定的 `OOB_VERSION` 安装 `out-of-band`。
3. 从 `receipt` 参数或可信评论里解析回执。
4. 验签，核对绑定。
5. 取证据归档并比对摘要。
6. 发布 check run、固定评论和 step summary。

job 跑在 `ubuntu-latest`，5 分钟超时；并发按 `check-name` 和 `commit` 分组，不取消正在跑的 run。

## 参数

| 参数 | 类型 | 默认值 | 含义 |
| --- | --- | --- | --- |
| `pr` | string | `"0"` | 用来收集评论和发固定评论的 PR；`0` 表示都不用 |
| `commit` | string | 必需 | 期望的 head SHA |
| `job` | string | 必需 | 期望的 job 名 |
| `required` | boolean | `true` | 这次改动是否需要回执 |
| `check-name` | string | `oob` | check run 名字 |
| `receipt` | string | 空 | 直接传入回执文本，优先于评论 |
| `allowed-signers` | string | `.github/allowed_signers` | 使用方仓库里的路径 |
| `trusted-authors` | string | 空 | 允许提供回执的登录名，逗号分隔 |
| `evidence-url` | string | 空 | 证据 `.tar.gz` 的 HTTPS 地址 |
| `evidence-file` | string | 空 | runner 上的路径，优先于 `evidence-url` |
| `report` | boolean | `true` | 发布 check run 和固定评论；`false` 只算结论 |
| `require-evidence` | boolean | `true` | 要求摘要一致的证据归档 |
| `source-ref` | string | 空 | 内部参数：本仓库自测用的 checkout ref；其他仓库忽略 |

输出：`verdict`，取值为 `verified`、`failed`、`unverified` 或 `not applicable`。

`source-ref` 是给本仓库测试未发布代码用的。使用方设置它没有意义：只有调用方是 `Oaklight/out-of-band` 时才会读。

## 权限

调用方必须给：

```yaml
permissions:
  contents: read
  checks: write
  pull-requests: write
```

不使用仓库 secret。`GITHUB_TOKEN` 是唯一的凭据。

## 最小配置

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
          PR: ${{ github.event.pull_request.number || github.event.issue.number }}
        run: |
          commit="$(gh api "repos/$GITHUB_REPOSITORY/pulls/$PR" --jq .head.sha)"
          echo "pr=$PR" >> "$GITHUB_OUTPUT"
          echo "commit=$commit" >> "$GITHUB_OUTPUT"

      - id: paths
        env:
          GH_TOKEN: ${{ github.token }}
          PR: ${{ steps.context.outputs.pr }}
        run: |
          if gh api --paginate "repos/$GITHUB_REPOSITORY/pulls/$PR/files?per_page=100" \
               --jq '.[].filename' | grep -qE '^patches/'; then
            echo "requires=true" >> "$GITHUB_OUTPUT"
          else
            echo "requires=false" >> "$GITHUB_OUTPUT"
          fi

  verified:
    needs: policy
    uses: Oaklight/out-of-band/.github/workflows/verify.yml@<full-sha> # v0.5.0
    with:
      pr: ${{ needs.policy.outputs.pr }}
      commit: ${{ needs.policy.outputs.commit }}
      job: patch-smoke
      required: ${{ needs.policy.outputs.requires == 'true' }}
      check-name: patch-smoke-verified
      trusted-authors: your-login
```

`policy` 用 API 解析 head，因为在 `issue_comment` 事件里，`github.sha` 是默认分支，不是 PR head。示例没有写证据来源；调用时补上 `evidence-url` 或 `evidence-file`，或者设 `require-evidence: false`。

## 为什么 checkout 默认分支

workflow 明确 checkout 默认分支。checkout PR 会让 PR 自己提供 `allowed_signers`。它读的仓库文件只有这一个。

同理，调用方要用 `pull_request_target` 或 `issue_comment`，不要用 `pull_request`。调用它的 workflow 带可写 token，绝不能 checkout 或执行 PR 代码。

## 固定版本

```yaml
uses: Oaklight/out-of-band/.github/workflows/verify.yml@<full-sha> # v0.5.0
```

完整 SHA 不会变，tag 会。版本号写在注释里，让 Dependabot 去开升级 PR。见[运维](../operations.md#发布与固定版本)。

## action 还是 workflow

action 是 step，继承调用方的权限、超时和并发，可以和别的步骤放在同一个 job。workflow 是 job，边界明确，设置固定。两者跑的是同一个验证器，发布的是同一种 check。
