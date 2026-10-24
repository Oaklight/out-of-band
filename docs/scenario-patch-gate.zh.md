# 场景：补丁合并前先测

[English](scenario-patch-gate.md) | [中文](scenario-patch-gate.zh.md)

仓库里有一个 `patches/` 目录（也可能是 `src/`、固件目录），改动必须在真机上跑过冒烟测试。CI 做不了这件事，就由人来跑，然后签个名。

## workflow

两个 job：`policy` 判断这个 PR 要不要回执，`verified` 调用可复用 workflow。

```yaml
name: receipt gate

on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  issue_comment:
    types: [created]

permissions:
  contents: read
  checks: write
  pull-requests: write

jobs:
  policy:
    # 带标记的评论才重跑，其他评论一概不理。
    if: >
      github.event_name == 'pull_request' ||
      (github.event_name == 'issue_comment' &&
       github.event.issue.pull_request != null &&
       contains(github.event.comment.body, '<!-- receipt:v1 -->'))
    runs-on: ubuntu-latest
    outputs:
      pr: ${{ steps.context.outputs.pr }}
      commit: ${{ steps.context.outputs.commit }}
      requires: ${{ steps.paths.outputs.requires }}
    steps:
      - name: Resolve the PR and its head
        id: context
        env:
          GH_TOKEN: ${{ github.token }}
          PR_NUMBER: ${{ github.event.pull_request.number || github.event.issue.number }}
        run: |
          commit="$(gh api "repos/$GITHUB_REPOSITORY/pulls/$PR_NUMBER" --jq .head.sha)"
          echo "pr=$PR_NUMBER" >> "$GITHUB_OUTPUT"
          echo "commit=$commit" >> "$GITHUB_OUTPUT"

      - name: Decide whether a receipt is required
        id: paths
        env:
          GH_TOKEN: ${{ github.token }}
          PR: ${{ steps.context.outputs.pr }}
        run: |
          if gh api --paginate "repos/$GITHUB_REPOSITORY/pulls/$PR/files?per_page=100" \
               --jq '.[].filename' | grep -qE '^(patches|firmware)/'; then
            echo "requires=true" >> "$GITHUB_OUTPUT"
          else
            echo "requires=false" >> "$GITHUB_OUTPUT"
          fi

  verified:
    needs: policy
    uses: Oaklight/outboard/.github/workflows/verify.yml@<full-sha>
    with:
      pr: ${{ needs.policy.outputs.pr }}
      commit: ${{ needs.policy.outputs.commit }}
      job: patch-smoke
      required: ${{ needs.policy.outputs.requires == 'true' }}
      check-name: patch-smoke-verified
      trusted-authors: your-login
```

两种触发都通过 API 取 head。在 `issue_comment` 事件里，`github.sha` 指向默认分支而不是 PR head，不能直接拿事件上下文来用。

几个输入的含义：

- `job` 是回执里的名字，操作员签名时必须写同一个字符串。
- `check-name` 是分支保护匹配的名字，每个 job 要唯一。
- `required: false` 时，没有回执会得到 `not applicable` 和 `success`，纯文档 PR 不会被卡住。
- `trusted-authors` 限定谁有资格提交回执；不填的话，owner、member、collaborator 都算。

## 操作员做什么

```bash
# 1. 取到实际推送的那个 commit。
gh pr checkout 5            # 或者 git fetch origin pull/5/head:pr-5
git rev-parse HEAD          # 6e5b8a4...

# 2. 跑测试，把证据留下。
mkdir -p /tmp/evidence
./run-smoke.sh 2>&1 | tee /tmp/evidence/smoke.log

# 3. 签名。离线完成，私钥不离开这台机器。
outboard sign \
  --job patch-smoke \
  --commit "$(git rev-parse HEAD)" \
  --result pass \
  --evidence-dir /tmp/evidence \
  --key ~/.ssh/outboard \
  --repo owner/repo \
  --output-file /tmp/evidence/last-lines.txt \
  --out receipt.md

# 4. 交付。用有权限的账号发一条 PR 评论。
gh pr comment 5 --body-file receipt.md
```

`--output-file` 可选，最多 4 KiB，会出现在 check 里可折叠的记录中，评审通常先看这里。别往里面放密钥；check 是公开的。

## 需要你替换什么

workflow 是模板，但真正要你定的只有三处，另有一处可选。`${{ }}` 里的表达式由 GitHub 在运行时求值，不用管。

| 占位符 | 是什么 |
| --- | --- |
| `uses:` 里的 `<full-sha>` | 你要固定的 outboard commit，从 release 页面复制 |
| `job:` | 必须和操作员的 `--job` 一致 |
| `check-name:` | 分支保护匹配的字符串，所以每个 job 要唯一 |
| `trusted-authors:` | 可选；你的 GitHub 登录名，或逗号分隔的列表 |

如果直接抄这一页的调用方 workflow，其余地方都不用改。

## 只写一次

调用方 workflow 提交到默认分支一次就够了。之后每个 PR 需要的是回执，不是改 workflow：`policy` 会在运行时解析 head 和改动的路径。改固定的 SHA 是计划内的升级；加一个平台，就是加一个调用 job，也只加一次。

## 之后会发生什么

评论会触发 workflow：回执里的标记正好命中 `policy` 的条件。验证方读取 PR 评论，只看有权限的作者，挑出 head commit 和 `patch-smoke` 对应的那一条，验签，然后发布 `patch-smoke-verified`。

如果 PR 又推了新提交，旧回执对不上 head，会被忽略。给新 commit 重新签一条、再发评论即可，不用删旧的。

## 常见问题

| 现象 | 原因 |
| --- | --- |
| `E_WRONG_COMMIT` | 签的是 merge commit 或更早的 head；重新看 `git rev-parse HEAD` |
| `E_WRONG_JOB` | `--job` 和 `job:` 输入不一致 |
| `E_BAD_SIGNATURE` | 公钥不在默认分支的 `allowed_signers` 里 |
| `E_MULTI_BLOCK` | 同一个 commit、同一个 job 有两份不同的回执；删掉一份 |
| check 完全没出现 | workflow 没跑；看 Actions 页面和 `if:` 条件 |

## 注意

- 验证 job 不要 checkout PR head。workflow 故意从默认分支读 `allowed_signers`。
- fork 来的 PR 在 `pull_request` 下只有只读 token。用上面示范的 `issue_comment`，或者 `pull_request_target`。
- 证据上传是可选的。需要日志时加 `evidence-url`，见[硬件运行](scenario-hardware-run.zh.md)。
