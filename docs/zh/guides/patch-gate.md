# 指南：补丁测过才能合并

[English](../../en/guides/patch-gate.md) | [中文](patch-gate.md)

假设 `patches/`、固件目录或其他某个路径下的改动，必须在真实硬件上做冒烟测试。CI 跑不了这个测试，所以由操作员跑完再签名。

这是“GitHub 跑不了”的情况。同一套门禁也适用于测试已经在工作站上跑过、只是不想再跑一遍的情况，区别只在签名理由。

## workflow

两个 job：`policy` 判断这个 PR 是否需要回执，`verified` 调用可复用 workflow。

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
    # 带标记的评论才重跑，其他评论忽略。
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
      - name: 解析 PR 和 head
        id: context
        env:
          GH_TOKEN: ${{ github.token }}
          PR_NUMBER: ${{ github.event.pull_request.number || github.event.issue.number }}
        run: |
          commit="$(gh api "repos/$GITHUB_REPOSITORY/pulls/$PR_NUMBER" --jq .head.sha)"
          echo "pr=$PR_NUMBER" >> "$GITHUB_OUTPUT"
          echo "commit=$commit" >> "$GITHUB_OUTPUT"

      - name: 判断是否需要回执
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
    uses: Oaklight/out-of-band/.github/workflows/verify.yml@<full-sha> # v0.5.0
    with:
      pr: ${{ needs.policy.outputs.pr }}
      commit: ${{ needs.policy.outputs.commit }}
      job: patch-smoke
      required: ${{ needs.policy.outputs.requires == 'true' }}
      check-name: patch-smoke-verified
      trusted-authors: your-login
```

两种触发方式都用 API 解析 head。在 `issue_comment` 事件里，`github.sha` 是默认分支，不是 PR head，事件上下文不能直接用。

参数含义：

- `job` 是回执里的名字。操作员签名时要用同一个字符串。
- `check-name` 是分支保护匹配的字符串。每个 job 用不同的名字。
- `required: false` 会把缺失的回执变成 `not applicable`，结论为 `success`，只改文档的 PR 不会被挡住。
- `trusted-authors` 限定谁能提供回执。不设时，owner、member、collaborator 都算。

## 操作员做什么

```bash
# 1. 拿到被推送的那个 commit。
gh pr checkout 5            # 或：git fetch origin pull/5/head:pr-5
git rev-parse HEAD          # 6e5b8a4...

# 2. 跑测试，留下证据。
mkdir -p /tmp/evidence
./run-smoke.sh 2>&1 | tee /tmp/evidence/smoke.log

# 3. 签名。离线运行；私钥不离开这台机器。
oob sign \
  --job patch-smoke \
  --commit "$(git rev-parse HEAD)" \
  --result pass \
  --evidence-dir /tmp/evidence \
  --key ~/.ssh/out-of-band \
  --repo owner/repo \
  --claims evidence_url=https://example.com/evidence.tgz \
  --output-file /tmp/evidence/last-lines.txt \
  --out receipt.md

# 4. 交付。可信账号发一条 PR 评论，是最常见的通道。
oob render --block receipt.md --out comment.md
gh pr comment 5 --body-file comment.md
```

`--output-file` 可选，最多 4 KiB，会出现在 check 折叠起来的输出里，审阅的人先看这里。不要放密钥，check 是公开的。

证据默认必需。验证方会从 `evidence-file`、`evidence-url` 或 `claims.evidence_url` 拿归档。上面的签名命令把地址签进了 claim，所以一条评论就自带证据位置。补丁测试的证据通常不大，打包后放到 runner 能访问的地方：

```bash
oob pack --evidence-dir /tmp/evidence --out evidence.tgz
```

不想存归档，就在调用时设 `require-evidence: false`，回执里的摘要就是唯一的证据记录。

## workflow 从哪来

`pull_request` 用的是 PR 合并提交里的 workflow 文件。贡献者因此可以改审判自己的门禁：改 `required`，用期望的名字发一个绿色 check，或者删掉 job 让必需的 check 一直缺失。分支保护分辨不出来。

`pull_request_target` 用的是默认分支的副本，带可写 token，fork PR 也一样。所以例子用它触发。代价是这条规则：这个 workflow 里绝不能 checkout 或执行 PR 代码。验证方从默认分支读 `allowed_signers`，把回执当数据。

## 固定版本和升级

`uses:` 那一行写在默认分支上，普通 PR 不会碰它。升级是另一个小 PR；两个升级 PR 改同一行会像其他改动一样冲突，所以一次合一个。

ref 的几种写法：

- **完整 commit SHA**（推荐）：不可变。后面加 `# v0.5.0` 注释，让工具知道版本，也让 Dependabot 去开升级 PR。
- **release tag**：短一些，但 tag 可以被移到别的 commit。
- **默认分支**：永远最新，永远没审过。门禁不要这么用。
- **本地副本**（`uses: ./.github/workflows/verify.yml`）：没有外部固定，但验证器和它的升级都归你维护。

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
```

## 你要改哪些地方

workflow 是模板，但真正要你定的只有几处。`${{ }}` 里的内容由 GitHub 在运行时求值，不用你填。

| 占位符 | 是什么 |
| --- | --- |
| `uses:` 里的 `<full-sha>` | 你固定的 out-of-band commit，从 release 页面复制 |
| `job:` | 必须和操作员的 `--job` 一致 |
| `check-name:` | 分支保护匹配的字符串，每个 job 唯一 |
| `trusted-authors:` | 可选；你的 GitHub 登录名，或逗号分隔的列表 |

照着这一页抄调用方 workflow，其他地方不用改。

## 只写一次

调用方 workflow 提交到默认分支一次就够了。新的 PR 需要的是回执，不是改 workflow：`policy` 在运行时解析 head 和改动路径。换固定的 SHA 是你安排的升级；加一个平台，就是加一个调用 job，也只加一次。

## 接下来发生什么

评论触发 workflow，因为块里的标记满足 `policy` 条件。验证方读取 PR 评论，保留可信作者的，挑出 head commit 和 `patch-smoke` 对应的块，验签，然后发布 `patch-smoke-verified`。

PR 有了新推送之后，旧回执不再匹配 head，会被忽略。给新 commit 签一份、再发一条评论即可，旧的不需要删。

## 出问题的时候

| 现象 | 原因 |
| --- | --- |
| `E_WRONG_COMMIT` | 签的是合并提交或旧的 head；看 `git rev-parse HEAD` |
| `E_WRONG_JOB` | `--job` 和 `job:` 参数不一致 |
| `E_BAD_SIGNATURE` | 钥匙不在默认分支的 `allowed_signers` 里 |
| `E_MULTI_BLOCK` | 同一个 commit 和 job 有两份不同的回执；删掉一份 |
| `E_NO_EVIDENCE` | 要求证据，但没提供归档 |
| 完全没有 check | workflow 没跑；看 Actions 页面和 `if:` 条件 |

## 注意

- 这个 workflow 带可写 token，fork PR 也一样，所以不要 checkout 或执行 PR 代码。
- fork PR 在 `pull_request` 下拿到的是只读 token。`pull_request_target` 和 `issue_comment` 都绕开这个问题；例子用前者，这样每次推送都会自动跑，不用等评论。
- 运行更大、需要带归档的场景，见[硬件运行](hardware-run.md)。
