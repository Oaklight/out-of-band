# 指南：记录一次 benchmark 或模型运行

[English](../../en/guides/hardware-run.md) | [中文](hardware-run.md)

一次运行发生在 GitHub 够不到的机器上：租来的 V100、实验室服务器、集群。你想把结果挂到一个 commit 上，半年后回来看仍然有足够的信息。

## “挂上去”是什么意思

check run 属于 commit，不属于分支、release 或某个身份。第一个要定的是：你在为哪个 commit 背书。

- 正在审的 PR：head commit。接法和[补丁门禁](patch-gate.md)一样。
- release 或 tag：tag 指向的 commit。没有 PR 可以评论，用 dispatch 提交。
- 长期分支：推送上去的 commit，事后提交。[分支门禁](branch-gate.md)讲这种情况。

## 签名

```bash
# 在跑任务的机器上。不需要网络。
oob sign \
  --job v100-bench \
  --commit 6e5b8a482f1baf41c8080b79501294cbf4057987 \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/out-of-band \
  --repo owner/repo \
  --output-file ./summary.txt \
  --out receipt.md
```

证据目录尽量小、尽量有用：命令行、日志、以后会查的数字。`oob pack` 把它打成确定性的归档：

```bash
oob pack --evidence-dir ./evidence --out evidence.tgz
```

回执里的摘要覆盖目录内容，签了什么就绑定什么。签完再打包没关系，归档里的文件必须完全一致。

`--output-file` 可选，上限 4 KiB。它是审阅者在 check 摘要下折叠看到的部分，把关键数字放这里，完整日志留给归档。

## 交付证据

证据默认必需。验证方可以取回归档并留成 artifact；来源可以是 runner 能访问的 HTTPS 地址，也可以是 runner 上的路径（`evidence-file`）。

```bash
gh workflow run bench-gate.yml \
  -f commit=6e5b8a482f1baf41c8080b79501294cbf4057987 \
  -F receipt=@receipt.md \
  -f evidence-url=https://example.com/evidence/6e5b8a4.tgz
```

`-F` 从文件读值，省掉多行块在 shell 里的引号问题。

归档常见放法：同一个仓库的 `evidence/<sha>` 分支、release asset、带签名 URL 的对象存储。通道不需要可信，workflow 会重新算摘要，对不上就不发布通过。

如果归档不离开 runner，用 `evidence-file` 代替 `evidence-url`。完全不想交归档，就设 `require-evidence: false`；回执里仍然有摘要，摘要会写 `digest only`。

大小限制：单个归档 50 MiB，`output` 4 KiB。要取舍。完整训练日志属于 artifact 存储，不属于回执。

## 只有 dispatch 的门禁

不 gate PR 的仓库，一个小调用方就够了：

```yaml
name: bench gate

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
      job: v100-bench
      check-name: v100-bench-verified
      receipt: ${{ inputs.receipt }}
      evidence-url: ${{ inputs.evidence-url }}
```

`pr: "0"` 表示不扫评论，也不发固定评论。check 挂在 `inputs.commit` 上，workflow 本身从哪个分支 dispatch 都行。

也可以给更早的 commit dispatch。check 出现在那个 commit 上，而不是分支 head，因为回执说的是被测试的那份代码。

## 长时间运行

门禁从不等待。有事件触发时它才跑（PR 更新、评论、dispatch），检查当时已有的回执，几秒内结束。跑三个小时或三天的 job 是常态：跑完再签，然后贴评论或 dispatch。

真正的限制：

- 可复用 workflow 的 job 5 分钟超时；取证据 120 秒。这两个和 job 跑了多久无关。
- 跑的过程中 PR head 变了，回执指向旧 head，会被当作 `E_WRONG_COMMIT` 忽略。给新 head 重新签。
- 回执不过期。为你关心的每个 commit 签一份，而不是每天签一份。策略要求“最近跑过”，在门禁外面实现。
- 从来没跑过的必需 check 会一直挡住 PR。硬件测试还没完成时，这通常正是你要的。

## 看结果

- check run 显示结论，输出里有 claims 和折叠的 `output` 文本。
- run 的 step summary 重复结论、来源和证据状态，并列出证据清单和有限长度的文本预览。
- 提供了归档的话，run 上有 `oob-evidence`，受 Actions 保留期限制（默认 90 天）。
- 有 PR 评论时，那条评论是长期记录。

## force-push 之后

commit 仍然能按 SHA 访问，check 也跟着它。分支不再包含这个 commit 时，分支上看不到它。代码重写了就给新 commit 签一份；回执不会转移。
