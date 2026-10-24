# 操作员机器验证

[English](../en/validation.md) | [中文](validation.md)

目标：证明跑检查、签回执的那台机器，不需要入站通路，也不需要持有 GitHub 凭据。

记录于 2026-10-23。机器是 Debian 12，OpenSSH 9.2p1，Python 3.11，单 vCPU，内存不足 3 GiB。下称**操作员机器**；本文不出现主机名、地址、用户名或设备标识。

## 验证了什么

| 检查项 | 结果 |
|---|---|
| 在空的网络命名空间里执行 `oob sign`（`unshare -n`） | 退出码 0，得到有效块 |
| 对字面 payload 离线执行 `ssh-keygen -Y verify` | 退出码 0 |
| 机器上的 GitHub 凭据 | 没有：无 `gh` 配置，环境中没有 `GH_TOKEN` / `GITHUB_TOKEN` |
| 流程需要的入站监听 | 没有；每一步都是本地读取，或一次出站 HTTPS 请求 |

## 过程

在操作员机器上以 root 身份，在一个临时目录里执行。

```bash
WORK=$(mktemp -d)
mkdir -p "$WORK/repo" "$WORK/evidence/nested" "$WORK/keys"
cd "$WORK/repo"
git init -q -b main
git config user.email op@example.invalid
git config user.name operator
printf 'build ok\n' > build.log
git add build.log
git commit -qm candidate
git remote add origin git@github.com:acme/widget.git
COMMIT=$(git rev-parse HEAD)

printf 'run output\n' > "$WORK/evidence/run.log"
printf '{"passed":true}\n' > "$WORK/evidence/nested/result.json"
ssh-keygen -q -t ed25519 -N "" -f "$WORK/keys/op_key"

# 完全没有网络命名空间。
unshare -n env PYTHONPATH=/path/to/out-of-band/src python3 -m oob.cli sign \
  --job smoke --commit "$COMMIT" --result pass \
  --evidence-dir "$WORK/evidence" --key "$WORK/keys/op_key" > "$WORK/block.md"

# 对字面字节离线验签。
python3 - "$WORK" <<'PY'
import pathlib, re, subprocess, sys
work = pathlib.Path(sys.argv[1])
block = (work / "block.md").read_text()
payload, signature = re.search(
    r"```json\n(.*)\n```\n```ssh-signature\n(.*?)\n```", block, re.S
).groups()
(work / "payload.json").write_text(payload)
(work / "payload.sig").write_text(signature + "\n")
pub = (work / "keys" / "op_key.pub").read_text().strip()
(work / "allowed_signers").write_text(f"operator {pub}\n")
result = subprocess.run(
    ["ssh-keygen", "-Y", "verify", "-f", str(work / "allowed_signers"),
     "-I", "operator", "-n", "receipt", "-s", str(work / "payload.sig")],
    input=payload.encode(), capture_output=True,
)
print("verify exit:", result.returncode)
PY
```

断网状态下，签名和验证都成功了。

## 这证明了什么，没证明什么

它证明这套机制不需要入站可达性，也不需要 GitHub 凭据：签名在本地，验证也在本地。

它不证明这台机器在其他方面做了加固。机器上可能还跑着别的服务、开着别的端口；这个测试只说明回执流程本身不要求新增监听。把回执送到 GitHub 需要一次出站 HTTPS 请求；如果操作员手工把块贴进 PR，则一次都不需要。
