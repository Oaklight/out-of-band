# 回执

[English](../../en/concepts/receipt.md) | [中文](receipt.md)

回执是一把钥匙对一个 commit 的声明。它通过 PR 评论、dispatch 参数或文件传递。项目里其他东西，都是为生成、检查或展示它服务的。

## 块的结构

````text
<!-- receipt:v1 -->
```json
{"schema":"receipt/v2","repo":"acme/widget","commit":"6e5b8a4...","tree":"0d3c1f...","job":"smoke","result":"pass","issued_at":"2026-10-24T19:30:00Z","tool":"oob/0.5.0","evidence":{"count":2,"digest":"sha256:0ac06086..."},"output":"2 passed in 41s","claims":{"device":"v100"}}
```
```ssh-signature
-----BEGIN SSH SIGNATURE-----
...
-----END SSH SIGNATURE-----
```
````

三部分：

- 标记 `<!-- receipt:v1 -->`，workflow 靠它在评论里找到回执；
- 恰好一行 JSON；
- 对这一行原始字节的 SSH 签名。

签名覆盖写出来的那一行：不重新序列化，不规整空白，不转换换行。改一个字节就验不过。块外面的文字不参与验证。

## JSON 绑定了什么

| 字段 | 含义 |
| --- | --- |
| `repo` | 仓库，`owner/name` |
| `commit` | 被测试的完整 commit SHA |
| `tree` | 该 commit 的 tree，改写过的 commit 不能复用回执 |
| `job` | job 名，和使用方约定好 |
| `result` | `pass` 或 `fail` |
| `evidence.digest` | 对证据清单计算的 `sha256:` |
| `evidence.count` | 清单里的文件数 |
| `issued_at` | 签名者声明的签名时间，UTC |
| `tool` | 生成回执的版本；仅供参考，从不参与判断 |
| `output` | 可选，最多 4 KiB 的检查输出（schema v2） |
| `claims` | 可选的可公开事实，序列化后不超过 2048 字节 |

`repo`、`commit`、`tree`、`job` 都是和调用方上下文里的值比对，不和回执里的其他字段互相印证。签名验证通过之前，这些值都由提交者控制。

## schema 版本

- `receipt/v1` 没有 `output`。
- `receipt/v2` 只多了 `output`，别的没变。
- 只有给了 `--output-file`，`oob sign` 才生成 v2。
- v2 的验证器两种都读；v1 的验证器只读 v1。

兼容边界是 schema 字符串，不是包版本号。

## claims

claims 放一些使用方想展示或以后会用的小事实：设备名、批次号、模型哈希、证据包链接。

- key 匹配 `[a-z][a-z0-9_.-]{0,63}`。
- value 可以是字符串、安全范围内的整数、布尔值，或最多 16 个这类标量组成的数组。
- 不能嵌套对象，不能有浮点数，不能有 null。
- 序列化后不超过 2048 字节。

claims 是数据。它们会出现在 check 摘要里的代码块中，Markdown 和 @ 提及语法会被转义，所以一条 claim 变不成链接，也 ping 不到人。

`claims.evidence_url` 有特殊含义：验证方没有 `evidence-url` 或 `evidence-file` 时，会去取这个地址。这样一份评论就能自带证据位置。地址必须是 `https`。

## 限制

| 限制 | 值 |
| --- | --- |
| 整个块 | 16 KiB |
| JSON | 一行，不能换行 |
| `output` | 4096 字节 |
| `claims` | 序列化后 2048 字节 |
| 证据文件数 | 1000 |
| 证据总大小 | 50 MiB |

验证方先看大小再解析，所以一条恶意评论做不了太多事。

## 回执不说明什么

它不说明 job 真的跑了、结果正确，也不说明签名机没被入侵。它只说明：某把被列出的钥匙，签了这些字节。完整的边界见[信任](trust.md)。

规范里的语法、提取规则和字段范围在 [SPEC.md](../../../SPEC.md)。
