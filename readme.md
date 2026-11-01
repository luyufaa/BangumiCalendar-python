# 基于GitHub Action建立bgm番剧Mac日历订阅服务
> 如果在使用项目中遇到问题，欢迎提issues！！！！！！！！

![image](https://github.com/HammerCloth/BangumiCalendar-python/blob/main/IMG/iShot_2022-12-07_22.08.47.png)

​通过bgm开放的api，获取用户所有在看的番剧id以及相关章节信息，生成ics文件，然后通过github中的文件链接，导入到mac自带的日历中，实现日历订阅，不需要专门的服务器来实现。

## ✨ 特性亮点

1. **流媒体平台播放时间优先对齐**：
   - 自动查询并优先使用 **巴哈姆特動畫瘋**（`gamer` / `gamer_hk`）、**Netflix**、**Crunchyroll**（CR）的上线播放时间；
   - 彻底解决日本电视台放送时间与各大流媒体平台网络上线时间不一致（或存在时差）的问题；
   - 当流媒体平台均无播放时间时，自动回退到 TV 原版首播时间。
2. **先行播放与播出时间/日期调整工具（`adjust.py`）**：
   - 支持对特定番剧进行**全剧提前/延后**（如流媒体先行播放提前 1 周，输入 `-7` 天）；
   - 支持修改每日具体**播放时间**（例如修改为 `23:30` 或 `21:00`）；
   - 支持**单集先行播放**特化配置（例如仅第 1 集提前半个月网络先行试映，后续剧集恢复正常日程）；
   - 支持指定首播完整日期时间，或强制指定放送平台；
   - 提供**交互式终端管理菜单**与**命令行一键指令**，调整后配置持久化记录于 `offsets.json`，可直接提交到 GitHub 并在 Actions 中自动生效。

---

## 项目目录

```shell
.
├── .github  
│   └── workflows
│       └── python-app.yml  // github action配置文件
├── adjust.py               // 番剧播放时间、日期及先行播放调整管理工具 (交互式 & CLI)
├── offsets.json            // 用户自定义番剧时间调整配置文件 (由 adjust.py 管理或手动编写)
├── config.json             // 本地配置文件 (可选，配置本地 USERID 等)
├── target.ics              // 生成的目标ics文件
├── requirements.txt        // github action python依赖配置文件
├── iCal.py                 // ics文件生成脚本类
├── main.py                 // GitHub Actions 执行主入口
├── reptile.py              // bgm api 与 bangumi-data 流媒体平台时间抓取
├── readme.md    
└── util.py                 // 时间计算、平台匹配与配置工具类 
```

---

## 🛠️ 番剧播放时间与先行播放调整工具 (`adjust.py`)

当某些新番存在**流媒体先行播放**（如提前 1 周上线）、**单集先行试映**（如第 1 集提前试映）或需要修改播放时分时，可以使用本程序进行调整：

### 1. 交互式菜单模式（推荐）

直接在终端运行：
```shell
python adjust.py
```
程序会自动拉取你的在看番剧列表，列出当前平台与播放时间：
- 输入序号即可对该番剧进行编辑；
- 支持调整日期偏移（提前/延后天数）、修改播出时分、设置第 1 集先行播放、切换平台等；
- 调整后即时保存到 `offsets.json`，还可以选择直接重新生成 `target.ics` 验证效果。

### 2. 命令行快捷指令模式

也支持通过命令行参数快速修改：

```shell
# 查看当前已保存的所有番剧调整
python adjust.py --list

# 将番剧 (例如 ID: 346425) 整体提前 7 天 (流媒体先行播放)
python adjust.py --id 346425 --days -7

# 将番剧播出时间修改为 23:30
python adjust.py --id 346425 --time 23:30

# 设置第 1 集单集先行播放 (指定日期和时间)
python adjust.py --id 346425 --ep 1 --ep-date 2026-09-20 --ep-time 20:00

# 强制使用巴哈姆特平台时间 (可选: gamer, netflix, crunchyroll, tv)
python adjust.py --id 346425 --platform gamer

# 清除某个番剧的调整，恢复默认
python adjust.py --id 346425 --clear

# 本地重新生成 target.ics 文件
python adjust.py --generate --user 你的BGM_ID
```

### 3. 配置同步到 GitHub Actions

当你使用 `adjust.py` 调整好番剧后，只需将生成的 `offsets.json` 提交到 GitHub 仓库：
```shell
git add offsets.json
git commit -m "更新番剧先行播放调整"
git push
```
GitHub Actions 在每日定时执行 `main.py` 时会自动读取 `offsets.json` 并应用你的个性化调整！

---

## 项目配置流程

#### 1. fork项目到你的仓库中

#### 2. 在GitHub setting 中配置 secret
![image](https://github.com/HammerCloth/BangumiCalendar-python/blob/main/IMG/iShot_2023-01-14_18.18.48.png)

```yaml
name ： USERID
value ： 你的bgm用户id
```
#### 3. 开放 github action 权限
![image](https://github.com/HammerCloth/BangumiCalendar-python/blob/main/IMG/iShot_2023-01-14_18.19.52.png)

#### 4. 在系统日历中订阅如下链接

> 你也可以直接下载下来 target.ics 文件拖到日历中，但是这样就无法自动更新了

```python
https://raw.githubusercontent.com/{你的github用户名}/BangumiCalendar-python/main/target.ics
```
