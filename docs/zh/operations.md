# 运维

[English](../en/operations.md) | [中文](operations.md)

密钥、发布，以及结论不符合预期时怎么查。信任模型见[信任](concepts/trust.md)，这一页是操作手册。

## 生成密钥

```bash
ssh-keygen -t ed25519 -f ~/.ssh/out-of-band -C "out-of-band operator"
chmod 600 ~/.ssh/out-of-band
```

`ssh-keygen -Y sign` 直接读密钥文件，不走 `ssh-agent`。设了口令就要交互输入，有人在场时没问题，无人值守时做不到。

公钥放进默认分支的 `.github/allowed_signers`：

```text
operator ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... out-of-band operator
```

主名是自己起的标签，和 GitHub 登录名无关。

## 改信任根

验证方从默认分支读 `allowed_signers`，而且是有意 checkout 默认分支。PR 加不了能给自己背书的钥匙。改这个文件就是改策略，按改策略的方式审。

删掉一把钥匙，不只挡住以后签的回执。它签过的回执也会验不过，包括已经发出去的。旧回执还有用，就保留旧钥匙，在旁边加新的。

## 轮换密钥

1. 新公钥加进 `allowed_signers`，合并。
2. 签名机换成新私钥。
3. 旧钥匙签的最后一份回执不再需要之后，另开一个 PR 删掉旧钥匙。

可以同时列两把钥匙，验证器不区分。

## 增加操作员

把对方的公钥加进 `allowed_signers`。如果调用方设了 `trusted-authors`，再把对方的 GitHub 登录名加进去。这是两道关：谁能发评论，谁的签名算数。

## 发布与固定版本

使用方用完整 commit SHA 固定 action 或 workflow：

```yaml
uses: Oaklight/out-of-band@<full-sha> # v0.5.0
```

固定的是跑哪份验证器代码，不是信任哪些钥匙。后者由调用方的 `allowed_signers` 决定。

新版本改了 schema 或 CLI，就在一个审过的 PR 里更新固定值。v2 验证器仍然读 v1 回执，所以使用方不用给旧 commit 重新签名。

## 排查

先看 run，不要先看 check。step summary 里有状态、错误码、来源和 commit。check 的输出会重复 claims。

| 状态 | 错误码 | 含义 |
| --- | --- | --- |
| `unverified` | `E_NO_BLOCK` | 没有可信评论带标记 |
| `unverified` | `E_WRONG_COMMIT` | 有回执，但没有一份对应这个 commit |
| `unverified` | `E_WRONG_JOB` | 有对应 commit 的回执，但 job 名不对 |
| `unverified` | `E_BAD_SIGNATURE` | 钥匙不在列表里，或签名后字节被改过 |
| `unverified` | `E_WRONG_TREE` | commit 的 tree 和签名的 tree 不一致 |
| `unverified` | `E_MULTI_BLOCK` | 同一个 commit 和 job 有两份不同的回执 |
| `unverified` | `E_EVIDENCE_MISMATCH` | 归档算出的摘要和签名值不一致 |
| `unverified` | `E_NO_EVIDENCE` | 要求证据，但没提供归档 |
| `failed` | `OK` | 回执有效，内容为 `result: fail` |
| `not applicable` | `OK` | 调用方设了 `required: false` |

`failed` 不是错误。它是一份有效的回执，报告 job 失败；check 红是因为声明本身是负面的。

本地复现：

```bash
oob verify \
  --block receipt.md \
  --allowed-signers .github/allowed_signers \
  --repo owner/repo \
  --commit <sha> \
  --expect-job <job>
```

退出码就是结论：0 通过，1 有效失败，2 缺失或无效，3 工具错误。workflow 把 0 映射成 `success`，1 和 2 都映射成 `failure`，具体是哪一种看 summary。完整错误码表见 [CLI](reference/cli.md#错误码)。

## 时间

门禁从不等人。验证 job 由事件触发，几秒结束；回执可能在对应的运行结束几小时甚至几天后才到。回执没有 TTL，绑定的是 commit，所以给同一个 commit 再签一份，是又多一份有效回执，不是替换旧的。

只有本地超时：可复用 workflow 的 job 5 分钟，下载证据 120 秒。action 继承调用方 job 的超时。

## 证据出问题

- URL 必须能从 runner 访问，不能需要浏览器会话。私有对象存储要给签名 URL。
- 归档必须是 `oob pack` 生成的 `.tar.gz`，或者形状一致：没有绝对路径、`..`、链接和特殊文件。
- 摘要覆盖路径和文件内容，不覆盖归档字节，所以重新打包没问题，改文件不行。
- 超过 50 MiB 的归档在解包前就被拒绝。
- 证据检查失败会把本来通过的回执变成 `E_EVIDENCE_MISMATCH` 和 `failure`，不会降级成“只有摘要”。

三个来源和保留期规则见[证据](concepts/evidence.md)。
