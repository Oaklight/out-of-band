# 信任

[English](../../en/concepts/trust.md) | [中文](trust.md)

信任根是一个文本文件：默认分支上的 `.github/allowed_signers`。其余规则都从这里来。

## 谁可以签

`allowed_signers` 用 OpenSSH 格式：

```text
operator ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... ci operator
```

- 第一列是主名（principal），只是签名里的标签，不是 GitHub 登录名。
- 一个主名可以列多把钥匙，也可以有多个主名。
- 验证方逐个尝试，只要有一个主名验过就算有效。
- 不接受通配主名（`*`、`?`、`!`）。列不全的信任根不算信任根。

谁能**发**回执是另一个问题。workflow 只读 `trusted-authors` 里的作者，未设置时只读 owner、member 和 collaborator 的评论。不可信的评论直接忽略，陌生人贴个标记也卡不住门禁。

## 为什么从默认分支读文件

如果 PR 能自己加一把钥匙，它就能给自己的回执背书。可复用 workflow 明确 checkout 默认分支；action 通过 contents API 读默认分支上的文件。两者都不会从 PR 里读 `allowed_signers`。

这也是调用方要用 `pull_request_target` 或 `issue_comment`、而不是 `pull_request` 的原因：门禁必须用默认分支的代码和可写 token 运行。代价是，这个 workflow 里绝不能 checkout 或执行 PR 代码。

## 私钥

- 留在签名机上，权限 `0600`。
- 不进仓库、不进回执、不进 artifact、不进日志。
- `ssh-keygen -Y sign` 直接读文件，不经过 `ssh-agent`。
- 有人在场时可以用口令；无人值守时，用一把只有操作员能登录的机器上的无口令密钥。

如果密钥路径落在证据目录里，签名器会直接拒绝，避免密钥的名字和哈希进入摘要。

## 轮换与移除

1. 把新公钥加进 `allowed_signers`，合并。
2. 签名机换成新私钥。
3. 旧钥匙签的回执都不再需要之后，再把它删掉。

删掉一把钥匙，不只挡住以后签的回执。它签过的回执也会验不过，包括已经发出去的。如果旧回执还有用，就保留旧钥匙，在旁边加新的。

## 回执证明什么

证明某把被列出的私钥的持有者，签了这些字节，绑定了一个仓库、commit、tree、job 和证据摘要。

它不证明：

- job 跑过，或跑对了；
- 证据和摘要一致（签名者只是声明了一个摘要，和上传的归档比对是另一步）；
- 签名机没有被入侵；
- 这个 commit 就是最终合并的内容（记 tree 就是为了让改写过的 commit 对不上）；
- `issued_at` 准确。这个时间是自己填的。

回执是钥匙持有者的背书，不是正确性证明。

## 不会过期

回执绑定 commit，不绑定时刻。几周前为同一个 commit 签的回执，和一分钟前签的，验证结果一样。`issued_at` 只记录，不强制。如果策略要求“最近跑过”，在机制外面实现，比如环境变化时要求重新签。

## 验证方不会做的事

- 不执行回执里的任何内容。
- 不把 claim 当命令、模板或链接。
- 除了 `allowed_signers`，不读仓库里的其他文件。
- 除了 `api.github.com` 和 `github.com`，不把 GitHub token 发给任何主机。

规范条文见 [SPEC.md](../../../SPEC.md) 第 3、7、8 节。
