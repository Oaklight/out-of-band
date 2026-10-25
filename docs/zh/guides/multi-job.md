# 指南：多个 job 或多台机器

[English](../../en/guides/multi-job.md) | [中文](multi-job.md)

一个 commit 可以被多个 job 背书：旧 GPU 上的冒烟测试、新 GPU 上的 benchmark、集群上的数值检查。每个 job 有自己的回执和 check。

## 一份回执一个调用

用可复用 workflow 时，调用它的 job 不能带 matrix，所以每个名字声明一个 job：

```yaml
jobs:
  v100:
    uses: Oaklight/out-of-band/.github/workflows/verify.yml@<full-sha> # v0.5.0
    with:
      pr: ${{ github.event.pull_request.number }}
      commit: ${{ github.event.pull_request.head.sha }}
      job: v100-smoke
      check-name: v100-smoke-verified
      trusted-authors: your-login

  a100:
    uses: Oaklight/out-of-band/.github/workflows/verify.yml@<full-sha> # v0.5.0
    with:
      pr: ${{ github.event.pull_request.number }}
      commit: ${{ github.event.pull_request.head.sha }}
      job: a100-bench
      check-name: a100-bench-verified
      required: false
      trusted-authors: your-login
```

这段配置省略了证据来源。给每个调用加 `evidence-url` 或 `evidence-file`，或者设
`require-evidence: false`。

用 [action](../reference/action.md) 时，同样的形状可以放进一个带 matrix 的 job：

```yaml
jobs:
  verify:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - job: v100-smoke
            check: v100-smoke-verified
          - job: a100-bench
            check: a100-bench-verified
    steps:
      - uses: Oaklight/out-of-band@<full-sha> # v0.5.0
        with:
          commit: ${{ github.event.pull_request.head.sha }}
          job: ${{ matrix.job }}
          check-name: ${{ matrix.check }}
```

两种写法都是每个 job 名一个 check。action 省掉重复的 job 声明；workflow 给每份回执独立的 job 边界。[multi-job.yml](../../../examples/multi-job.yml) 是完整的 action 写法。

每个调用只读 `job` 等于自己的那份回执，所以几份回执可以分开发在不同的 PR 评论里。收集时按 job 过滤也是这个原因：一个 commit 上两份都有效但内容不同的回执，否则看起来就像互相矛盾。

`required: false` 是可选平台的写法。回执缺失会变成 `not applicable`，结论为 `success`，PR 不会因为硬件碰巧不可用而被扣住。

## 要求“至少一个”

分支保护要求每个列出的 check 都通过，没有 OR。如果策略是“这些平台任意一个”，加一个汇总 job：

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

分支保护里要求 `any-platform`，不要再单独要求那两个 check。如果每个平台都必须通过，反过来做：逐个要求，不要汇总 job。

## 命名

- `job` 在回执里面，就是操作员的 `--job`。
- `check-name` 是分支保护的抓手。它应该说明测了什么，而不是谁跑的。
- 两个都别改。改了之后，已有回执或已有保护会悄悄失效。

## 证据

除非设 `require-evidence: false`，每个调用都要有自己的证据来源。如果一份归档覆盖多个 job，就针对同一个目录给每个 job 各签一份回执，让摘要一致，然后让每个调用指向同一个归档。也可以按 job 拆目录。

归档和签名摘要对不上就是 `E_EVIDENCE_MISMATCH`。三个来源和限制见[证据](../concepts/evidence.md)。
