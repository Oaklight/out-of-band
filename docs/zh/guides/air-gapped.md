# 指南：离线的签名机器

[English](../../en/guides/air-gapped.md) | [中文](air-gapped.md)

HPC 登录节点常常没有外网，连不上 PyPI，也没有 GitHub 凭据。流程照样能走，只是传输靠人。

`sign`、`pack`、`render` 都不开 socket。签名覆盖本地字节，`issued_at` 取主机时钟，所以时钟不准只影响时间戳，不影响有效性。

## 谁带什么

`out-of-band` 不实现传输，也不开 socket。回执是对字节的签名，任何能搬字节的通道都行，通道本身不需要可信：改一个字节就验不过。把 SSH 塞进工具，意味着要维护凭据、host key 和堡垒机规则，而且仍然覆盖不了所有站点。

跑任务的机器和签名的机器可以不是同一台。回执是操作员对证据摘要的背书，不是主机自己出具的声明。常见的分工：

1. 任务在必须跑的地方跑，写一个运行目录，放证据（日志、输出、测量值）。
2. 把证据带出来。
3. 在私钥所在的机器上签名。

### 私钥不放在集群上

首选。集群不需要钥匙、凭据，也不用装工具，只负责写目录。把目录拉回工作站再签：

```bash
ssh hpc 'tar -C ~/runs/1234 -cf - .' | tar -C ./evidence -xf -
oob sign --job bench-smoke --commit <sha> --result pass \
  --evidence-dir ./evidence --key ~/.ssh/out-of-band --repo owner/name \
  --output-file ./check-output.txt > receipt.md
```

声明说的仍是主机上发生了什么；签名表示你为它负责，摘要说明你为哪些字节负责。

### 必须由主机签名时

有些策略要求钥匙留在隔离区里。那就主机签，只有输出出来。按优先级：

**共享存储。** 登录节点和计算节点通常共享 `$HOME` 或 scratch。任务写 `~/runs/<id>/`，在登录节点签名，再从工作站拉走。不需要任何回连主机的路径。

**SSH 拉取。** 工作站能连主机（直接连或过堡垒机），反过来不行：

```bash
ssh hpc 'cat ~/runs/1234/receipt.md' > receipt.md
ssh hpc 'cat ~/runs/1234/evidence.tgz' > evidence.tgz
```

`sign` 把块写到 stdout，所以也可以在远端跑，钥匙留在主机上：

```bash
ssh hpc 'oob sign --job bench-smoke --commit <sha> --result pass \
  --evidence-dir runs/1234 --key .ssh/out-of-band --repo owner/name' > receipt.md
```

**单向物理传递。** U 盘、数据二极管，或跳板机上的内部共享。步骤不变，只是 `scp` 换成拷贝。

### runner 还需要什么

workflow 从 GitHub 的 runner 去取 `evidence-url`，不是从你的机器取。URL 必须能从面向公网的 runner 访问；HPC 内网的地址不行。在联网一侧上传归档，再 dispatch 或评论。

如果归档已经在 runner 上（比如前一步下载好了），改用 `evidence-file`。完全不想交归档，设 `require-evidence: false`。

## 把工具带进去

通常一个文件就够。每个 release 都带 `oob-<version>.pyz`：zipapp，内含包和入口，只需要 Python 3.10+。

```bash
scp oob-0.5.0.pyz host:
ssh host python3 oob-0.5.0.pyz --version
```

它的行为和安装后的命令一样，下面所有例子都可以用 `python3 oob-0.5.0.pyz` 代替 `oob`。直接运行 `./oob-0.5.0.pyz` 时，POSIX 启动器会找第一个 3.10+ 的解释器；找不到会明说，而不是抛语法错误。Windows 没有 shebang，用 `python oob-0.5.0.pyz`。

站点愿意正常安装的话，wheel 是纯 Python（`py3-none-any`），任何 3.10+ 解释器都能用。在联网机器上：

```bash
pip download out-of-band==0.5.0 -d wheelhouse
```

把 `wheelhouse/` 拷过去，然后：

```bash
python3 -m venv ~/out-of-band
~/out-of-band/bin/pip install --no-index --find-links wheelhouse out-of-band==0.5.0
~/out-of-band/bin/oob --version
```

wheel、sdist 和 zipapp 都在 release 页面，也可以直接用浏览器下载。

## 把仓库带进去

`sign` 需要本地存在那个 commit（`git cat-file -e <sha>^{commit}`）。只克隆了默认分支的仓库，拿不到 PR head。

在包含 PR ref 的 clone 里：

```bash
git bundle create lab.bundle main <pr-branch>
```

拷过去，在主机上：

```bash
git clone lab.bundle work
cd work
git checkout <head-sha>
```

主机上已经有仓库的话，把 bundle fetch 进去：

```bash
git fetch /path/to/lab.bundle <head-sha>
```

显式传 `--repo owner/name`：从 bundle 克隆出来的仓库，`origin` 可能是本地路径，转换不成仓库名。

## 签名并打包

```bash
oob sign \
  --job bench-smoke \
  --commit <head-sha> \
  --result pass \
  --evidence-dir ./evidence \
  --key ~/.ssh/out-of-band \
  --repo owner/name \
  --output-file ./check-output.txt

oob pack --evidence-dir ./evidence --out evidence.tgz
```

不联网，不要凭据，没有守护进程。

## 把结果带出来

把回执和归档拷到联网的工作站：

```bash
scp host:receipt.md host:evidence.tgz .
```

然后贴成 PR 评论，或手动跑门禁：

```bash
gh workflow run receipt-gate.yml -f pr=5 -f commit=<head-sha> \
  -f receipt="$(cat receipt.md)" -f evidence-url=<https-url-to-evidence.tgz>
```

证据 URL 必须能从 **runner** 访问，不是从 HPC 主机。传到仓库的 evidence 分支、release asset、内网对象存储都可以。workflow 会先按签名摘要核对，再保留归档。

## 这套流程解决不了什么

- 回执仍然要由人或单向传递带出来。主机没有出网路径，这是定义决定的。
- 大的原始日志打包前要裁剪。workflow 限制归档 50 MiB；签名里的 `output` 限制 4 KiB。
- 密钥轮换仍然在联网一侧做，改 `allowed_signers`。见[信任](../concepts/trust.md)。
