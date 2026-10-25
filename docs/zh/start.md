# 快速上手

[English](../en/start.md) | [中文](start.md)

这一页从一台空机器开始，到本地能验签为止。接入仓库是下一步，[action](reference/action.md) 和[可复用 workflow](reference/workflow.md) 两页分别讲两种接法。

## 需要什么

- Python 3.10 或更高版本。
- OpenSSH 8.0 或更高版本，`ssh-keygen -Y sign` 要用。
- 一个包含目标 commit 的 git clone。

包没有运行时依赖。

```bash
pip install out-of-band
oob --version
```

release 页面还有单文件版 `oob-<version>.pyz`，只需要 Python。机器连不上 PyPI 时通常用它，见[离线机器](guides/air-gapped.md)。

## 生成密钥

```bash
ssh-keygen -t ed25519 -N "" -C "ci operator" -f ~/.ssh/out-of-band
```

`ssh-keygen -Y sign` 直接读密钥文件，不走 `ssh-agent`。无人值守时用空口令比较省事；有人在场时也可以设口令。私钥留在签名机上，权限 `0600`。

把公钥放进使用方仓库的 `.github/allowed_signers`：

```text
operator ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... ci operator
```

第一列是你自己起的主名（principal）。它只是签名里的标签，不是 GitHub 登录名。

## 为一个 commit 签名

`--commit` 要完整 40 位 SHA，而且本地仓库里得有这个 commit。tree 从 commit 对象读，不读工作区。

```bash
cd /path/to/repo
mkdir -p ./evidence
./run-the-check.sh 2>&1 | tee ./evidence/run.log

oob sign \
  --job smoke \
  --commit "$(git rev-parse HEAD)" \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/out-of-band \
  --repo owner/name \
  --out receipt.md
```

输出就是一个块：一行 HTML 标记、一行 JSON、一段 SSH 签名。这个块就是回执。证据目录不会上传，回执里记的是它的摘要。

常用参数：

| 参数 | 作用 |
| --- | --- |
| `--repo owner/name` | 回执声明的仓库；默认取 `origin` |
| `--claims k=v` | 带一条可公开的小事实，可重复 |
| `--claims evidence_url=https://...` | 把证据包的位置签进回执 |
| `--output-file <file>` | 把最多 4 KiB 的检查输出带进回执 |
| `--allow-dirty` | 工作区有未提交改动时仍然签 |

默认拒绝脏工作区，因为回执绑定的是 commit，不是磁盘上的文件。

## 本地验一下

```bash
oob verify \
  --block receipt.md \
  --allowed-signers .github/allowed_signers \
  --repo owner/name \
  --commit "$(git rev-parse HEAD)" \
  --expect-job smoke
```

退出码就是结论：

| 退出码 | 含义 |
| --- | --- |
| `0` | 回执有效，`result: pass` |
| `1` | 回执有效，`result: fail` |
| `2` | 没有回执，或回执验不过 |
| `3` | 工具本身跑不了 |

加 `--json` 会输出一行机器可读的结果。以退出码为准。

## 让评论能看

原始块贴在 PR 里很难读。`oob render` 会转成 Markdown 表格，并把签名的原始字节放进折叠区：

```bash
oob render --block receipt.md --out comment.md
```

表格只是展示。验证方不读表格，只读块。

## 打包证据

```bash
oob pack --evidence-dir ./evidence --out evidence.tgz
```

`oob pack` 写出确定性的归档，并打印文件数和摘要。解开后的目录摘要，和 `oob sign` 写进回执的一致。验证方拿到归档后重新计算摘要，再决定是否留成 run 的 artifact。

## 接进仓库

两种载体选一个：

- [action](reference/action.md)：作为已有 job 里的一个 step；
- [可复用 workflow](reference/workflow.md)：单独成一个 job，自带超时、并发和权限。

两种都会按你指定的名字发布 check run。把这个名字配进分支保护。

## 接下来读什么

- [回执](concepts/receipt.md)：每个字段和绑定关系。
- [证据](concepts/evidence.md)：传输方式、限制和保留期。
- [状态](concepts/states.md)：为什么 `unverified` 不是 `failed`。
