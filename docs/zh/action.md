# 用 action 还是 workflow

可复用 workflow 是一个 job，action 是一个 step。两者跑同一套验证逻辑，发同一种 check run，区别只在外面那层由谁来写。

想把它塞进现有 job，或者想自己控制触发器、权限、并发，又或者用户是在 Marketplace 上找到的，用 action。想让验证独占一个 runner、有自己的超时和 job 边界，用[可复用 workflow](../../README_zh.md#接到自己的仓库)。

| | Action | 可复用 workflow |
| --- | --- | --- |
| 调用位置 | step，`uses: Oaklight/out-of-band@v0.5.0` | job，`uses: Oaklight/out-of-band/.github/workflows/verify.yml@<sha>` |
| Runner | 调用方的 job | 自己的 `ubuntu-latest` job |
| 权限 | 调用方设置 | workflow 自己声明 |
| 超时、并发 | 调用方设置 | 内置 |
| Marketplace | 可以上架 | 不能上架 |

## 调用方要自己写的东西

这些 action 声明不了，都属于调用它的 workflow：

- 触发器，通常是 `pull_request_target` 加 `issue_comment`
- `permissions: contents: read, checks: write, pull-requests: write`
- token，默认是 `${{ github.token }}`
- `check-name`，分支保护匹配的就是这个字符串
- 回执要对应的 commit 和 job 名

## 输入

| 输入 | 默认值 | 含义 |
| --- | --- | --- |
| `commit` | 必填 | 回执里必须出现的 commit SHA |
| `job` | 必填 | 回执里必须出现的 job 名 |
| `pr` | `0` | 用来收集评论和发汇总的 PR 号；`0` 表示都不用 |
| `required` | `true` | 这个 commit 是否必须有回执 |
| `check-name` | `oob` | check run 的名字 |
| `receipt` | 空 | 直接传入回执文本，优先于评论 |
| `allowed-signers` | `.github/allowed_signers` | 调用方仓库里的路径，从默认分支读取 |
| `trusted-authors` | 空 | 允许提交回执的登录名，逗号分隔 |
| `evidence-url` | 空 | 证据 `.tar.gz` 的 HTTPS 地址 |
| `report` | `true` | 发布 check run 和 sticky 评论；`false` 只计算结论 |
| `version` | `0.4.0` | 安装的 out-of-band 版本；留空则不装 |
| `source` | 空 | 改为从本地路径安装，供开发和自测使用 |
| `python-version` | `3.12` | 验证器使用的 Python |
| `token` | `${{ github.token }}` | API token，权限见上 |

输出只有一个 `verdict`：`verified`、`failed`、`unverified` 或 `not applicable`。

## 等操作员提交回执

action 不会挂在那里轮询。每次事件都是一次新的 run：

1. PR 打开，workflow 跑一遍，找不到回执，发一个 `unverified` 的 check，不通过。
2. 操作员在受限机器上跑完，把签好的回执贴成 PR 评论。
3. `issue_comment` 再触发一次 workflow。
4. action 找到 `commit` 和 `job` 都对得上的那段，验签，发出同名的 check。分支保护看到的是新结果。

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

      - uses: Oaklight/out-of-band@v0.5.0
        with:
          pr: ${{ steps.context.outputs.pr }}
          commit: ${{ steps.context.outputs.commit }}
          job: bench-smoke
          check-name: receipt-verified
```

## 安全上的几件事

- 在 `pull_request_target` 下，action 不 checkout、也不执行 PR 里的代码。`allowed_signers` 通过 API 从默认分支读，PR 改不了自己的信任根。
- 真门禁里 `uses:` 用完整 commit SHA 固定。示例里的 tag 只是好读，不是不可变。
- 调用方的 `permissions` 是上限。job 没给 `checks: write`，action 也加不出来。
- CLI 按 `version` 从 PyPI 安装。只有本仓库自测才把 `source` 指到本地。

## 可以直接抄的例子

[`examples/`](https://github.com/Oaklight/out-of-band/tree/main/examples) 下每个场景一份完整 workflow：

- [pr-comment-gate.yml](https://github.com/Oaklight/out-of-band/blob/main/examples/pr-comment-gate.yml)：评论提交回执的 PR 门禁
- [manual-dispatch.yml](https://github.com/Oaklight/out-of-band/blob/main/examples/manual-dispatch.yml)：维护者手动填回执
- [hardware-evidence.yml](https://github.com/Oaklight/out-of-band/blob/main/examples/hardware-evidence.yml)：GPU 跑完带证据包
- [multi-job.yml](https://github.com/Oaklight/out-of-band/blob/main/examples/multi-job.yml)：一个 commit 两个 job
- [path-gate.yml](https://github.com/Oaklight/out-of-band/blob/main/examples/path-gate.yml)：只有 `patches/` 需要回执
- [reuse-local-run.yml](https://github.com/Oaklight/out-of-band/blob/main/examples/reuse-local-run.yml)：复用已经在别处跑完的结果
