# 文档

[English](../en/README.md) | [中文](README.md)

有些任务没法在 GitHub 上跑：租来的 GPU 机器上的 benchmark、工作站上的补丁冒烟测试、实验室内网里的一次训练。outboard 让跑任务的机器签一份很短的声明，GitHub 负责验证，再把结论发布成 check run。

下面按你手上的事来选。

想先看一遍再读细节？[走一遍导览](https://oaklight.github.io/outboard/)。

| 你的场景 | 读这篇 |
| --- | --- |
| 补丁测过才能合并 | [补丁门禁](scenario-patch-gate.md) |
| 把 benchmark 或模型运行记到某个 commit 上 | [硬件运行](scenario-hardware-run.md) |
| 不经过 PR，给分支上的推送做背书 | [分支门禁](scenario-branch-gate.md) |
| 多台机器、多个 job | [多 job](scenario-multi-job.md) |
| 签名机没有外网 | [离线机器](offline.md) |
| 生成、轮换密钥，或排查结论 | [运维](operations.md) |
| 看自测跑出来的证据 | [验证记录](validation.md) |
| 和 Sigstore、attestation 以及同类项目的关系 | [先例与替代方案](prior-art.md) |

## 两个译名

`gate` 译作“门禁”：允许或阻止合并的策略。`check` / `check run` 保留英文，或译作“检查”：GitHub 上那个具体的结果。门禁靠 check 落地，但两者不是一回事。

## 共同的结构

不管哪种场景，都是三件事。

1. **回执。** 一行 JSON 加一段 SSH 签名。操作员在跑任务的机器上用 `outboard sign` 生成，不需要网络，也不需要 GitHub 凭据。
2. **验证方。** 可复用 workflow 用默认分支上的 `allowed_signers` 验签，再核对仓库、commit、tree 和 job。
3. **check run。** GitHub 把结论挂到 commit 上，分支保护按名字匹配。

状态只有这几种，各说各的，不要混：

| 状态 | 含义 | 谁来处理 |
| --- | --- | --- |
| `verified` | 签名有效，声明为通过 | 可以合并 |
| `failed` | 签名有效，声明为失败 | 修 job，重新签 |
| `unverified` | 没有可用回执、签名不对，或证据对不上 | 操作员 |
| `not applicable` | 这次改动本来就不需要回执 | 不用管 |

`unverified` 不是语气更缓和的 `failed`。它的意思是门禁判断不了，所以交给人，而不是自己猜。

## 动手之前

- 可复用 workflow 用完整 commit SHA 固定。tag 是会动的。
- `allowed_signers` 放在默认分支的 `.github/` 下。它是信任根，PR 改不动自己的信任根。
- `check-name` 定下来就别改。分支保护匹配的是字符串，改名等于悄悄换掉了受保护的东西。
