# 状态

[English](../../en/concepts/states.md) | [中文](states.md)

门禁只报四种状态，不会合并成两种。

| 状态 | 含义 | check | 谁来处理 |
| --- | --- | --- | --- |
| `verified` | 签名有效，`result: pass` | `success` | 可以合并 |
| `failed` | 签名有效，`result: fail` | `failure` | 修 job，重新签 |
| `unverified` | 没有可用回执、签名不对，或证据对不上 | `failure` | 人来看 |
| `not applicable` | 这次改动本来就不需要回执 | `success` | 不用管 |

`unverified` 不是语气更缓和的 `failed`。它的意思是门禁判断不了。必需的 check 保持红色，摘要里带错误码，原因看得见。

## 为什么 `unverified` 算失败

能挡住合并的结论只有两种：`failure`，或者 check 一直缺失。把 `unverified` 写成 `success`，就等于让“我判断不了”把代码合进去。写成 `failure` 既关着门，又能在标题和摘要里区分原因。

另一种做法是让 check 一直 pending。UI 上好看一些，实际更糟：pending 可以无限等下去，有些策略还会把陈旧的 pending 当成可以合并的理由。门禁先判断，再报告。

## 状态和退出码

| 回执 | `oob verify` 退出码 | 验证器状态 | check 结论 |
| --- | --- | --- | --- |
| 有效，`result: pass` | 0 | `verified` | `success` |
| 有效，`result: fail` | 1 | `failed` | `failure` |
| 缺失或无效 | 2 | `unverified` | `failure` |
| 工具跑不了 | 3 | 不发布 check | job 失败 |

退出码 3 不是结论。它表示验证器自己没法工作：文件缺失、参数写错、代码有 bug。这时不创建 check，必需的 check 保持缺失，合并继续被挡住。这就是 fail-closed。

## `not applicable`

使用方设 `required: false` 时，回执根本不参与判断。状态是 `not applicable`，结论是 `success`，摘要里说明没有评估回执。路径过滤和可选平台都靠它：只改文档的 PR 不该被硬件回执卡住。

一份陈旧的失败回执，也不能挡住策略已经判定为“不需要”的 PR。所以是跳过，不是读完再忽略失败。

## 只算结论，不发布

`report: false` 会算出结论，写 step summary 和 output，但不创建 check run，也不发固定评论。仓库自测的负向用例用它：结论照样断言，PR 的 check 列表保持绿色。

这是测试和试运行用的开关，不是策略选项。真正要门禁的使用方必须让 `report` 保持 `true`。

## 错误码

`unverified` 一定带一个错误码，比如 `E_NO_BLOCK`、`E_WRONG_COMMIT`、`E_BAD_SIGNATURE` 或 `E_EVIDENCE_MISMATCH`。错误码指向第一个失败的检查。完整列表见 [CLI](../reference/cli.md#错误码)。
