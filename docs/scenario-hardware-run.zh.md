# 场景：记录一次 benchmark 或模型运行

[English](scenario-hardware-run.md) | [中文](scenario-hardware-run.zh.md)

运行发生在 GitHub 够不着的机器上：租来的 V100、实验室服务器、集群。你希望结果挂在某个 commit 上，半年后回来看还能看懂。

## "挂在 commit 上"是什么意思

check run 属于 commit，不属于分支、release 或某个人。所以第一步是决定为哪个 commit 背书。

- 正在评审的 PR：head commit，接法同[补丁门禁](scenario-patch-gate.zh.md)。
- release 或 tag：tag 指向的 commit。这类没有 PR 可评论，用 dispatch 提交。
- 长期分支：推送后的那个 commit，事后补交，见[分支门禁](scenario-branch-gate.zh.md)。

## 签名

```bash
# 在跑任务的那台机器上，不需要网络。
outboard sign \
  --job v100-bench \
  --commit 6e5b8a482f1baf41c8080b79501294cbf4057987 \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/outboard \
  --repo owner/repo \
  --output-file ./summary.txt \
  --out receipt.md
```

证据目录要小而有信息量：命令行、日志、以后还想看的数字。`outboard pack` 把它们打成确定性的压缩包：

```bash
outboard pack --evidence-dir ./evidence --out evidence.tgz
```

回执里的 digest 覆盖目录内容，签了什么就绑定了什么。签完再打包也可以；包里的文件必须和签名时一致。

## 交付证据

验证方可以把压缩包取下来存成 artifact，需要一个 GitHub runner 能访问的 HTTPS 地址：

```bash
gh workflow run bench-gate.yml \
  -f commit=6e5b8a482f1baf41c8080b79501294cbf4057987 \
  -F receipt=@receipt.md \
  -f evidence-url=https://example.com/evidence/6e5b8a4.tgz
```

`-F` 从文件读值，多行文本经过 shell 时那些引号麻烦就都没了。

常见放法：同仓库的 `evidence/<sha>` 分支、release asset、对象存储的签名 URL。传输通道本身不需要可信：workflow 会重新算 digest，和签名对不上就拒绝发布。

限额：单个包 50 MiB，`output` 4 KiB。挑重点。完整的训练日志应该进 artifact 存储，不该塞进回执。

## 只用 dispatch 的门禁

不靠 PR 把关的仓库，一个小的调用方就够了：

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
    uses: Oaklight/outboard/.github/workflows/verify.yml@<full-sha>
    with:
      pr: "0"
      commit: ${{ inputs.commit }}
      job: v100-bench
      check-name: v100-bench-verified
      receipt: ${{ inputs.receipt }}
      evidence-url: ${{ inputs.evidence-url }}
```

`pr: "0"` 表示不扫评论、也不发置顶评论。check 建在 `inputs.commit` 上；workflow 本身可以从任何分支手动触发。

也可以给更早的 commit 补交回执。check 出现在那个 commit 上，而不是分支头。这正是重点：它说的是"被测过的那份代码"，不是"现在的分支"。

## 长任务

门禁不会等。它由事件触发——PR 更新、评论、手动 dispatch——只看触发那一刻已经存在的回执，几秒内结束。任务跑三小时还是三天都无所谓：跑完再签、再发评论。

真实的限制只有这些：

- 验证 job 本身 5 分钟超时；下载证据给 120 秒。两者都和任务跑了多久无关。
- 任务进行中如果 PR head 变了，回执写的是旧 head，会被当成 `E_WRONG_COMMIT` 忽略。给新 head 重新签。
- 回执不会过期。按 commit 签，不要按天签。如果策略要求"最近跑过"，那要在门禁之外实现。
- 必须的 check 从没跑过时，PR 会一直卡着。硬件测试还没做完时，这通常正是你要的效果。

## 看结果

- check run 里是结论，output 里是声明和折叠的 `output` 文本。
- run 的 step summary 再写一遍结论、来源和证据状态。
- 上传了包的话，run 里会有 `outboard-evidence`，受 Actions 保留期限制（默认 90 天）。
- 有 PR 评论的话，那条评论才是长期记录，check 不是。

## 强制推送之后

commit 只要还能按 SHA 访问，check 就还在。分支不再包含它时，分支页面上看不到。代码改写后要重新签新 commit；回执不会跟着走。
