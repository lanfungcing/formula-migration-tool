# formula-migration-tool

## 项目介绍

经过抽样调查，我们发现，在上游的 [Homebrew/homebrew-core](https://github.com/homebrew/homebrew-core) 仓库中，大部分 formula 可以不经任何修改直接在 Harmonybrew 上构建成功并测试通过。这些 formula 可以从上游原封不动地搬运到我们的下游仓库中。

这个搬运 formula 的过程，是一套机械化的动作，我们可以很轻易地将这一套动作封装成自动化工具，本项目就是这个自动化工具。

我们基于 GitHub Actions 实现 formula 的构建验证和自动化搬运过程，用 GitHub 提供的免费构建机进行构建和上传，用户无需准备本地环境。

## 使用方法

**1\. Fork 仓库**

需要 fork 的仓库有两个
1. [Harmonybrew/formula-migration-tool](https://github.com/Harmonybrew/formula-migration-tool)：在 GitHub 平台操作。
2. [Harmonybrew/homebrew-core](https://gitcode.com/Harmonybrew/homebrew-core)：在 GitCode 平台操作。

确保已经把它们都 fork，生成个人仓。

**2\. 启用 Actions**

* 在 GitHub 网页上访问自己 fork 的 formula-migration-tool 仓库，找到仓库顶部的 `Actions` 页签，点开页签。
* 点击里面的 `Enable Actions on this repository` 按钮，启用工作流。

**3\. 录入相关变量和密钥**

* 在 GitHub 网页上访问自己 fork 的 formula-migration-tool 仓库，找到仓库顶部的 `Settings` 页签，点开页签。
* 找到 `Secrets and variables` 菜单，进入里面的 `Actions` 子菜单。
* 在 `Secrets` 页签中，找到 `Repository secrets`，往里面录入一个密钥。密钥名字为 `GITCODE_TOKEN`，密钥内容需要去 GitCode 平台的 [访问令牌](https://gitcode.com/setting/token-classic) 界面生成，权限范围需要包含 PR 的读写权限。
* 在 `Variables` 页签中，找到 `Repository variables`，往里面录入两个变量。名字分别为 `GITCODE_USER` 和 `GITCODE_EMAIL`，内容是你的 GitCode 用户名和邮箱。

**4\. 分析 formula 依赖情况和录入情况**

* 在 GitHub 网页上访问自己 fork 的 formula-migration-tool 仓库，找到仓库顶部的 `Actions` 页签，点开页签。
* 点开 `check-migration` 工作流，点击右上角 `Run workflow`，输入你要分析的 formula 名字。
* 等待工作流运行结束后，你可以在日志中看到分析结果。日志会详细打印这个 formula 的依赖信息，并提示哪些包已经搬运过了、哪些包还没有搬运过。

如果你要的 formula 或者它的级联依赖还没有被搬运，你需要执行下面的步骤 5，对它们进行搬运。

**5\. 自动化搬运 formula**

* 在 GitHub 网页上访问自己 fork 的 formula-migration-tool 仓库，找到仓库顶部的 `Actions` 页签，点开页签。
* 点开 `auto-migrate` 工作流，点击右上角 `Run workflow`，输入你要搬运的 formula 名字。注意，这个工作流每次只会搬运一个 formula，不具备自动处理级联依赖的功能。
* 等待工作流运行结束或报错退出
  * 如果工作流没有报错，你可以在工作流的日志中看到有 PR 链接打印出来，在 [Harmonybrew/homebrew-core](https://gitcode.com/Harmonybrew/homebrew-core) 仓库中也能看到自动生成的 PR，等待维护者评审即可。
  * 如果工作流报错了，这意味着这个包需要人工处理（改 formula 或者打补丁），本工具无法处理。

如果你有多个 formula 需要搬运，且他们之间没有级联依赖关系，那你可以同时触发多个任务，让它们并行跑。GitHub 给免费用户提供的并发任务限额是 20个，你最多可以同时构建 20 个 formula。
