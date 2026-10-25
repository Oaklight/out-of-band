# 操作员主机验证记录

[English](../en/validation.md) | [中文](validation.md)

目标：证明跑检查、签回执的那台机器不需要被访问，也不持有 GitHub 凭据。

记录于 2026-10-23，Debian 12，OpenSSH 9.2p1，Python 3.11，1 个 vCPU，内存不到 3 GiB。文中称这台机器为 **operator host**；不出现主机名、地址、用户名或设备标识。

## 测了什么

| 检查 | 结果 |
| --- | --- |
| 在空网络命名空间（`unshare -n`）里运行 `oob sign` | 退出 0，生成有效块 |
| 离线对原始 payload 运行 `ssh-keygen -Y verify` | 退出 0 |
| 主机上的 GitHub 凭据 | 没有：无 `gh` 配置，环境里无 `GH_TOKEN`/`GITHUB_TOKEN` |
| 流程需要的入站监听 | 无；每一步都是本地读取或主动发起 HTTPS |

## 过程

在操作员主机上以 root 运行，目录用完即弃。

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

# 离线验证原始字节。
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

断网状态下，签名和验证都成功。

## 这证明了什么，没证明什么

证明机制不需要入站可达，也不需要 GitHub 凭据：签名在本地，验证也在本地。

它不证明这台主机在其他方面已经加固。主机可能还跑着别的服务、开着自己的监听；这个测试只说明回执流程没有增加这种需求。把回执送到 GitHub 需要一次主动的 HTTPS 请求，操作员手动把块贴进 PR 时连这一次都不需要。

回执证明什么，见[信任](concepts/trust.md)；传输方式见[离线机器](guides/air-gapped.md)。
