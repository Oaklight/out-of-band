# 运维

[English](../en/operations.md) | [中文](operations.md)

密钥、信任，以及结论不符合预期时怎么办。

## 生成密钥

```bash
ssh-keygen -t ed25519 -f ~/.ssh/out-of-band -C "out-of-band operator"
chmod 600 ~/.ssh/out-of-band
```

`ssh-keygen -Y sign` 直接读密钥文件，不走 `ssh-agent`。设了口令就要交互输入：人坐在机器前没问题，无人值守的 job 里做不到。要么用不带口令的密钥、保证 `0600` 且机器只有操作员能登录，要么在有人值守时签名。

公钥写进默认分支的 `.github/allowed_signers`：

```
operator ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... out-of-band operator
```

密钥前面那个 principal 是自己起的标签，和 GitHub 账号没有关系。

## 信任根

验证 workflow 从默认分支读 `allowed_signers`，并且是故意检出默认分支的。PR 没法塞一把能给自己验签的钥匙。改这个文件就是改策略，按策略变更来审。

删掉一把公钥，不只是挡住以后回执：它签过的回执也会失效，包括已经发出去的。如果旧的回执还有意义，就保留旧钥，在旁边加新钥。

## 轮换

1. 新公钥加进 `allowed_signers`，合并。
2. 操作员机器换用新私钥。
3. 旧钥签的最后一份回执不再需要之后，另开一个 PR 把旧钥删掉。

两把公钥可以同时存在，验证方不区分。

## 增加操作员

把对方的公钥加进 `allowed_signers`。如果 workflow 设了 `trusted-authors`，还要加上对方的 GitHub 登录名。这是两道不同的关：谁有资格发评论，和谁的签名算数。

## 发布与固定版本

调用方用 `uses: Oaklight/out-of-band/.github/workflows/verify.yml@<sha>` 固定 workflow。workflow 自己从调用方仓库读 `allowed_signers`，所以这个 pin 决定跑哪份验证代码，不决定信任哪些钥匙。

新版本改了 schema 或 CLI 时，照常发布，用经过评审的 PR 更新 pin，并让旧版本至少再活一个 release。v2 验证器仍然能读 v1 回执。

## 排查

先看 run，不要只盯着 check。step summary 里有状态、错误码、来源和 commit，check 的 output 里还会重复一遍声明。

| 结论 | 错误码 | 含义 |
| --- | --- | --- |
| unverified | `E_NO_BLOCK` | 有权限的评论里没有回执 |
| unverified | `E_WRONG_COMMIT` | 有回执，但没有一份是这个 commit 的 |
| unverified | `E_WRONG_JOB` | 这个 commit 的回执写的是别的 job |
| unverified | `E_BAD_SIGNATURE` | 公钥不在名单里，或签名后字节被改过 |
| unverified | `E_WRONG_TREE` | commit 的 tree 和签名的 tree 对不上 |
| unverified | `E_MULTI_BLOCK` | 同一个 commit、同一个 job 有两份不同的回执 |
| unverified | `E_EVIDENCE_MISMATCH` | 包算出来的 digest 和签名的不一致 |
| unverified | `E_TOO_MANY_COMMENTS` | 评论超过 5000 条；退出码 3 |
| failed | — | 回执有效，且声明 `result: fail` |
| not applicable | `OK` | 调用方设了 `required: false` |

`failed` 不是错误。那是一份有效回执，报告 job 失败了；check 红是因为结论本身就是负面的。

本地复现：

```bash
oob verify \
  --block receipt.md \
  --allowed-signers .github/allowed_signers \
  --repo owner/repo \
  --commit <sha> \
  --expect-job <job>
```

退出码：0 通过，1 有效但失败，2 缺失或无效，3 用法或内部错误。workflow 把它们映射成 `success`、`failure`、`action_required`。

## 时间

没有任何环节在等操作员。验证 job 由事件触发，几秒就结束；回执可以在任务结束几小时甚至几天之后才出现。回执没有有效期，绑定的是 commit，所以对同一个 commit 再签一次，是又一份有效回执，不是替换旧的那份。

超时只有本地的两处：验证 job 5 分钟，下载证据 120 秒。

## 证据相关的问题

- 地址要 runner 能访问，且不需要浏览器会话。私有对象存储给签名 URL。
- 包必须是 `oob pack` 生成的 `.tar.gz`，或布局一致：没有绝对路径、没有 `..`、没有链接、没有特殊文件。
- digest 覆盖路径和文件内容，不是压缩包字节。重新打包没关系，改文件就有关系。
- 超过 50 MiB 在解压前就会被拒。
- 证据检查失败会把原本通过的回执变成 `E_EVIDENCE_MISMATCH` 和 `action_required`，不会退化成"只看 digest"。
