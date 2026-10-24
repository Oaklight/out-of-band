# 先例与替代方案

[English](../en/prior-art.md) | [中文](prior-art.md)

out-of-band 卡在一个很窄的位置。下面这些工具解决的是相邻问题，其中几个在条件满足时是更好的选择。

## 机制本身不新

Jenkins、Buildkite、CircleCI 很多年前就能通过 commit status 和 Checks API，把 GitHub 之外的结果报回来。发布一个结论这件事，没有任何新东西。

这里的差别在回执：一份签名，绑定仓库、commit、tree、job 和证据 digest；验证方从默认分支读 `allowed_signers`。操作员机器上不需要 GitHub 凭据，结果有三种状态，而不是两种。

## GitHub 的 artifact attestation

`actions/attest-build-provenance` 和 `gh attestation verify` 为 workflow 里构建的产物生成、校验 Sigstore 背书的 provenance。身份来自 workflow 的 OIDC token，attestation 存在 GitHub。

任务确实在 Actions 里跑，这就是对的工具。HPC 登录节点、租来的 GPU 上没有这个身份，而那正是 out-of-band 要管的情况。

## Sigstore，keyless

Keyless 签名从 Fulcio 拿一张短期证书，证书绑在 OIDC 身份上，签名再记进 Rekor。两者都要网络，也要有签发方。目标场景里的机器两样都没有。

Sigstore 也可以用密钥离线签一个 blob，这部分是重叠的。它不提供的是 GitHub 这一侧的策略：哪把钥匙能代表这个仓库说话、声明覆盖哪个 commit 和哪份证据、什么能挡住合并。这层策略是 out-of-band 的主体。

out-of-band 没有透明日志。长期记录是 PR 评论；除非上传证据包，证据留在操作员手里。

## SLSA 与 provenance 框架

SLSA 描述的是构建 provenance 和等级。回执是操作员的声明，不是构建者身份声明。out-of-band 不构成任何 SLSA 等级，也不假装构成。

in-toto 在精神上最接近：对供应链各步骤的签名声明，再用 layout 规定谁能证明什么。它表达力更强，但也需要 layout 和验证器。out-of-band 故意两样都不要。

## 同一细分里的先例

这些是设计参考，不是依赖。该记的功劳要记：

- [`fredericrous/attest`](https://github.com/fredericrous/attest)：`ssh-keygen` 加 `allowed_signers`、tree 绑定、拒绝脏工作区。它故意是 fail-open 的，因为它的目的是跳过重复工作，而不是挡住合并。
- [`Praxso/attested`](https://github.com/Praxso/attested)：receipt / verify check / evidence digest 这套词汇，以及“两个 check”（一个给人看，一个是必需的）的思路。它的 keyless 签名把自己绑在了 Actions 上。
- [`AdriaBA/veriforge-attest`](https://github.com/AdriaBA/veriforge-attest)：很早，也没有 license；没有借用任何东西。
- [`LouisBrunner/checks-action`](https://github.com/LouisBrunner/checks-action)：Checks API 的惯用写法。

## 什么时候该用别的

- 任务能在 Actions 里跑：用托管 runner；需要 provenance 就用 artifact attestation。
- 机器能跑 runner，你也管得住上面执行什么：self-hosted runner 比回执简单。
- 你需要透明日志或可验证的构建身份：Sigstore、in-toto 才是那一层。
- 你需要的是“有人批准”，不是证据：review 或 environment 规则就够了。

out-of-band 管的是剩下的那种：一个必需检查、任务跑在 GitHub 够不着的地方、那台机器上不能有凭据。
