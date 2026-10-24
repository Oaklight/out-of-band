# 场景：多个 job、多台机器

[English](../en/scenario-multi-job.md) | [中文](scenario-multi-job.md)

同一个 commit 可以由多个 job 背书：老 GPU 上的冒烟测试、新卡上的 benchmark、集群上的数值检查。每个 job 有自己的回执和 check。

## 一个回执一个调用 job

调用可复用 workflow 的 job 不能带 matrix，所以按名字各写一个：

```yaml
jobs:
  v100:
    uses: Oaklight/outboard/.github/workflows/verify.yml@<full-sha>
    with:
      pr: ${{ github.event.pull_request.number }}
      commit: ${{ github.event.pull_request.head.sha }}
      job: v100-smoke
      check-name: v100-smoke-verified
      trusted-authors: your-login

  a100:
    uses: Oaklight/outboard/.github/workflows/verify.yml@<full-sha>
    with:
      pr: ${{ github.event.pull_request.number }}
      commit: ${{ github.event.pull_request.head.sha }}
      job: a100-bench
      check-name: a100-bench-verified
      required: false
      trusted-authors: your-login
```

每次调用只读回执里 `job` 与自己相同的那条，所以两份回执可以分别发在同一个 PR 的两条评论里。收集器按 job 过滤就是为这个：不过滤的话，同一 commit 上两份都有效的回执会被当成互相矛盾。

`required: false` 是可选平台的做法。没有回执时结论是 `not applicable`、conclusion 为 `success`，PR 不会被当时恰好拿不到的硬件拖住。

## "至少有一个"怎么写

分支保护要求每一个列出的 check 都通过，没有 OR。如果策略是"任一平台通过即可"，加一个汇总 job：

```yaml
  any-platform:
    needs: [v100, a100]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - env:
          V100: ${{ needs.v100.outputs.verdict }}
          A100: ${{ needs.a100.outputs.verdict }}
        run: |
          if [ "$V100" = "verified" ] || [ "$A100" = "verified" ]; then
            exit 0
          fi
          echo "no platform verified: v100=$V100 a100=$A100"
          exit 1
```

分支保护改成要求 `any-platform`，不要要求单个平台。如果每个平台都必须过，那就反过来：逐个要求，去掉汇总。

## 命名

- `job` 在回执里面，是操作员的 `--job`。
- `check-name` 是分支保护的抓手，名字应该说明测了什么，而不是谁测的。
- 两者都别改。改了以后，旧回执或旧保护会悄悄失效。

## 证据

每次调用有自己的 `evidence-url`。一个包覆盖多个 job 时，要么每个 job 对同一目录各签一份（digest 相同），要么把目录拆开。对不上签名 digest 的包会得到 `E_EVIDENCE_MISMATCH`。
