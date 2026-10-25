# FAQ

[English](../en/faq.md) | [中文](faq.md)

## 为什么不在那台机器上跑自托管 runner？

能跑就用。它需要持续的出网连接、主机上的 GitHub 凭据，还会执行仓库里的 workflow 代码，公开仓库的攻击面很大。临时租的机器和调度器管理的登录节点，通常一样都不满足。

## 为什么不放个 token 在机器上，直接发 status？

这样你本来想保持干净的机器上就多了一个长期凭据。个人访问令牌只能创建 commit status，不能创建 check run；status 只是一个标签，不绑定证据、tree 或 job。回执不需要凭据，签名覆盖的就是声明本身。

## 为什么不直接在 CI 里跑？

托管 runner 能跑就在 CI 里跑。out-of-band 是搬不动的任务的后备方案。

## 为什么不人工评论批准？

“LGTM”没有 commit、没有 job、没有证据，而且可以改、可以删。回执由机器校验，绑定一个 commit 和一份证据摘要，之后仍然可验。

## 为什么不把日志传上去，贴个链接？

谁都能传任何东西，链接也不能证明它和 commit 的关系。在这里，证据是要核对的：提供归档时，先按签名摘要重新计算，再决定是否保留。

## 为什么不用 Sigstore 或 GitHub 的 artifact attestations？

任务在 Actions 里跑时，用它们。签名的是 workflow 的 OIDC 身份。Actions 之外的机器没有这个身份，无密钥签名又需要 Fulcio 和 Rekor。Sigstore 可以用密钥离线签一个 blob，但 GitHub 侧的门禁还是得自己搭：谁能签、签哪个 commit、覆盖什么证据。out-of-band 就是这个门禁。

## 为什么不用 in-toto 或 SLSA？

它们描述构建 provenance 和供应链步骤，in-toto 在精神上最接近。两者表达力更强，也都需要 layout 和验证器。回执是操作员的背书，不是构建者身份声明，项目也不声称 SLSA 等级。见[先例与替代方案](prior-art.md)。

## 回执能证明任务真的跑了吗？

不能。它证明某把被列出的钥匙的持有者，签了一份声明，声明里有仓库、commit、tree、job、结果和证据摘要。任务有没有跑、证据是否属实，都在签名之外。见[信任](concepts/trust.md)。

## 签名机被入侵了怎么办？

被偷走的钥匙可以签任何声明。记录 tree 能限制改写后的 commit 复用回执，证据哈希能限制调包，但都发现不了被入侵的主机。怀疑泄露就轮换钥匙。

## 回执会过期吗？

不会。它绑定 commit，不绑定时刻。`issued_at` 只记录，不强制。策略要求“最近跑过”，就在门禁外面实现。

## force-push 之后呢？

commit 仍然能按 SHA 访问，check 也跟着它。分支不再包含这个 commit 时，分支上看不到它。给新 commit 重新签；回执不会转移。

## 一个 commit 能让多个 job 或多台机器背书吗？

可以。每份回执有自己的 `job`，收集时按 commit 和 job 过滤，几份回执可以共存。见[多 job](guides/multi-job.md)。

## 证据放在哪？

默认在操作员那边。run 上会留一份 `oob-evidence` artifact，受仓库的 Actions 保留期限制。长期记录是回执评论。见[证据](concepts/evidence.md)。

## 有服务器、账号或透明日志吗？

没有。工具没有服务端组件。钥匙在仓库里，签名在本地或 workflow 里验证，不在任何地方注册。

## GitHub 之外能用吗？

回执格式和 CLI 与 forge 无关。验证器的两种载体是 GitHub 专用的。别的 forge 完全可以用 `oob verify` 检查同一个块。

## 为什么用 SSH 钥匙？

目标机器上本来就装了 OpenSSH，`ssh-keygen -Y sign` 是现成命令，`allowed_signers` 是仓库可以审的纯文本信任根。不用引入新的密钥格式、守护进程或 PKI。

## 支持 Windows 吗？

CLI 是纯 Python，能在 Windows 上跑。验证器载体用 `ubuntu-latest`。zipapp 没有 shebang，用 `python oob-<version>.pyz` 运行。见[离线机器](guides/air-gapped.md)。

## 可以不要证据吗？

可以，设 `require-evidence: false`。回执仍然绑定证据摘要，但不取归档、不上传。摘要会写 `digest only`。

## 能测试门禁但不发布 check 吗？

设 `report: false`。会算出结论并写进 step summary 和 output，但不创建 check run，也不发评论。本仓库的自测就是这么跑负向用例的。
