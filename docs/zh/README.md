# 文档

[English](../en/README.md) | [中文](README.md)

会走到这里的任务有两种：

- GitHub 跑不了的任务：硬件、工具链、网络或数据在别处；
- 已经在别处跑过的任务，在 CI 里重跑太慢、不稳定，或者结果对不上。

两种情况下，跑任务的机器签一份很短的声明，GitHub 上的 workflow 验签，再把结论发布成 check。签名机不需要被访问，也不需要 GitHub 凭据。

想先看一遍再读细节？[走一遍导览](https://oaklight.github.io/out-of-band/)。

## 按你手上的事来选

| 你的场景 | 读这篇 |
| --- | --- |
| 装上，签出第一份回执 | [快速上手](start.md) |
| 回执到底绑定了什么 | [回执](concepts/receipt.md) |
| 哪把钥匙算数，门禁不证明什么 | [信任](concepts/trust.md) |
| 把日志或输出随回执一起交 | [证据](concepts/evidence.md) |
| 四种结论分别是什么意思 | [状态](concepts/states.md) |
| 查一个命令、参数或退出码 | [CLI](reference/cli.md) |
| 把验证器当 step 用 | [action](reference/action.md) |
| 把验证器当 job 用 | [可复用 workflow](reference/workflow.md) |
| 补丁测过才能合并 | [补丁门禁](guides/patch-gate.md) |
| 把 benchmark 或模型运行记到某个 commit 上 | [硬件运行](guides/hardware-run.md) |
| 多台机器、多个 job | [多 job](guides/multi-job.md) |
| 不经过 PR，给分支上的推送做背书 | [分支门禁](guides/branch-gate.md) |
| 签名机没有外网 | [离线机器](guides/air-gapped.md) |
| 生成、轮换密钥，或排查结论 | [运维](operations.md) |
| 看自测跑出来的证据 | [验证记录](validation.md) |
| 和 Sigstore、attestation 以及同类项目的关系 | [先例与替代方案](prior-art.md) |
| 常见反对意见的直说 | [FAQ](faq.md) |

## 共同的结构

1. **回执。** 一行 JSON 加一段 SSH 签名。操作员在跑任务的机器上用 `oob sign` 生成，不需要网络，也不需要 GitHub 凭据。
2. **验证方。** workflow 或 action 用默认分支上的 `allowed_signers` 验签，再核对仓库、commit、tree 和 job。
3. **check run。** GitHub 把结论挂到 commit 上，分支保护按名字匹配。

这个仓库负责机制，使用者负责策略：哪些路径需要回执、job 叫什么、用哪把钥匙、这个 check 是否必需。

四种状态表在[状态](concepts/states.md)。

## 两个译名

`gate` 译作“门禁”：允许或阻止合并的策略。`check` / `check run` 保留英文，或译作“检查”：GitHub 上那个具体的结果。门禁靠 check 落地，但两者不是一回事。

## 动手之前

- workflow 或 action 用完整 commit SHA 固定。tag 是会动的。
- `allowed_signers` 放在默认分支的 `.github/` 下。它是信任根，PR 改不动自己的信任根。
- `check-name` 定下来就别改。分支保护匹配的是字符串，改名等于悄悄换掉了受保护的东西。
