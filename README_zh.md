<h1 align="center">out-of-band</h1>

<p align="center">给 GitHub 跑不了、或者已经在别处跑过的 CI 检查签一份回执。</p>

<p align="center">
  <a href="https://pypi.org/project/out-of-band/"><img src="https://img.shields.io/pypi/v/out-of-band?color=green" alt="PyPI"></a>
  <a href="https://github.com/Oaklight/out-of-band/releases/latest"><img src="https://img.shields.io/github/v/release/Oaklight/out-of-band?color=green" alt="Release"></a>
  <a href="https://github.com/Oaklight/out-of-band/actions/workflows/ci.yml"><img src="https://github.com/Oaklight/out-of-band/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="Apache-2.0"></a>
</p>

<p align="center">
  <a href="README_en.md">English</a> | <a href="README_zh.md">中文</a>
</p>

<p align="center">
  <a href="https://oaklight.github.io/out-of-band/?lang=zh"><strong>走一遍导览 →</strong></a>
</p>

## 两种需要回执的情况

**GitHub 跑不了这个任务。** 代码需要特定的加速卡、有许可证的工具链、只有办公网能连的数据库，或者一台几个人共用的实验机。托管 runner 到不了那里。

**任务已经在别处跑过。** 在 CI 里重跑太慢、不稳定，或者结果对不上。你希望门禁接受手上这次运行。

两种情况留下的是同一个缺口：一个必需的 check，没有任何 workflow 能诚实地产生它。out-of-band 让那台机器签一份声明，不需要 GitHub 凭据，也不需要被访问。

常见的替代方案是在机器上装自托管 runner。代价是共享硬件上多一个长期守护进程、一个能领取任务的凭据，以及仓库代码在那台机器上执行。传日志则把决定权交给浏览器标签页前的某个人。跳过 check，门禁就变成了建议。

## 怎么工作

```
签名机                                GitHub
─────────                             ──────
跑任务 ──► 证据 ──► 签名              PR 评论 / dispatch
                      │                    │
                      └── 签名块 ──────────┴──► verify.yml
                                                  │
                                                  ├── check run
                                                  ├── step summary
                                                  └── 固定评论
```

1. 操作员在任务必须跑的地方跑完，签一份声明：这个仓库、这个 commit、这个 tree、这个 job、这个结果、这份证据摘要。
2. 声明通过 PR 评论、dispatch 参数或文件传出去。
3. GitHub 上的 workflow 用默认分支的 `.github/allowed_signers` 验签，核对绑定，发布 check run。

这个仓库负责机制：格式、签名、验证、发布。使用方负责策略：哪些路径需要回执、job 叫什么、用哪把钥匙、这个 check 是否必需。

## 四种状态，不合并

| 回执 | 验证器状态 | check 结论 |
| --- | --- | --- |
| 有效，`result: pass` | `verified` | `success` |
| 有效，`result: fail` | `failed` | `failure` |
| 缺失或无效 | `unverified` | `failure` |
| 策略判定不需要 | `not applicable` | `success` |

`unverified` 的意思是门禁判断不了。结论发布成 `failure`，必需的 check 保持关闭，摘要里带错误码。缺回执从来不算 skip。

## 快速上手

需要 Python 3.10+ 和 OpenSSH 8.0+（`ssh-keygen -Y sign`）。没有运行时依赖。

```bash
pip install out-of-band
```

在跑任务的机器上生成密钥。私钥不离开这台机器。

```bash
ssh-keygen -t ed25519 -N "" -C "ci operator" -f ~/.ssh/out-of-band
```

把公钥提交到使用方仓库的 `.github/allowed_signers`：

```text
operator ssh-ed25519 AAAA...
```

为一个 commit 签名。`--commit` 必须是本地存在的完整 SHA；tree 从 commit 读，不读工作区。

```bash
oob sign \
  --job smoke \
  --commit "$(git rev-parse HEAD)" \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/out-of-band \
  --repo owner/name \
  --out receipt.md
```

输出是一整个块：一行 HTML 标记、一行 JSON、一段 SSH 签名。把它贴成 PR 评论，或传给 `workflow_dispatch` 参数。想让评论能读，先跑 `oob render --block receipt.md`。

发出去之前先本地验一遍：

```bash
oob verify --block receipt.md \
  --allowed-signers .github/allowed_signers \
  --repo owner/name --commit "$(git rev-parse HEAD)" --expect-job smoke
```

退出码：`0` 有效通过，`1` 有效失败，`2` 缺失或无效，`3` 工具错误。

## 接进仓库

两种载体，同一个验证器。[action](docs/zh/reference/action.md) 作为 step 跑；[可复用 workflow](docs/zh/reference/workflow.md) 作为独立 job 跑。

```yaml
  verified:
    needs: policy
    runs-on: ubuntu-latest
    permissions:
      contents: read
      checks: write
      pull-requests: write
    steps:
      - uses: Oaklight/out-of-band@<full-sha> # v0.5.0
        with:
          pr: ${{ needs.policy.outputs.pr }}
          commit: ${{ needs.policy.outputs.commit }}
          job: smoke
          required: ${{ needs.policy.outputs.requires }}
          check-name: smoke-verified
          trusted-authors: operator-login
```

这段配置只展示门禁的接线。证据默认必需，所以要加 `evidence-url` 或
`evidence-file`，或者设 `require-evidence: false`。

然后在分支保护里要求 `smoke-verified`。check 名是对外接口：改名等于悄悄换掉了受保护的东西。

`uses:` 用完整 commit SHA 固定。tag 会动。

## 证据

证据默认必需。三个来源选一个：

| 来源 | 什么时候用 |
| --- | --- |
| `evidence-file` | 归档已经在 runner 上 |
| `evidence-url` | 归档在某个 HTTPS 地址 |
| `claims.evidence_url` | 希望回执自带证据位置 |

```bash
oob pack --evidence-dir ./evidence --out evidence.tgz
```

验证方解开归档，重新算摘要，和签名里的值比对。对不上是 `E_EVIDENCE_MISMATCH`，结论为 `unverified`。对上了就上传成 `oob-evidence` artifact，job summary 里显示清单和有限长度的文本预览。

设 `require-evidence: false` 可以只接受签名摘要，不要归档。

GitHub token 只发给 `api.github.com` 和 `github.com`。其他主机必须公开可读，或者提供签名 URL。

## 回执证明什么

证明某把被列出的钥匙的持有者，签了这些字节，绑定了一个仓库、commit、tree、job 和证据摘要。

它不证明任务跑对了、证据和摘要一致，也不证明签名机没被入侵。它是背书，不是正确性证明。见[信任](docs/zh/concepts/trust.md)和 [SPEC.md](SPEC.md) 第 8 节。

## 文档

从[文档索引](docs/zh/README.md)开始。常见入口：

| 你想做的事 | 读这篇 |
| --- | --- |
| 装上并签出第一份回执 | [快速上手](docs/zh/start.md) |
| 理解回执、信任、证据、状态 | [概念](docs/zh/README.md#按你手上的事来选) |
| 查命令、参数或输入 | [CLI](docs/zh/reference/cli.md)、[action](docs/zh/reference/action.md)、[workflow](docs/zh/reference/workflow.md) |
| 照着搭一套完整门禁 | [补丁门禁](docs/zh/guides/patch-gate.md)、[硬件运行](docs/zh/guides/hardware-run.md) |
| 在离线机器上使用 | [离线机器](docs/zh/guides/air-gapped.md) |
| 和其他工具比较 | [先例与替代方案](docs/zh/prior-art.md) |

英文文档在 [`docs/en/`](docs/en/README.md)，结构与中文一致。

## 安装

```bash
pip install out-of-band
```

每个 release 还带 `oob-<version>.pyz`，单文件，只需要 Python。机器连不上 PyPI 时通常用它。

Python 3.10 到 3.14 都在测试范围内。Windows 上用 `python oob-<version>.pyz`。

## 项目

- [安全策略](SECURITY.md)
- [参与贡献](CONTRIBUTING.md)
- [更新记录](CHANGELOG.md)
- [示例](examples/README.md)
- [规范](SPEC.md)
- 许可证：Apache-2.0

## 不做什么

不做 runner，不做托管服务，不做 GitHub App，不接 Sigstore，不做透明日志，也不存 artifact。工具只负责签和验；其余归使用它的仓库。
