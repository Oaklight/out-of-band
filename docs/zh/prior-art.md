# 先例与替代方案

[English](../en/prior-art.md) | [中文](prior-art.md)

out-of-band 占的是一个很窄的位置。下面这些工具解决的是相邻问题，条件符合时，它们往往是更好的选择。

## 机制本身不新

Jenkins、Buildkite、CircleCI 多年来都在 GitHub 之外跑任务，再通过 commit status 或 Checks API 把结果报回来。发布结论这件事不新。

新的部分是回执：一份签名，覆盖绑定到仓库、commit、tree、job 和证据摘要的声明；验证方从默认分支读 `allowed_signers`。签名机不需要 GitHub 凭据，结果有四种状态，不是两种。

## GitHub artifact attestations

`actions/attest-build-provenance` 和 `gh attestation verify` 为 workflow 里构建的产物生成并校验 Sigstore 背书的 provenance。身份来自 workflow 的 OIDC token，attestation 存在 GitHub 上。

任务在 Actions 里跑，它们就是正确选择。HPC 登录节点或租来的 GPU 没有 workflow 身份可出示，这才是 out-of-band 的位置。

## Sigstore 的无密钥签名

无密钥签名从 Fulcio 取一张绑定 OIDC 身份的短期证书，再把签名记进 Rekor。两者都需要网络和一个签发方，目标场景里的主机两样都没有。

Sigstore 也可以用密钥离线签一个 blob，这部分有重叠。它不提供的是 GitHub 侧的策略：哪把钥匙可以代表这个仓库、声明覆盖哪个 commit 和哪份证据、什么能挡住合并。这套策略层才是这个工具的大部分。

out-of-band 没有透明日志。长期记录是 PR 评论；证据留在操作员那里，除非另交归档。

## SLSA 与 provenance 框架

SLSA 描述构建 provenance 和等级。回执是操作员的背书，不是构建者身份声明。out-of-band 不构成 SLSA 等级，也不声称。

in-toto 在精神上最接近：对供应链步骤的签名声明，再用 layout 规定谁能证明什么。它表达力更强，也需要 layout 和验证器。out-of-band 有意两者都不要。

## 复用已经跑过的运行

第二种使用理由的先例少一些。常见做法是：在 CI 里重跑并接受成本，相信一份贴过来的日志，或者人工批准。它们都不会把结果绑定到 commit 和证据摘要。机制和“GitHub 跑不了”那种情况一样，只是理由不同。

## 同类项目

这些是设计参考，不是依赖。该给的信用要给：

- [`fredericrous/attest`](https://github.com/fredericrous/attest)：`ssh-keygen` 加 `allowed_signers`，绑定 tree，拒绝脏工作区。它有意做成 fail-open，因为目的是跳过重复工作，不是挡合并。
- [`Praxso/attested`](https://github.com/Praxso/attested)：receipt / verify-check / evidence-digest 这套词汇，以及“一个给人看、一个必需”的双 check 思路。它的无密钥签名绑定在 Actions 上。
- [`AdriaBA/veriforge-attest`](https://github.com/AdriaBA/veriforge-attest)：很早，没有许可证；没有借用任何东西。
- [`LouisBrunner/checks-action`](https://github.com/LouisBrunner/checks-action)：Checks API 的惯用写法。

## 什么时候用别的

- 任务能在 Actions 里跑：用托管 runner；需要 provenance 就用 artifact attestations。
- 机器能跑 runner，而且你能控制上面执行什么：自托管 runner 比回执简单。
- 需要透明日志或可验证的构建身份：该用 Sigstore 和 in-toto。
- 需要的是批准，不是证据：review 或 environment 规则就够了。
- 重跑很便宜而且结果稳定：直接重跑。

out-of-band 管剩下的情况：一个必需的 check，任务跑在 GitHub 够不到的地方，或者已经在别处跑过，而且那台机器上没有凭据。
