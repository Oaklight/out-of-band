# CLI

[English](../../en/reference/cli.md) | [中文](cli.md)

```text
oob sign   --job <name> --commit <sha> --result pass|fail
                --evidence-dir <dir> --key <path>
                [--repo <owner/name>] [--claims k=v ...]
                [--output-file <file>] [--allow-dirty] [--out <file>]

oob pack   --evidence-dir <dir> --out <file> [--json]

oob verify --block <file> --allowed-signers <file>
                --repo <owner/name> --commit <sha> --expect-job <name>
                [--expect-tree <sha>] [--json]

oob render --block <file|-> [--out <file>]
```

命令成功都返回 `0`。`verify` 用 `1` 和 `2` 表示结论，其余情况用 `3` 表示工具错误。

## `oob sign`

为一个 commit 生成回执块。

| 参数 | 必需 | 含义 |
| --- | --- | --- |
| `--job` | 是 | 使用方期望的 job 名 |
| `--commit` | 是 | 本地存在的完整 40 位 commit |
| `--result` | 是 | `pass` 或 `fail` |
| `--evidence-dir` | 是 | 要计算证据摘要的目录 |
| `--key` | 是 | 私钥路径 |
| `--repo` | 否 | `owner/name`；默认取 `origin` |
| `--claims` | 否 | `k=v`，可重复 |
| `--output-file` | 否 | 最多 4096 字节的检查输出；生成 schema v2 |
| `--allow-dirty` | 否 | 工作区有改动时仍然签 |
| `--out` | 否 | 写到文件，而不是 stdout |

几个要点：

- `--commit` 必须是完整 SHA，不能写分支名或缩写。tree 从 commit 对象读，不从工作区读。
- 密钥不能在证据目录里面。
- `--claims` 的值如果是合法的标量或允许形状的数组，会按 JSON 解析；否则按字符串处理。浮点数、null、超出安全整数范围的值会被拒绝。
- 输出只有块本身，状态信息走 stderr。
- 不访问网络，不使用 GitHub 凭据。

## `oob pack`

把证据目录打成确定性的 `.tar.gz`。

| 参数 | 含义 |
| --- | --- |
| `--evidence-dir` | 要打包的目录 |
| `--out` | 归档路径 |
| `--json` | 输出 `{"count":N,"digest":"sha256:..."}` |

摘要和 `oob sign` 记录的是同一个。签完之后再打包没问题，只要内容没变。

## `oob verify`

用信任根和期望上下文检查一个块。

| 参数 | 必需 | 含义 |
| --- | --- | --- |
| `--block` | 是 | 含标记和两段 fence 的文件 |
| `--allowed-signers` | 是 | OpenSSH allowed-signers 文件 |
| `--repo` | 是 | 期望的 `owner/name`，大小写不敏感 |
| `--commit` | 是 | 期望的 commit，大小写不敏感 |
| `--expect-job` | 是 | 期望的 job，精确匹配 |
| `--expect-tree` | 否 | 期望的 tree，大小写不敏感 |
| `--json` | 否 | 输出一行机器可读结果 |

默认输出一段人看的摘要。加 `--json` 时输出一行：

```json
{"verdict":"pass|fail|unverified|error","code":"OK|E_...","repo":null,"commit":null,"job":null}
```

除非回执解析成功且签名验过，否则 `repo`、`commit`、`job` 都是 `null`。在那之前，这些值由提交者控制。

以退出码为准：

| 退出码 | 含义 |
| --- | --- |
| 0 | 回执有效，`result: pass` |
| 1 | 回执有效，`result: fail` |
| 2 | 没有回执，或回执验不过 |
| 3 | 用法或内部错误 |

## `oob render`

把块转成 Markdown 评论：签名字段的表格、可选的 output，以及折叠在 `<details>` 里的原始块。

| 参数 | 含义 |
| --- | --- |
| `--block` | 输入文件，`-` 表示 stdin |
| `--out` | 写到文件，而不是 stdout |

表格只是展示。验证只读块，所以渲染不会改变签名字节。

## 退出码

| 退出码 | 含义 |
| --- | --- |
| 0 | 成功；`verify` 表示有效的 `pass` |
| 1 | 仅 `verify`：回执有效且为 `fail` |
| 2 | 仅 `verify`：回执缺失或无效 |
| 3 | 用法、I/O 或内部错误；没有产生回执 |

回执缺失是退出 2，不是 0。CI 验证器把退出 2 映射成 `unverified`，结论为 `failure`。

## 错误码

以 `error: <CODE>: <message>` 打到 stderr。

| 代码 | 含义 | 退出码 |
| --- | --- | --- |
| `OK` | 验证成功（`pass` 或有效的 `fail`） | 0 或 1 |
| `E_NO_BLOCK` | 没找到回执标记 | 2 |
| `E_MULTI_BLOCK` | 标记不止一个，或可信评论之间互相矛盾 | 2 |
| `E_TOO_LARGE` | 块超过 16 KiB | 2 |
| `E_BAD_FENCE` | fence 缺失或顺序不对 | 2 |
| `E_MULTI_LINE` | JSON 不是一行 | 2 |
| `E_BAD_JSON` | 不是合法 UTF-8，或不是 JSON | 2 |
| `E_DUP_KEY` | JSON 对象有重复 key | 2 |
| `E_UNKNOWN_FIELD` | 当前 schema 没有这个字段 | 2 |
| `E_BAD_SCHEMA` | `schema` 不是受支持的版本 | 2 |
| `E_BAD_TYPE` | JSON 类型不对，或出现浮点数、null | 2 |
| `E_BAD_VALUE` | 值不符合格式或范围 | 2 |
| `E_CLAIMS_LIMIT` | claims 超过数量、大小或形状限制 | 2 |
| `E_OUTPUT_LIMIT` | `output` 超过 4096 字节 | 2 或 3 |
| `E_EVIDENCE_ARCHIVE` | 证据归档不安全或读不了 | 2 |
| `E_EVIDENCE_MISMATCH` | 上传的证据和签名摘要不一致 | 2 |
| `E_NO_EVIDENCE` | 要求证据，但没有提供归档 | 2 |
| `E_BAD_SIGNATURE` | 签名 armor 格式不对 | 2 |
| `E_NO_PRINCIPAL` | `allowed_signers` 里没有主名能验过这个签名 | 2 |
| `E_WRONG_REPO` | `repo` 和期望仓库不一致 | 2 |
| `E_WRONG_COMMIT` | `commit` 和期望 head 不一致 | 2 |
| `E_WRONG_TREE` | `tree` 和期望 tree 不一致 | 2 |
| `E_WRONG_JOB` | `job` 和期望 job 不一致 | 2 |
| `E_BAD_ALLOWED_SIGNERS` | 文件缺失、没有钥匙，或出现通配主名 | 3 |
| `E_TOO_MANY_COMMENTS` | 要扫描的评论超过 5000 条 | 3 |
| `E_KEY_IN_EVIDENCE` | 签名密钥在证据目录里 | 3 |
| `E_NOT_A_REPO` | `sign` 不在 git 仓库里运行 | 3 |
| `E_NO_REMOTE` | 没有 `origin`，也没给 `--repo` | 3 |
| `E_UNKNOWN_COMMIT` | 本地没有这个 commit | 3 |
| `E_SIGN_FAILED` | `ssh-keygen` 生成不了签名 | 3 |
| `E_DIRTY_WORKTREE` | 工作区有改动，且没给 `--allow-dirty` | 3 |
| `E_EVIDENCE_PATH` | 文件名不是 UTF-8，或含 LF、CR、NUL | 3 |
| `E_EVIDENCE_TYPE` | 证据里有符号链接或非普通文件 | 3 |
| `E_EVIDENCE_READ` | 证据目录缺失或读不了 | 3 |
| `E_USAGE` | 命令行参数不对 | 3 |
| `E_INTERNAL` | 意外失败 | 3 |

退出 2 的错误码表示“找到了回执但拒绝了”，`E_NO_BLOCK` 例外，它表示没找到。

## CLI 里没有的东西

没有 `publish` 命令。创建 check run 需要 GitHub App 身份。在 Actions 里，`GITHUB_TOKEN` 就是 Actions App，所以发布放在 workflow 或 action 里。个人访问令牌只能创建 commit status，不能创建 check run，而 status 不是这个门禁。

## 调试

`OOB_DEBUG=1` 会让意外失败打印 traceback。不设时，CLI 打印 `error: E_INTERNAL: ...` 并退出 3。
