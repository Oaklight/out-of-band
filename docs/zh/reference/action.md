# action

[English](../../en/reference/action.md) | [中文](action.md)

action 把验证器放进你已有的 job，作为其中一个 step；[可复用 workflow](workflow.md) 把它做成单独的 job。两种发布同样的 check run，读同一个信任根。

想自己掌握触发条件、权限、超时和并发，或者想把验证塞进一个已经在做别的事的 job，用 action。想要独立的 job 边界、不想自己配验证器，用可复用 workflow。

| | action | 可复用 workflow |
| --- | --- | --- |
| 调用位置 | step，`uses: Oaklight/out-of-band@<sha>` | job，`uses: Oaklight/out-of-band/.github/workflows/verify.yml@<sha>` |
| runner | 调用方的 job | 独立的 `ubuntu-latest` job |
| 权限 | 调用方设置 | workflow 自己声明 |
| 超时、并发 | 调用方设置 | 内置 |
| Marketplace | 可以上架 | 不能上架 |

## 调用方要提供什么

下面这些 action 自己声明不了：

- 触发条件，通常是 `pull_request_target` 加 `issue_comment`；
- `permissions: contents: read, checks: write, pull-requests: write`；
- `check-name`，分支保护匹配的就是这个字符串；
- 回执必须携带的 commit 和 job 名。

token 默认是 `${{ github.token }}`，必须能创建 check run、编辑 PR 评论。

## 参数

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `commit` | 必需 | 回执必须声明的 commit SHA |
| `job` | 必需 | 回执必须携带的 job 名 |
| `pr` | `0` | 用来收集评论和发固定评论的 PR；`0` 表示都不用 |
| `required` | `true` | 这次改动是否需要回执；字符串 `true` 或 `false` |
| `check-name` | `oob` | check run 名字 |
| `receipt` | 空 | 直接传入回执文本，优先于评论 |
| `allowed-signers` | `.github/allowed_signers` | 使用方仓库里的路径，从默认分支读取 |
| `trusted-authors` | 空 | 允许提供回执的登录名，逗号分隔 |
| `evidence-url` | 空 | 证据 `.tar.gz` 的 HTTPS 地址 |
| `evidence-file` | 空 | runner 上的证据 `.tar.gz` 路径，优先于 `evidence-url` |
| `report` | `true` | 发布 check run 和固定评论；`false` 只算结论 |
| `require-evidence` | `true` | 要求摘要一致的证据归档；`false` 允许只有摘要 |
| `version` | `0.5.0` | 安装的 out-of-band 版本；留空则不装 |
| `source` | 空 | 改为从本地路径安装；开发和自测用 |
| `python-version` | `3.12` | 验证器使用的 Python |
| `token` | `${{ github.token }}` | API token；权限见上 |

输出：`verdict`，取值为 `verified`、`failed`、`unverified` 或 `not applicable`。

## 它做什么

1. 按 `version` 从 PyPI 安装 `out-of-band`，或从 `source` 安装。
2. 通过 contents API 读默认分支上的 `allowed-signers`。
3. 解析回执：先用 `receipt` 参数，再读 `pr` 上可信作者的评论。
4. 验签，核对绑定。
5. 有证据就取归档，比对摘要。
6. 发布 check run、固定评论和 step summary。证据清单进 summary，归档变成 `oob-evidence` artifact。

每一步都软失败：验证不通过会发布成 `unverified`，而不是让 job 崩掉。只有工具错误（退出 3）才不发布 check。

## 等操作员

action 不会阻塞轮询。每个事件都是一次新的 run：

1. PR 打开。workflow 跑一遍，没找到回执，发布 `unverified`。
2. 操作员在受限机器上跑完 job，把签好的回执贴成评论。
3. `issue_comment` 再次触发 workflow。
4. action 找到 `commit` 和 `job` 都匹配的块，验签，用同一个名字发布 check。分支保护看到新的结果。

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
  verify:
    if: >
      github.event_name == 'pull_request_target' ||
      (github.event_name == 'issue_comment' &&
       github.event.issue.pull_request != null &&
       contains(github.event.comment.body, '<!-- receipt:v1 -->'))
    runs-on: ubuntu-latest
    steps:
      - id: context
        env:
          GH_TOKEN: ${{ github.token }}
          EVENT: ${{ github.event_name }}
          PR: ${{ github.event.pull_request.number || github.event.issue.number }}
        run: |
          if [ "$EVENT" = "pull_request_target" ]; then
            commit="${{ github.event.pull_request.head.sha }}"
          else
            commit="$(gh api "repos/$GITHUB_REPOSITORY/pulls/$PR" --jq .head.sha)"
          fi
          echo "pr=$PR" >> "$GITHUB_OUTPUT"
          echo "commit=$commit" >> "$GITHUB_OUTPUT"

      - uses: Oaklight/out-of-band@<full-sha> # v0.5.0
        with:
          pr: ${{ steps.context.outputs.pr }}
          commit: ${{ steps.context.outputs.commit }}
          job: bench-smoke
          check-name: receipt-verified
          trusted-authors: your-login
```

这段配置只展示门禁的接线。证据默认必需，所以要加 `evidence-url` 或
`evidence-file`，或者设 `require-evidence: false`。

## 安全注意

- 在 `pull_request_target` 下，绝不要 checkout 或执行 PR 代码。action 通过 API 读默认分支上的 `allowed_signers`，PR 改不了自己的信任根。
- 真正的门禁里，`uses:` 用完整 commit SHA 固定。tag 会动。
- 调用方的 `permissions` 是上限。job 没给 `checks: write`，action 也加不出来。
- action 按 `version` 从 PyPI 装 CLI；不在本仓库自测时，`source` 留空。
- 证据默认必需。三个来源和 token 规则见[证据](../concepts/evidence.md)。

## 可直接抄的例子

[`examples/`](../../../examples/README.md) 里有完整 workflow：

- [pr-comment-gate.yml](../../../examples/pr-comment-gate.yml)：带 policy job 的 PR 门禁；
- [manual-dispatch.yml](../../../examples/manual-dispatch.yml)：维护者手动贴回执；
- [hardware-evidence.yml](../../../examples/hardware-evidence.yml)：GPU 运行加证据包；
- [multi-job.yml](../../../examples/multi-job.yml)：一个 commit 两个 job；
- [path-gate.yml](../../../examples/path-gate.yml)：只有 `patches/` 下的改动需要回执；
- [reuse-local-run.yml](../../../examples/reuse-local-run.yml)：验证已经在别处跑过的任务。
