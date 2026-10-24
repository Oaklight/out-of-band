# 离线的操作员机器

[English](../en/offline.md) | [中文](offline.md)

HPC 的登录节点常常没有外网、连不上 PyPI，也没有 GitHub 凭据。流程照样能走，只是传输得靠人。

`sign`、`pack`、`verify` 都不开 socket。签名覆盖的是本地字节，`issued_at` 取的是本机时钟，所以时钟没同步只会让时间戳偏一点，不影响有效性。

## 谁来搬什么

out-of-band 不做传输，也不开 socket。回执是对字节的签名，只要能把字节搬过去，什么通道都行；通道本身不需要可信，改了字节就验不过。把 SSH 做进工具里，意味着要在工具内部管凭据、host key 和跳板机规则，而且仍然覆盖不了所有站点。

跑任务的机器和签名的机器可以不是同一台。回执是操作员的声明，绑定一份证据的 digest，不是机器自己吐出来的凭据。常见做法：

1. 任务在必须运行的机器上跑，留下一个目录，里面是证据（日志、输出、测量数据）。
2. 把证据带出来。
3. 在私钥所在的机器上签名。

### 私钥不要放在集群上

推荐。集群不需要密钥、不需要凭据、也不需要安装，只负责写目录。把目录拉回工作站再签：

```bash
ssh hpc 'tar -C ~/runs/1234 -cf - .' | tar -C ./evidence -xf -
oob sign --job bench-smoke --commit <sha> --result pass \
  --evidence-dir ./evidence --key ~/.ssh/out-of-band --repo owner/name \
  --output-file ./check-output.txt > receipt.md
```

声明说的仍是机器上发生了什么；签名表示你对它负责，digest 表示你具体对哪几个字节负责。

### 必须由机器本身签名

有些策略要求私钥留在内网。那就机器签，只有结果往外走。按推荐程度排：

**共享存储。** 登录节点和计算节点通常共享 `$HOME` 或某个 scratch。让任务写 `~/runs/<id>/`，在登录节点签名，再从工作站把结果拉走。不需要任何反向路由。

**SSH 拉取。** 工作站能连到机器（直连或经跳板机），反过来不行：

```bash
ssh hpc 'cat ~/runs/1234/receipt.md' > receipt.md
ssh hpc 'cat ~/runs/1234/evidence.tgz' > evidence.tgz
```

`sign` 默认把整块写到 stdout，所以私钥在机器上时也可以远程签：

```bash
ssh hpc 'oob sign --job bench-smoke --commit <sha> --result pass \
  --evidence-dir runs/1234 --key .ssh/out-of-band --repo owner/name' > receipt.md
```

**单向物理搬运。** U 盘、数据二极管、跳板机上的共享目录。步骤不变，只是 `scp` 换成拷贝。

### runner 那边仍然要求什么

workflow 是从 GitHub 的 runner 去取 `evidence-url` 的，不是从你的机器。所以这个地址必须对公网的 runner 可达；放在 HPC 内网的地址不行。从能上网的一侧上传压缩包，再评论或 dispatch。

## 把工具带进去

通常一个文件就够了。每个 release 都带 `oob-<version>.pyz`：一个 zipapp，内含包和入口，只需要 Python 3.10+。

```bash
scp oob-0.4.0.pyz host:
ssh host python3 oob-0.4.0.pyz --version
```

它的用法和装好的命令一样，下面所有例子都能把 `oob` 换成 `python3 oob-0.4.0.pyz`。直接执行 `./oob-0.4.0.pyz` 时，里面的 POSIX 启动脚本会挑第一个 Python 3.10+；一个都没有就明确报错，不会抛出一句看不懂的语法错误。Windows 没有 shebang，用 `python oob-0.4.0.pyz`。

如果站点更习惯正常安装，wheel 是纯 Python（`py3-none-any`），任何 3.10+ 解释器都能用。在能上网的机器上：

```bash
pip download out-of-band==0.4.0 -d wheelhouse
```

把 `wheelhouse/` 拷过去，然后：

```bash
python3 -m venv ~/out-of-band
~/out-of-band/bin/pip install --no-index --find-links wheelhouse out-of-band==0.4.0
~/out-of-band/bin/oob --version
```

wheel、sdist 和 zipapp 都在 release 页面上，也可以直接用浏览器下载。

## 把仓库带进去

`sign` 要求 commit 在本地存在（`git cat-file -e <sha>^{commit}`）。只克隆了默认分支的仓库，拿不到 PR head。

在带有 PR ref 的克隆里：

```bash
git bundle create lab.bundle main <pr-branch>
```

拷过去，然后在目标机器上：

```bash
git clone lab.bundle work
cd work
git checkout <head-sha>
```

如果目标机器上已经有仓库，就把 bundle fetch 进去：

```bash
git fetch /path/to/lab.bundle <head-sha>
```

显式传 `--repo owner/name`：从 bundle 克隆出来的仓库，`origin` 可能是一个本地路径，没法转成仓库名。

## 签名和打包

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

不需要网络、不需要凭据、不需要常驻进程。

## 把结果带出来

把回执和压缩包拷回能上网的工作站：

```bash
scp host:receipt.md host:evidence.tgz .
```

然后二选一：把回执发成 PR 评论，或者手动跑门禁：

```bash
gh workflow run receipt-gate.yml -f pr=5 -f commit=<head-sha> \
  -F receipt=@receipt.md -f evidence-url=<https-url-to-evidence.tgz>
```

证据地址必须对 **runner** 可达，而不是对 HPC 机器可达。放到仓库的 evidence 分支、PR 附件、内部对象存储都可以；workflow 会先按签名 digest 校验，再决定是否保留。

## 这套方案解决不了什么

- 回执终究要靠人或单向传输带出来。机器没有出网路径，这是定义决定的。
- 原始日志太大就该先筛选。workflow 对压缩包的限制是 50 MiB，签名里的 `output` 限制是 4 KiB。
- 密钥轮换仍然在能上网的一侧做，改 `allowed_signers` 即可。
