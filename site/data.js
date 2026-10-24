/* Content for the tour. Every user-visible string carries en and zh. */

const UI = {
  en: {
    navTour: "Tour",
    navScenarios: "Scenarios",
    navStates: "States",
    navFaq: "Why not…",
    kicker: "Out-of-band CI receipts",
    title: "Prove the test ran, when GitHub cannot run it.",
    lede:
      "A job runs on hardware GitHub cannot reach. The machine signs one line of JSON. GitHub verifies the signature and turns the verdict into a check run. No inbound access, and no GitHub credential on the machine.",
    simulation:
      "This page is a simulation: the pull request and its checks are mock-ups.",
    tourTitle: "Follow one receipt from a pull request to a green check",
    tourLede:
      "Pick a scenario, then step through it. The left pane is what GitHub sees; the right pane is what happens on the machine you control.",
    paneGithub: "GitHub",
    paneMachine: "Your side",
    prev: "Back",
    next: "Next",
    counter: "Step {n} of {m}",
    variantsTitle: "The other shapes",
    variantsLede:
      "The tour covers three. These are the rest, with the full procedures in the repository.",
    statesTitle: "Four states, never collapsed",
    statesLede:
      "Turning “I could not tell” into “pass” is worse than having no gate, so these states stay separate.",
    adoptTitle: "Adopting it for real",
    adoptLede:
      "Five steps, in order. The guides in docs/ carry the exact commands.",
    adoptNote:
      "You write the workflow once. A new pull request needs a receipt, not a workflow edit. Changing the pinned SHA is an upgrade you choose, not part of every PR.",
    limitsTitle: "When GitHub does not run the test",
    limitsLede: "Usually one of these.",
    limits: [
      {
        title: "No runner has the hardware",
        text: "An accelerator, a capture card, a licensed toolchain, a particular OS image.",
      },
      {
        title: "No route in or out",
        text: "Behind a firewall, or a site that forbids agents and outbound polling.",
      },
      {
        title: "The data cannot leave",
        text: "The test needs data that is not allowed to reach a hosted runner.",
      },
      {
        title: "It is not a CI machine",
        text: "An hourly rental, or a login node with a scheduler. A runner there is disproportionate or forbidden.",
      },
      {
        title: "You already ran it",
        text: "Re-running on a runner is slow, flaky, or gives a different number. Sign the run you have.",
      },
    ],
    faqTitle: "Why not just…",
    faqLede: "These alternatives all have a place. Here is where each one stops.",
    faq: [
      {
        q: "…run a self-hosted runner on that machine?",
        a: "The right answer when the machine can reach GitHub and you control what runs on it. It needs persistent outbound access, and it executes workflow code from the repository, which is a serious attack surface for a public repo. Ephemeral GPUs and scheduler-managed login nodes rarely fit. If it fits, use it. This tool is for when it does not.",
      },
      {
        q: "…put a GitHub token on the machine and post a status?",
        a: "A long-lived credential now lives on the machine you wanted to keep clean. A PAT can create commit statuses but not check runs, and a status is a label: nothing binds it to the evidence or the tree. A receipt needs no credential, and the signature covers the claim itself.",
      },
      {
        q: "…just run the test in CI?",
        a: "If a hosted runner can run it, do that. Out-of-band is the fallback.",
      },
      {
        q: "…approve it by hand with a comment?",
        a: "“LGTM” names no commit, no job, and no evidence, and it can be edited or deleted. A receipt is machine-checked, bound to one commit and one evidence digest, and stays verifiable.",
      },
      {
        q: "…upload the log somewhere and link it?",
        a: "Anyone can upload anything, and a link proves nothing about the commit. Evidence upload is optional here; when it is used, the bundle is re-hashed against the signed digest before it is kept.",
      },
      {
        q: "…use Sigstore or GitHub's artifact attestations?",
        a: "Use them when the job runs in Actions: the workflow's OIDC identity is what signs. A machine outside Actions has no such identity, and keyless signing needs Fulcio and Rekor. Sigstore can sign a blob offline with a key, but the GitHub-side gate is still yours to build: who may sign, for which commit, and over what evidence. Out-of-band is that gate.",
      },
      {
        q: "…use Jenkins?",
        a: "Fine if you have it and it can reach GitHub. It still needs a credential and a network path, and its result is a status like any other. Out-of-band covers the case where neither is available.",
      },
    ],
    footerDocs: "Docs",
    footerRelease: "Releases",
    openGuide: "Open the guide →",
    actors: [
      {
        title: "GitHub",
        tag: "public side",
        items: [
          "the pull request and its comments",
          "the gate workflow and the check",
          "allowed_signers, on the default branch",
        ],
        flow: "reads the receipt · publishes a check",
      },
      {
        title: "Operator machine",
        tag: "you control it",
        items: [
          "the private key",
          "oob sign / verify",
          "no GitHub credential",
        ],
        flow: "signs bytes · never opens a socket",
      },
      {
        title: "Restricted machine",
        tag: "runs the job",
        items: [
          "GPU, device, or cluster",
          "writes the evidence directory",
          "no outbound network required",
        ],
        flow: "produces evidence · nothing else",
      },
    ],
  },
  zh: {
    navTour: "导览",
    navScenarios: "场景",
    navStates: "状态",
    navFaq: "为什么不用…",
    kicker: "带外 CI 回执",
    title: "GitHub 跑不了的测试，也能证明它跑过。",
    lede:
      "任务跑在 GitHub 够不着的机器上。机器对一行 JSON 签名，GitHub 验签，再把结论变成 check run。不需要入站访问，机器上也不需要 GitHub 凭据。",
    simulation: "这一页是模拟的：PR 和 check 都是假的。",
    tourTitle: "跟着一份回执，从 PR 走到绿色的 check",
    tourLede:
      "先选一个场景，再一步步走。左边是 GitHub 看到的东西，右边是你控制的机器上发生的事。",
    paneGithub: "GitHub",
    paneMachine: "你这一侧",
    prev: "上一步",
    next: "下一步",
    counter: "第 {n} 步，共 {m} 步",
    variantsTitle: "其他几种形态",
    variantsLede: "导览覆盖了三种。这里是剩下的，完整步骤在仓库的文档里。",
    statesTitle: "四种状态，别混为一谈",
    statesLede:
      "把“判断不了”说成“通过”，比没有门禁更糟，所以这几种状态始终分开。",
    adoptTitle: "真的要用起来",
    adoptLede: "五步，按顺序来。具体命令在 docs/ 里。",
    adoptNote:
      "workflow 只写一次。之后每个 PR 需要的是回执，不是改 workflow。改固定的 SHA 是一次你主动决定的小升级，不是每个 PR 的例行公事。",
    limitsTitle: "什么情况下 GitHub 不跑这个测试",
    limitsLede: "通常是下面几种情况之一。",
    limits: [
      {
        title: "没有 runner 具备那套硬件",
        text: "加速卡、采集卡、带 license 的工具链、某个特定的系统镜像。",
      },
      {
        title: "进不来，也出不去",
        text: "机器在防火墙后面，或者站点禁止装 agent、禁止向外轮询。",
      },
      {
        title: "数据不能离开",
        text: "测试要用的数据不允许出现在托管 runner 上。",
      },
      {
        title: "它根本不是 CI 机器",
        text: "按小时租的卡，或者带调度器的登录节点。在上面装 runner 要么小题大做，要么不被允许。",
      },
      {
        title: "你已经跑过了",
        text: "放到 runner 上重跑，可能更慢、更不稳定，数字也可能不一样。直接签手上这次。",
      },
    ],
    faqTitle: "那为什么不直接用……",
    faqLede: "这些替代方案各有适用的时候。下面说它们各自卡在哪。",
    faq: [
      {
        q: "……在那台机器上跑 self-hosted runner？",
        a: "机器能连 GitHub、你也管得住上面跑什么，这就是正解。但它要求持续的出网连接，而且会执行仓库里的 workflow 代码；对公开仓库来说，这是实打实的攻击面。按小时租的 GPU、带调度器的登录节点，通常不合适。合适就用；out-of-band 管的是不合适的那种。",
      },
      {
        q: "……在机器上放一个 GitHub token，直接发 status？",
        a: "那台你本想保持干净的机器上，从此多了一个长期凭据。PAT 只能创建 commit status，不能创建 check run；status 只是个标签，既不绑定证据，也不绑定 tree。回执不需要凭据，签名覆盖的就是声明本身。",
      },
      {
        q: "……直接在 CI 里跑？",
        a: "托管 runner 跑得了、也不贵，就该在 CI 里跑。out-of-band 也管另一种情况：结果已经在手上，重跑又慢又不稳。",
      },
      {
        q: "……人工评论一句批准？",
        a: "“LGTM”没有指明 commit、job，也没有证据，而且可以改、可以删。回执是机器校验的，绑定一个 commit 和一份证据 digest，之后仍然可验证。",
      },
      {
        q: "……把日志传到某个地方，贴个链接？",
        a: "谁都能上传任何东西，一个链接也证明不了它和 commit 的关系。这里的证据上传是可选的；用了的话，会按签名 digest 重新校验，对不上就不保留。",
      },
      {
        q: "……用 Sigstore 或 GitHub 的 artifact attestation？",
        a: "任务在 Actions 里跑，就用它们：签名用的是 workflow 的 OIDC 身份。Actions 之外的机器没有这个身份，keyless 签名还要连 Fulcio 和 Rekor。Sigstore 可以用密钥离线签一个 blob，但 GitHub 这一侧的门禁还是得自己搭：谁能签、签哪个 commit、覆盖哪份证据。out-of-band 做的就是这道门。",
      },
      {
        q: "……用 Jenkins？",
        a: "有 Jenkins、它又能连 GitHub，那就用。但它同样需要凭据和一条网络通路，结果也只是个 status。两者都没有的时候，才轮到 out-of-band。",
      },
    ],
    footerDocs: "文档",
    footerRelease: "发布",
    openGuide: "打开指南 →",
    actors: [
      {
        title: "GitHub",
        tag: "公开的一侧",
        items: [
          "PR 和它下面的评论",
          "门禁 workflow 和 check",
          "默认分支上的 allowed_signers",
        ],
        flow: "读取回执 · 发布 check",
      },
      {
        title: "操作员机器",
        tag: "你控制它",
        items: ["私钥", "oob sign / verify", "不需要 GitHub 凭据"],
        flow: "对字节签名 · 不开 socket",
      },
      {
        title: "受限机器",
        tag: "跑任务的地方",
        items: [
          "GPU、设备或集群",
          "写出证据目录",
          "不需要外网",
        ],
        flow: "产出证据 · 别的都不做",
      },
    ],
  },
};

const SCENARIOS = [
  {
    id: "patch",
    label: { en: "Patch gate", zh: "补丁门禁" },
    blurb: {
      en: "A pull request that needs a hardware smoke test before it merges.",
      zh: "合并前必须在硬件上做冒烟测试的 PR。",
    },
    steps: [
      {
        nav: { en: "A PR CI can't test", zh: "CI 测不了的 PR" },
        title: {
          en: "The rule is about a path, not an identity.",
          zh: "规则看的是路径，不是身份。",
        },
        body: {
          en: "A change under <code>patches/</code> needs a device test. The hosted runner cannot provide the device, so branch protection waits on a check the hosted runner cannot produce. The rest of this tour makes that check worth trusting.",
          zh: "<code>patches/</code> 下的改动要在设备上测。托管的 runner 给不了设备，于是分支保护在等一个只能从外部来的 check。后面几步要做的，就是让这个 check 值得信任。",
        },
        github: [
          { t: "event", text: "pull_request_target · synchronize" },
          {
            t: "pr",
            title: {
              en: "Fix fp16 accumulation in attention",
              zh: "修正 attention 的 fp16 累加",
            },
            meta: {
              en: "#5 · main ← kernel/fp16 · 1 file",
              zh: "#5 · main ← kernel/fp16 · 1 个文件",
            },
          },
          {
            t: "files",
            items: [{ path: "patches/0001-fp16-accum.patch", add: "+18", del: "−2" }],
          },
          {
            t: "checks",
            items: [
              {
                name: "patch-smoke-verified",
                state: "missing",
                text: { en: "required · not run", zh: "必需 · 未运行" },
              },
              { name: "lint", state: "ok", text: "pass" },
            ],
          },
          {
            t: "note",
            text: {
              en: "The required check has never run. GitHub shows it as waiting, not as failed.",
              zh: "必需的 check 从没跑过。GitHub 把它显示成等待，而不是失败。",
            },
          },
        ],
        machine: [
          {
            t: "term",
            title: { en: "Your workstation", zh: "你的工作站" },
            lines: [
              { k: "cmd", text: "$ gh pr checkout 5" },
              { k: "out", text: "Switched to branch 'kernel/fp16'" },
              { k: "cmd", text: "$ git rev-parse HEAD" },
              { k: "ok", text: "6e5b8a482f1baf41c8080b79501294cbf4057987" },
            ],
          },
          {
            t: "note",
            text: {
              en: "Sign the head commit: not the merge commit, not a branch name. Branches move; commits do not.",
              zh: "签 head commit：不是 merge commit，也不是分支名。分支会动，commit 不会。",
            },
          },
        ],
      },
      {
        nav: { en: "The rule", zh: "规则" },
        title: {
          en: "Two jobs: decide, then verify.",
          zh: "两条 job：先判断，再验证。",
        },
        body: {
          en: "The repository owns the policy. <code>policy</code> decides whether this diff touches the paths that need proof. <code>verified</code> calls the shared verifier, pinned by commit SHA. The verifier reads <code>allowed_signers</code> from the default branch, so a pull request cannot vouch for itself.",
          zh: "策略在仓库这一侧。<code>policy</code> 判断这次改动有没有碰到需要证明的路径；<code>verified</code> 调用共享验证器，用 commit SHA 固定版本。验证器从默认分支读 <code>allowed_signers</code>，所以 PR 没法给自己作保。",
        },
        github: [
          {
            t: "code",
            text:
              "jobs:\n" +
              "  policy:\n" +
              "    outputs:\n" +
              "      pr:       ${{ steps.ctx.outputs.pr }}\n" +
              "      commit:   ${{ steps.ctx.outputs.commit }}\n" +
              "      requires: ${{ steps.paths.outputs.requires }}\n" +
              "    steps:\n" +
              "      - id: ctx\n" +
              "        run: gh api .../pulls/$PR --jq .head.sha\n" +
              "      - id: paths\n" +
              "        run: gh api .../pulls/$PR/files\n" +
              "  verified:\n" +
              "    needs: policy\n" +
              "    uses: Oaklight/out-of-band/.github/workflows/verify.yml@<sha>\n" +
              "    with:\n" +
              "      pr:         ${{ needs.policy.outputs.pr }}\n" +
              "      commit:     ${{ needs.policy.outputs.commit }}\n" +
              "      job:        patch-smoke\n" +
              "      required:   ${{ needs.policy.outputs.requires }}\n" +
              "      check-name: patch-smoke-verified",
          },
          {
            t: "kv",
            items: [
              {
                k: "<sha>",
                v: {
                  en: "the commit of the out-of-band repository that you pin; copy it from the release page",
                  zh: "你要固定的 out-of-band 仓库 commit，从 release 页面复制",
                },
              },
              {
                k: "job",
                v: {
                  en: "must equal the operator's <code>--job</code>",
                  zh: "必须和操作员的 <code>--job</code> 一致",
                },
              },
              {
                k: "check-name",
                v: {
                  en: "the string branch protection requires",
                  zh: "分支保护要匹配的那个字符串",
                },
              },
              {
                k: "trusted-authors",
                v: {
                  en: "your GitHub login; optional, but recommended",
                  zh: "你的 GitHub 登录名；可选，但建议填",
                },
              },
            ],
          },
          {
            t: "note",
            text: {
              en: "Everything inside <code>${{ }}</code> is filled by GitHub at run time. You do not touch it.",
              zh: "<code>${{ }}</code> 里的东西由 GitHub 在运行时填好，不用管。",
            },
          },
          {
            t: "note",
            text: {
              en: "The gate runs <code>pull_request_target</code>: GitHub takes this file from the default branch, so a PR cannot edit the check that judges it.",
              zh: "门禁用 <code>pull_request_target</code>：文件取自默认分支，PR 改不了审判自己的 check。",
            },
          },
        ],
        machine: [
          {
            t: "note",
            text: {
              en: "None of this matters to the machine. It needs the commit, the evidence, and the key.",
              zh: "这些配置和机器无关。机器只需要 commit、证据和私钥。",
            },
          },
        ],
      },
      {
        nav: { en: "Run it", zh: "跑测试" },
        title: {
          en: "Run the test where the hardware is, and keep what it printed.",
          zh: "在硬件所在的地方跑，把它打印的东西留下。",
        },
        body: {
          en: "The evidence directory is what the receipt will bind. It does not have to be tidy; it has to be the thing you are willing to stand behind.",
          zh: "回执绑定的是证据目录。它不必好看，但必须是你愿意为之负责的东西。",
        },
        github: [
          { t: "event", text: "still waiting" },
          {
            t: "checks",
            items: [
              {
                name: "patch-smoke-verified",
                state: "missing",
                text: { en: "required · not run", zh: "必需 · 未运行" },
              },
            ],
          },
          {
            t: "note",
            text: {
              en: "Nothing has been sent to GitHub yet.",
              zh: "此刻还没有任何东西发给 GitHub。",
            },
          },
        ],
        machine: [
          {
            t: "term",
            title: { en: "The machine with the device", zh: "有设备的那台机器" },
            lines: [
              { k: "cmd", text: "$ mkdir -p ~/runs/5/evidence" },
              { k: "cmd", text: "$ ./scripts/smoke.sh 2>&1 \\" },
              { k: "cmd", text: "    | tee ~/runs/5/evidence/smoke.log" },
              { k: "ok", text: "[ok] driver 550.54" },
              { k: "ok", text: "[ok] patch applies cleanly" },
              { k: "ok", text: "[ok] forward pass matches reference" },
              { k: "cmd", text: "$ sha256sum ~/runs/5/evidence/smoke.log" },
              { k: "out", text: "4b1d9c2e...  smoke.log" },
            ],
          },
          {
            t: "note",
            text: {
              en: "Keep the command lines in the log. Six months later they are the difference between evidence and a rumour.",
              zh: "把命令行留在日志里。半年后，它是证据和传闻的区别。",
            },
          },
        ],
      },
      {
        nav: { en: "Sign", zh: "签名" },
        title: {
          en: "One command turns the directory into a claim.",
          zh: "一条命令，把目录变成一份声明。",
        },
        body: {
          en: "<code>oob sign</code> hashes every file, hashes the sorted file list, reads the commit's tree from the local repository, and signs one line of JSON with your SSH key. It opens no socket.",
          zh: "<code>oob sign</code> 逐个文件算哈希，再对排好序的文件清单算一次，从本地仓库读出 commit 的 tree，最后用 SSH 私钥对一行 JSON 签名。它不开任何 socket。",
        },
        github: [
          {
            t: "note",
            text: { en: "Still nothing here.", zh: "这边仍然什么都没有。" },
          },
        ],
        machine: [
          {
            t: "term",
            title: { en: "Same machine, still offline", zh: "同一台机器，仍然离线" },
            lines: [
              { k: "cmd", text: "$ oob sign --job patch-smoke \\" },
              { k: "cmd", text: "    --commit 6e5b8a4 --result pass \\" },
              { k: "cmd", text: "    --evidence-dir ~/runs/5/evidence \\" },
              { k: "cmd", text: "    --key ~/.ssh/out-of-band --repo you/repo \\" },
              { k: "cmd", text: "    --output-file ~/runs/5/summary.txt \\" },
              { k: "cmd", text: "    --out receipt.md" },
              { k: "ok", text: "wrote receipt.md" },
            ],
          },
          {
            t: "receipt",
            label: { en: "receipt.md", zh: "receipt.md" },
            text:
              "<!-- receipt:v2 -->\n" +
              "```json\n" +
              '{"schema":"receipt/v2","repo":"you/repo","commit":"6e5b8a4...",\n' +
              ' "tree":"f0c1...","job":"patch-smoke","result":"pass",\n' +
              ' "issued_at":"2026-10-23T21:40:00Z","tool":"oob/0.4.0",\n' +
              ' "evidence":{"count":1,"digest":"sha256:7b6f..."},\n' +
              ' "output":"[ok] driver 550.54\\n[ok] patch applies cleanly\\n..."}\n' +
              "```\n" +
              "```ssh-signature\n" +
              "-----BEGIN SSH SIGNATURE-----\n" +
              "U1NIU0lHAAAAAQAAADMAAAALc3NoLWVkMjU1MTkAAAAg...\n" +
              "-----END SSH SIGNATURE-----\n" +
              "```",
          },
          {
            t: "chips",
            items: [
              { en: "no network", zh: "不需要网络" },
              { en: "no GitHub token", zh: "不需要 GitHub token" },
              { en: "key stays here", zh: "私钥不离开" },
            ],
          },
          {
            t: "note",
            text: {
              en: "The excerpt you passed to <code>--output-file</code> is signed too, so it cannot drift from the claim. It appears folded in the check.",
              zh: "传给 <code>--output-file</code> 的摘录同样被签名，不会和声明脱节。它会折叠显示在 check 里。",
            },
          },
        ],
      },
      {
        nav: { en: "Deliver", zh: "交付" },
        title: {
          en: "Post the block as a comment. That is the whole transport.",
          zh: "把整块发成评论，传输就完成了。",
        },
        body: {
          en: "Any channel works: a PR comment, a dispatch input, a file. The signature covers bytes, so the channel does not need to be trusted. The comment marker makes the workflow re-run; the receipt names the head commit, so a stale comment is ignored rather than deleted.",
          zh: "什么通道都行：PR 评论、dispatch 输入、一个文件。签名覆盖的是字节，所以通道不需要可信。评论里的标记会让 workflow 重跑；回执写明了 head commit，旧评论会被忽略，不用删。",
        },
        github: [
          { t: "event", text: "issue_comment · created" },
          {
            t: "comment",
            author: "operator",
            time: { en: "just now", zh: "刚刚" },
            body:
              "<!-- receipt:v2 -->\n" +
              "```json\n" +
              '{"schema":"receipt/v2","repo":"you/repo", "...": "..."}\n' +
              "```\n" +
              "```ssh-signature\n" +
              "-----BEGIN SSH SIGNATURE-----\n" +
              "U1NIU0lHAAAAAQAAADMAAAALc3NoLWVkMjU1MTkAAAAg...\n" +
              "-----END SSH SIGNATURE-----\n" +
              "```",
          },
          {
            t: "checks",
            items: [
              {
                name: "patch-smoke-verified",
                state: "pending",
                text: { en: "queued", zh: "排队中" },
              },
            ],
          },
        ],
        machine: [
          {
            t: "term",
            title: { en: "Delivering", zh: "交付" },
            lines: [
              { k: "cmd", text: "$ gh pr comment 5 --body-file receipt.md" },
              { k: "ok", text: "https://github.com/you/repo/pull/5#issuecomment-..." },
            ],
          },
          {
            t: "note",
            text: {
              en: "Or paste it by hand. Or carry it off an air-gapped site and post it from a laptop; the signature survives the trip.",
              zh: "也可以手工粘贴。或者从离线站点带出来，在笔记本上发；签名经得起这一趟。",
            },
          },
        ],
      },
      {
        nav: { en: "Verify", zh: "验证" },
        title: {
          en: "The runner verifies, then publishes a check.",
          zh: "runner 验签，然后发布 check。",
        },
        body: {
          en: "The workflow re-reads the default branch, verifies the signature, binds repository, commit, tree, and job, and checks the evidence bundle if a URL was given. The verdict becomes a check run, a step summary, and one sticky comment.",
          zh: "workflow 重新读默认分支，验签，核对仓库、commit、tree 和 job；如果给了证据地址，再校验压缩包。结论会变成 check run、step summary 和一条置顶评论。",
        },
        github: [
          { t: "event", text: "check_suite · completed" },
          {
            t: "checks",
            items: [
              {
                name: "patch-smoke-verified",
                state: "ok",
                text: { en: "verified · 11s", zh: "verified · 11 秒" },
              },
              { name: "lint", state: "ok", text: "pass" },
            ],
          },
          {
            t: "jobs",
            items: [
              { name: "policy", state: "ok", time: "4s" },
              { name: "verified / verify", state: "ok", time: "11s" },
            ],
          },
          {
            t: "summary",
            title: "oob: verified",
            body:
              "job: patch-smoke\n" +
              "commit: 6e5b8a482f1baf41c8080b79501294cbf4057987\n" +
              "state: verified\n" +
              "code: OK\n" +
              "source: comments\n" +
              "evidence: digest only",
            details: {
              en: "check output",
              zh: "check 输出",
            },
            transcript:
              "$ ./scripts/smoke.sh\n" +
              "[ok] driver 550.54\n" +
              "[ok] patch applies cleanly\n" +
              "[ok] forward pass matches reference",
          },
        ],
        machine: [
          {
            t: "note",
            text: {
              en: "Your machine does nothing else. No daemon, no polling, no credential.",
              zh: "你的机器没再做别的事。没有常驻进程，没有轮询，没有凭据。",
            },
          },
          {
            t: "checklist",
            items: [
              { en: "ran the smoke test", zh: "跑了冒烟测试" },
              { en: "wrote evidence/", zh: "写出 evidence/" },
              { en: "signed one line", zh: "签了一行" },
              { en: "opened no socket", zh: "没开任何 socket" },
            ],
          },
        ],
      },
    ],
  },
  {
    id: "bench",
    label: { en: "Benchmark run", zh: "Benchmark 运行" },
    blurb: {
      en: "A result on a rented GPU, with no pull request in sight.",
      zh: "租来的 GPU 上跑出的结果，根本没有 PR。",
    },
    steps: [
      {
        nav: { en: "A run on a rented GPU", zh: "租来的 GPU" },
        title: {
          en: "Some results belong to a commit, not to a pull request.",
          zh: "有些结果属于 commit，不属于 PR。",
        },
        body: {
          en: "A benchmark finished on a rented V100. There is no pull request; the commit is on main. Check runs attach to commits, so the target is the SHA you actually tested, not a branch, tag, or “latest”.",
          zh: "在租来的 V100 上跑完了一次 benchmark。没有 PR，commit 在 main 上。check run 挂在 commit 上，所以对象是你实际测过的那个 SHA，不是分支、tag 或“最新”。",
        },
        github: [
          { t: "event", text: "commit 6e5b8a4 · main" },
          {
            t: "pr",
            title: { en: "6e5b8a4", zh: "6e5b8a4" },
            meta: {
              en: "No checks reported for this commit",
              zh: "这个 commit 上没有任何 check",
            },
          },
          {
            t: "note",
            text: {
              en: "No pull request means no comment box. Delivery has to be a dispatch.",
              zh: "没有 PR 就没有评论框。交付只能走 dispatch。",
            },
          },
        ],
        machine: [
          {
            t: "term",
            title: { en: "The GPU box", zh: "GPU 机器" },
            lines: [
              {
                k: "cmd",
                text: "$ python bench.py --device cuda:0 --tokens 4096",
              },
              { k: "out", text: "warming up..." },
              { k: "ok", text: "throughput 1843 tok/s" },
              { k: "cmd", text: "$ ls results/" },
              { k: "out", text: "bench.json  run.log  gpu.txt" },
            ],
          },
          {
            t: "note",
            text: {
              en: "Everything under <code>results/</code> is what the receipt will bind.",
              zh: "回执绑定的，就是 <code>results/</code> 里的全部内容。",
            },
          },
        ],
      },
      {
        nav: { en: "Wire a dispatch-only gate", zh: "只管手动触发的门禁" },
        title: {
          en: "One small caller, no pull request required.",
          zh: "一个小的调用方，不需要 PR。",
        },
        body: {
          en: "<code>pr: \"0\"</code> disables comment scanning and the sticky comment. The check is created on <code>inputs.commit</code>, so the run can be dispatched from any branch.",
          zh: "<code>pr: \"0\"</code> 表示不扫评论、也不发置顶评论。check 建在 <code>inputs.commit</code> 上，所以 workflow 从任何分支触发都行。",
        },
        github: [
          {
            t: "code",
            text:
              "on:\n" +
              "  workflow_dispatch:\n" +
              "    inputs:\n" +
              "      commit:       { required: true }\n" +
              "      receipt:      { required: true }\n" +
              '      evidence-url: { default: "" }\n' +
              "\n" +
              "jobs:\n" +
              "  verified:\n" +
              "    uses: Oaklight/out-of-band/.github/workflows/verify.yml@<sha>\n" +
              "    with:\n" +
              '      pr: "0"\n' +
              "      commit: ${{ inputs.commit }}\n" +
              "      job: v100-bench\n" +
              "      check-name: v100-bench-verified\n" +
              "      receipt: ${{ inputs.receipt }}\n" +
              "      evidence-url: ${{ inputs.evidence-url }}",
          },
        ],
        machine: [
          {
            t: "note",
            text: {
              en: "The workflow file lives on the default branch. The commit being attested does not have to be the branch head.",
              zh: "workflow 文件放在默认分支上。被背书的 commit 不必是分支头。",
            },
          },
        ],
      },
      {
        nav: { en: "Sign with a transcript", zh: "带摘录签名" },
        title: {
          en: "Put the interesting part inside the receipt.",
          zh: "把有用的部分签进回执里。",
        },
        body: {
          en: "<code>--output-file</code> adds up to 4 KiB to the signed claim, and it appears folded in the check. The rest goes into the evidence bundle, which the runner can fetch and re-hash.",
          zh: "<code>--output-file</code> 最多给签名声明加 4 KiB，会折叠显示在 check 里。其余内容进证据包，runner 可以取下来重新算 digest。",
        },
        github: [
          {
            t: "note",
            text: {
              en: "Nothing is published until the dispatch.",
              zh: "在 dispatch 之前，什么都不会发布。",
            },
          },
        ],
        machine: [
          {
            t: "term",
            title: { en: "On the GPU box", zh: "GPU 机器上" },
            lines: [
              { k: "cmd", text: "$ oob sign --job v100-bench \\" },
              { k: "cmd", text: "    --commit 6e5b8a4 --result pass \\" },
              { k: "cmd", text: "    --evidence-dir results \\" },
              { k: "cmd", text: "    --key ~/.ssh/out-of-band \\" },
              { k: "cmd", text: "    --repo you/repo --output-file summary.txt \\" },
              { k: "cmd", text: "    --out receipt.md" },
              { k: "cmd", text: "$ oob pack --evidence-dir results \\" },
              { k: "cmd", text: "    --out evidence.tgz" },
              { k: "ok", text: "wrote receipt.md, evidence.tgz" },
            ],
          },
          {
            t: "chips",
            items: [
              { en: "4 KiB transcript", zh: "4 KiB 摘录" },
              { en: "50 MiB bundle", zh: "50 MiB 证据包" },
              { en: "digest binds both", zh: "digest 把两者绑定" },
            ],
          },
        ],
      },
      {
        nav: { en: "Park the bundle", zh: "放置证据包" },
        title: {
          en: "The transport does not need to be trusted.",
          zh: "传输通道不需要可信。",
        },
        body: {
          en: "Push it to an <code>evidence/&lt;sha&gt;</code> branch, attach it to a release, or hand out a signed object-store URL. The workflow downloads it, extracts it without following links, re-hashes it, and refuses a mismatch as <code>E_EVIDENCE_MISMATCH</code>.",
          zh: "推到 <code>evidence/&lt;sha&gt;</code> 分支、挂到 release，或者给一个对象存储的签名 URL。workflow 会下载、在不跟随链接的前提下解压、重新算 digest；对不上就报 <code>E_EVIDENCE_MISMATCH</code>。",
        },
        github: [
          {
            t: "note",
            text: {
              en: "The URL must be reachable from GitHub's runner, not from the GPU host.",
              zh: "地址必须对 GitHub 的 runner 可达，而不是对 GPU 机器可达。",
            },
          },
        ],
        machine: [
          {
            t: "term",
            title: { en: "Somewhere with a network", zh: "一台能上网的机器" },
            lines: [
              { k: "cmd", text: "$ git checkout --orphan evidence/6e5b8a4" },
              { k: "cmd", text: "$ git add evidence.tgz" },
              { k: "cmd", text: "$ git commit -m evidence" },
              { k: "cmd", text: "$ git push origin evidence/6e5b8a4" },
              { k: "ok", text: "https://github.com/you/repo/blob/evidence/6e5b8a4/evidence.tgz" },
            ],
          },
          {
            t: "note",
            text: {
              en: "A GPU host with no outbound network never uploads anything. A workstation does it.",
              zh: "没有外网的 GPU 机器不上传任何东西，由工作站来做。",
            },
          },
        ],
      },
      {
        nav: { en: "Dispatch", zh: "提交" },
        title: {
          en: "Hand over the receipt and the address together.",
          zh: "把回执和地址一起交上去。",
        },
        body: {
          en: "The dispatch input takes the block as text. <code>-F</code> reads it from a file, so shell quoting cannot mangle the backticks and newlines.",
          zh: "dispatch 输入收的是整块文本。<code>-F</code> 从文件读，反引号和换行不会被 shell 吃掉。",
        },
        github: [
          { t: "event", text: "workflow_dispatch" },
          {
            t: "checks",
            items: [
              {
                name: "v100-bench-verified",
                state: "pending",
                text: { en: "queued", zh: "排队中" },
              },
            ],
          },
          {
            t: "note",
            text: {
              en: "The receipt travels as an input, not a comment. No pull request is involved.",
              zh: "回执作为输入传进来，不走评论。整个过程没有 PR。",
            },
          },
        ],
        machine: [
          {
            t: "term",
            title: { en: "From a laptop, not the GPU box", zh: "在笔记本上，不是 GPU 机器" },
            lines: [
              { k: "cmd", text: "$ gh workflow run bench-gate.yml \\" },
              { k: "cmd", text: "    -f commit=6e5b8a4... \\" },
              { k: "cmd", text: "    -F receipt=@receipt.md \\" },
              {
                k: "cmd",
                text: "    -f evidence-url=https://.../evidence.tgz",
              },
              { k: "ok", text: "Created workflow_dispatch event" },
            ],
          },
          {
            t: "note",
            text: {
              en: "The GPU host never sees this command. It only produced the receipt and the bundle.",
              zh: "GPU 机器看不到这条命令。它只负责产出回执和压缩包。",
            },
          },
        ],
      },
      {
        nav: { en: "The check lands", zh: "check 落地" },
        title: {
          en: "The check lands on that commit, not on the branch.",
          zh: "check 落在那个 commit 上，不落在分支上。",
        },
        body: {
          en: "The verdict is now attached to the SHA that was tested. Re-run the benchmark on a new commit and it gets its own receipt; the old one stays true about the old code.",
          zh: "结论现在挂在被测的那个 SHA 上。新 commit 上再跑一次，就有它自己的回执；旧回执仍然只对旧代码为真。",
        },
        github: [
          { t: "event", text: "check_suite · completed" },
          {
            t: "checks",
            items: [
              {
                name: "v100-bench-verified",
                state: "ok",
                text: { en: "verified", zh: "verified" },
              },
            ],
          },
          {
            t: "summary",
            title: "oob: verified",
            body:
              "job: v100-bench\n" +
              "commit: 6e5b8a48...\n" +
              "state: verified\n" +
              "code: OK\n" +
              "source: input\n" +
              "evidence: uploaded",
            details: { en: "check output", zh: "check 输出" },
            transcript: "throughput 1843 tok/s\nmemory 71.2 GiB / 80 GiB",
          },
          {
            t: "artifact",
            text: { en: "oob-evidence · 349 B", zh: "oob-evidence · 349 B" },
          },
        ],
        machine: [
          {
            t: "note",
            text: {
              en: "The job could have taken three days. The gate never waits; it runs when you dispatch.",
              zh: "任务跑三天也没关系。门禁不会等，它只在你 dispatch 的时候跑。",
            },
          },
          {
            t: "checklist",
            items: [
              { en: "ran the benchmark", zh: "跑了 benchmark" },
              { en: "signed a 4 KiB transcript", zh: "签了 4 KiB 摘录" },
              { en: "packed the evidence", zh: "打了证据包" },
              { en: "uploaded from another host", zh: "从另一台机器上传" },
            ],
          },
        ],
      },
    ],
  },
  {
    id: "multi",
    label: { en: "Several jobs", zh: "多个 job" },
    blurb: {
      en: "Two machines attest one commit, each with its own receipt.",
      zh: "两台机器为同一个 commit 背书，各有一份回执。",
    },
    steps: [
      {
        nav: { en: "One commit, two machines", zh: "一个 commit，两台机器" },
        title: {
          en: "Two jobs can attest the same commit.",
          zh: "同一个 commit 可以由两个 job 背书。",
        },
        body: {
          en: "A smoke test on a V100 and a benchmark on an A100. One is required; the other is optional, because hardware is not always available. Both bind the same commit, and neither can stand in for the other.",
          zh: "V100 上的冒烟测试，A100 上的 benchmark。一个必需，一个可选，因为硬件不一定随时可用。两者绑定同一个 commit，但谁也不能代替谁。",
        },
        github: [
          { t: "event", text: "pull_request · opened" },
          {
            t: "pr",
            title: { en: "Retune the kernel", zh: "调整 kernel 参数" },
            meta: { en: "#7 · main ← kernel/tune · 3 files", zh: "#7 · main ← kernel/tune · 3 个文件" },
          },
          {
            t: "checks",
            items: [
              {
                name: "v100-smoke-verified",
                state: "missing",
                text: { en: "required · not run", zh: "必需 · 未运行" },
              },
              {
                name: "a100-bench-verified",
                state: "missing",
                text: { en: "optional · not run", zh: "可选 · 未运行" },
              },
            ],
          },
        ],
        machine: [
          {
            t: "note",
            text: {
              en: "Two operators, or one operator and two machines. The gate only knows job names.",
              zh: "两个操作员，或者一个操作员加两台机器。门禁只认 job 名字。",
            },
          },
        ],
      },
      {
        nav: { en: "One caller job each", zh: "各一个调用 job" },
        title: {
          en: "A job that calls a reusable workflow cannot carry a matrix.",
          zh: "调用可复用 workflow 的 job 不能带 matrix。",
        },
        body: {
          en: "Declare one caller per job name. Each call gets its own <code>job</code>, its own <code>check-name</code>, and its own required flag.",
          zh: "按 job 名各写一个调用。每次调用有自己的 <code>job</code>、自己的 <code>check-name</code>、自己的 required 开关。",
        },
        github: [
          {
            t: "code",
            text:
              "jobs:\n" +
              "  v100:\n" +
              "    uses: Oaklight/out-of-band/.github/workflows/verify.yml@<sha>\n" +
              "    with:\n" +
              "      pr: ${{ github.event.pull_request.number }}\n" +
              "      commit: ${{ github.event.pull_request.head.sha }}\n" +
              "      job: v100-smoke\n" +
              "      check-name: v100-smoke-verified\n" +
              "\n" +
              "  a100:\n" +
              "    uses: Oaklight/out-of-band/.github/workflows/verify.yml@<sha>\n" +
              "    with:\n" +
              "      pr: ${{ github.event.pull_request.number }}\n" +
              "      commit: ${{ github.event.pull_request.head.sha }}\n" +
              "      job: a100-bench\n" +
              "      check-name: a100-bench-verified\n" +
              "      required: false",
          },
        ],
        machine: [
          {
            t: "note",
            text: {
              en: "A missing receipt for an optional job becomes <code>not applicable</code>, with a success conclusion.",
              zh: "可选 job 没有回执时，结论是 <code>not applicable</code>，conclusion 为 success。",
            },
          },
        ],
      },
      {
        nav: { en: "Two receipts", zh: "两份回执" },
        title: {
          en: "One comment per receipt.",
          zh: "一份回执一条评论。",
        },
        body: {
          en: "The two receipts differ in <code>job</code> and in signature. Posting both is normal; the collection step sorts them out by commit and job.",
          zh: "两份回执的 <code>job</code> 不同，签名也不同。同时发出去很正常，收集步骤会按 commit 和 job 把它们分开。",
        },
        github: [
          { t: "event", text: "issue_comment · created ×2" },
          {
            t: "comment",
            author: "v100-operator",
            time: { en: "2 min ago", zh: "2 分钟前" },
            body: '<!-- receipt:v2 -->\n"job":"v100-smoke"  ...',
          },
          {
            t: "comment",
            author: "a100-operator",
            time: { en: "1 min ago", zh: "1 分钟前" },
            body: '<!-- receipt:v2 -->\n"job":"a100-bench"  ...',
          },
        ],
        machine: [
          {
            t: "term",
            title: { en: "Two machines", zh: "两台机器" },
            lines: [
              { k: "cmd", text: "$ oob sign --job v100-smoke ... --out v100.md" },
              { k: "cmd", text: "$ oob sign --job a100-bench ... --out a100.md" },
              { k: "ok", text: "each block names its own job" },
            ],
          },
        ],
      },
      {
        nav: { en: "Each reads its own", zh: "各读各的" },
        title: {
          en: "The collector filters by job before it compares.",
          zh: "收集器先按 job 过滤，再比较。",
        },
        body: {
          en: "Without the filter, two legitimate receipts for one commit look like a disagreement, and both gates fail with <code>E_MULTI_BLOCK</code>. Each call now selects only the block whose <code>job</code> it expects.",
          zh: "不过滤的话，同一 commit 上两份都合法的回执会被当成互相矛盾，两个门禁都会以 <code>E_MULTI_BLOCK</code> 失败。现在每次调用只挑 <code>job</code> 与自己相同的那一块。",
        },
        github: [
          {
            t: "checks",
            items: [
              {
                name: "v100-smoke-verified",
                state: "ok",
                text: { en: "verified", zh: "verified" },
              },
              {
                name: "a100-bench-verified",
                state: "ok",
                text: { en: "verified", zh: "verified" },
              },
            ],
          },
          {
            t: "note",
            text: {
              en: "If a receipt shows up for the commit but not for this job, the verdict is <code>E_WRONG_JOB</code> rather than a misleading pass.",
              zh: "如果 commit 有回执但没有这个 job 的，结论是 <code>E_WRONG_JOB</code>，而不是误导性的通过。",
            },
          },
        ],
        machine: [
          {
            t: "note",
            text: {
              en: "Nothing on the machines changes. The filtering happens on the runner.",
              zh: "机器上不需要改任何东西。过滤发生在 runner 上。",
            },
          },
        ],
      },
      {
        nav: { en: "All, or any", zh: "全要，还是任一" },
        title: {
          en: "Branch protection has no OR.",
          zh: "分支保护没有 OR。",
        },
        body: {
          en: "It requires every named check. If the policy is “any platform will do”, add an aggregator job and require that instead; if every platform must pass, require each check and skip the aggregator.",
          zh: "它要求每个列出的 check 都通过。如果策略是“任一平台即可”，加一个汇总 job 并要求它；如果每个平台都必须过，就逐个要求，不要汇总。",
        },
        github: [
          {
            t: "code",
            text:
              "any-platform:\n" +
              "  needs: [v100, a100]\n" +
              "  if: always()\n" +
              "  runs-on: ubuntu-latest\n" +
              "  steps:\n" +
              "    - env:\n" +
              "        V100: ${{ needs.v100.outputs.verdict }}\n" +
              "        A100: ${{ needs.a100.outputs.verdict }}\n" +
              "      run: |\n" +
              '        [ "$V100" = verified ] || [ "$A100" = verified ]',
          },
        ],
        machine: [],
      },
    ],
  },
];

const VARIANTS = [
  {
    title: { en: "Branch gate", zh: "分支门禁" },
    text: {
      en: "Attest a push when no pull request exists, and see what can and cannot be enforced.",
      zh: "没有 PR 时给推送做背书，也说明什么拦得住、什么拦不住。",
    },
    href: "https://github.com/Oaklight/out-of-band/blob/main/docs/en/scenario-branch-gate.md",
    hrefZh: "https://github.com/Oaklight/out-of-band/blob/main/docs/zh/scenario-branch-gate.md",
  },
  {
    title: { en: "Air-gapped hosts", zh: "离线机器" },
    text: {
      en: "Signing on an HPC login node with no outbound network. What to carry, and who carries it.",
      zh: "在没有外网的 HPC 登录节点上签名。带什么进去，谁把结果带出来。",
    },
    href: "https://github.com/Oaklight/out-of-band/blob/main/docs/en/offline.md",
    hrefZh: "https://github.com/Oaklight/out-of-band/blob/main/docs/zh/offline.md",
  },
  {
    title: { en: "Operations", zh: "运维" },
    text: {
      en: "Key generation, the trust root, rotation, the error-code table, and what the timeouts actually are.",
      zh: "生成密钥、信任根、轮换、错误码表，以及超时到底是什么。",
    },
    href: "https://github.com/Oaklight/out-of-band/blob/main/docs/en/operations.md",
    hrefZh: "https://github.com/Oaklight/out-of-band/blob/main/docs/zh/operations.md",
  },
  {
    title: { en: "Patch gate guide", zh: "补丁门禁指南" },
    text: {
      en: "The full caller workflow from the tour, including the API-based head resolution.",
      zh: "导览里那个调用方 workflow 的完整版本，包括通过 API 解析 head。",
    },
    href: "https://github.com/Oaklight/out-of-band/blob/main/docs/en/scenario-patch-gate.md",
    hrefZh: "https://github.com/Oaklight/out-of-band/blob/main/docs/zh/scenario-patch-gate.md",
  },
  {
    title: { en: "Benchmark run guide", zh: "Benchmark 记录指南" },
    text: {
      en: "Evidence upload, dispatch-only gates, and a section on jobs that run for days.",
      zh: "证据上传、只用 dispatch 的门禁，以及任务跑好几天时怎么办。",
    },
    href: "https://github.com/Oaklight/out-of-band/blob/main/docs/en/scenario-hardware-run.md",
    hrefZh: "https://github.com/Oaklight/out-of-band/blob/main/docs/zh/scenario-hardware-run.md",
  },
  {
    title: { en: "Multiple jobs guide", zh: "多 job 指南" },
    text: {
      en: "Naming, required versus optional, and the aggregator pattern in full.",
      zh: "命名、必需与可选，以及完整的汇总 job 写法。",
    },
    href: "https://github.com/Oaklight/out-of-band/blob/main/docs/en/scenario-multi-job.md",
    hrefZh: "https://github.com/Oaklight/out-of-band/blob/main/docs/zh/scenario-multi-job.md",
  },
];

const STATES = [
  {
    key: "verified",
    title: "verified",
    text: {
      en: "A valid signature over a passing claim. The merge can proceed.",
      zh: "签名有效，声明为通过。可以合并。",
    },
  },
  {
    key: "failed",
    title: "failed",
    text: {
      en: "A valid signature over a failing claim. Fix the job and sign again.",
      zh: "签名有效，声明为失败。修好 job，重新签。",
    },
  },
  {
    key: "unverified",
    title: "unverified",
    text: {
      en: "No usable receipt, a bad signature, or evidence that does not match. A human must look.",
      zh: "没有可用回执、签名不对，或证据对不上。需要人来判断。",
    },
  },
  {
    key: "na",
    title: "not applicable",
    text: {
      en: "No receipt was required for this change. Success, but it is not a pass.",
      zh: "这次改动本来就不需要回执。是 success，但不是通过。",
    },
  },
];

const ADOPT = [
  {
    title: { en: "Put the trust root in place", zh: "先放好信任根" },
    text: {
      en: "Add <code>.github/allowed_signers</code> on the default branch. A pull request cannot change it for itself.",
      zh: "把 <code>.github/allowed_signers</code> 放在默认分支。PR 改不动自己的信任根。",
    },
  },
  {
    title: { en: "Add a caller workflow", zh: "加上调用方 workflow" },
    text: {
      en: "Copy the closest scenario. Pin the reusable workflow by full commit SHA, not a tag, and let Dependabot bump it.",
      zh: "照最接近的场景抄一份。可复用 workflow 用完整 commit SHA 固定，不要用 tag；升级交给 Dependabot。",
    },
  },
  {
    title: { en: "Require the check", zh: "要求这个 check" },
    text: {
      en: "In branch protection or a ruleset, require the exact <code>check-name</code>. Renaming it silently changes what is protected.",
      zh: "在分支保护或 ruleset 里要求确切的 <code>check-name</code>。改名等于悄悄换掉了受保护的东西。",
    },
  },
  {
    title: { en: "Sign where the job ran", zh: "在跑任务的地方签名" },
    text: {
      en: "Install the wheel or the single-file <code>oob.pyz</code>. The command needs no network and no GitHub token.",
      zh: "装 wheel，或者用单文件 <code>oob.pyz</code>。命令不需要网络，也不需要 GitHub token。",
    },
  },
  {
    title: { en: "Deliver and read the result", zh: "交付并看结果" },
    text: {
      en: "Comment the block, or dispatch it. Then read the check, the step summary, and the durable comment.",
      zh: "把整块发成评论，或者 dispatch 提交。然后看 check、step summary 和那条长期保留的评论。",
    },
  },
];
