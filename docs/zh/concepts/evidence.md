# 证据

[English](../../en/concepts/evidence.md) | [中文](evidence.md)

证据就是操作员愿意为之负责的东西：日志、测量值、测试报告、模型哈希。回执里不装证据，只装证据目录的摘要；归档另外传。

## 摘要怎么算

`oob sign --evidence-dir` 遍历目录，对每个普通文件算哈希，每个文件一行清单：

```text
<文件 sha256>  <相对于证据目录的路径>
```

按路径排序后，对整个清单再算 SHA-256，就是摘要。文件权限、属主、时间戳都不参与。

空目录也合法，摘要就是空字节串的 SHA-256。

符号链接和特殊文件会被拒绝。路径必须是 UTF-8，不能含 `.`、`..` 分量，也不能含 LF、CR、NUL。跳过坏路径会让两棵不同的目录树算出同一个摘要，所以这里直接报错。

## 打包

```bash
oob pack --evidence-dir ./evidence --out evidence.tgz
```

`oob pack` 写出确定性的 `.tar.gz`：条目排序，元数据清零，然后打印文件数和摘要。解开后的目录摘要，和 `oob sign` 记录的一致。重新打包没问题，改文件不行。

## 交给验证方

三个来源，按顺序尝试：

1. `evidence-file`：runner 上的路径。
2. `evidence-url`：HTTPS 地址。
3. `claims.evidence_url`：签进回执里的地址。

第一种是给“归档已经在 runner 上”的情况（比如前一步刚下载）。后两种给签名机够不到 runner 的情况。

传输通道不需要可信。验证方解开归档，重新算摘要，和签名值比对。对不上就是 `E_EVIDENCE_MISMATCH`，结论只能是 `unverified`，不会变成通过。

URL 必须能从 GitHub 的 runner 访问。私有对象存储得给签名 URL。GitHub token 只发给 `api.github.com` 和 `github.com`；其他主机要么公开可读，要么自带签名。

## 默认必需

action 和可复用 workflow 默认要求证据。通过上面三个来源之一提供归档，或者设 `require-evidence: false`。

| 情况 | 结论 |
| --- | --- |
| 提供了归档，摘要一致 | `verified` 或 `failed`，看 `result` |
| 没提供归档 | `unverified`，`E_NO_EVIDENCE` |
| 提供了归档，摘要不一致 | `unverified`，`E_EVIDENCE_MISMATCH` |
| `require-evidence: false`，没有归档 | 按回执给结论，摘要写 `digest only` |

要求证据时，归档读不了、解不开，同样算 `unverified`。不会悄悄降级。

## run 里能看到什么

摘要一致的归档会作为 `oob-evidence` artifact 上传。job summary 里有一张清单表（文件、字节数、SHA-256 前几位），以及最多 20 个文本文件的折叠预览，单文件 32 KiB，总共 256 KiB。二进制文件只列不预览，其余留在 artifact 里。

artifact 和 run summary 受 Actions 保留期限制：默认 90 天，公开仓库只能调短。PR 评论里的回执才是长期记录。如果以后还要能核对证据本身，把它放到你能控制的地方，并把位置写进 `claims.evidence_url`。

## 放哪里

这些都可以，选环境里现成的：

- 同一个仓库的 `evidence/<sha>` 分支；
- release asset；
- 带签名 URL 的对象存储；
- 小文本归档可以用 gist 或其他公开粘贴；
- runner 能访问的内网共享。

能看 run 或能打开 URL 的人都能看到归档。把它当 CI 日志对待：不要放密钥、token、客户数据或私钥。

## 限制

| 限制 | 值 |
| --- | --- |
| 归档大小 | 50 MiB |
| 文件数 | 1000 |
| 清单条目 | 每个普通文件一行 |
| 单文件预览 | 32 KiB |
| 预览总量 | 256 KiB |
| 预览文件数 | 20 |

解包时先拒绝绝对路径、`..`、链接和特殊文件，再写盘。

## 错误码

| 代码 | 含义 |
| --- | --- |
| `E_NO_EVIDENCE` | 要求证据，但三个来源都没有归档 |
| `E_EVIDENCE_MISMATCH` | 归档算出的摘要和签名值不一致 |
| `E_EVIDENCE_ARCHIVE` | 归档不安全或读不了 |
| `E_EVIDENCE_PATH` | 文件名不是 UTF-8，或含 LF、CR、NUL |
| `E_EVIDENCE_TYPE` | 目录里有符号链接或特殊文件 |
| `E_KEY_IN_EVIDENCE` | 私钥落在要签名的目录里 |

完整列表见 [CLI](../reference/cli.md#错误码)。
