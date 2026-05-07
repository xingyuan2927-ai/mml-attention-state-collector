# Attention State Collector 数据采集说明

一定要认真阅读下面的所有指示，严格按照要求来。有任何不懂的地方请及时问我，因为一旦有一点小错误，就会造成整个数据集不可用。请按下面规则来，不要改命名格式。

GitHub 链接：  
<https://github.com/xingyuan2927-ai/mml-attention-state-collector>

---

## 1. 环境要求

❗请使用 **Python 3.12**

在 VS Code 右下角选择 Python 环境，必须选择之前 MML 用过的 **Python 3.12** 环境。

如果右下角不是 Python 3.12，请点击它并切换到 Python 3.12。注意：两个地方都要切换到 3.12，不要只切换一个。

每个人都需要在自己的电脑上重新安装依赖包，不是下载 GitHub 文件后就能直接运行。

### ❗步骤如下

在 VS Code 里打开 **Terminal / 终端**，确认路径在：

```text
mml-attention-state-collector\attention_state_collector
```

然后输入：

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

这一步是在下载项目运行需要的依赖包，比如 OpenCV、MediaPipe、pynput、pandas 等。

### ❗如何运行

安装完成后，打开：

```text
main.py
```

然后点击 VS Code 右上角的 **Run / 三角形运行按钮** 启动程序。

如果成功，会弹出一个窗口，标题是：

```text
Attention State Collector
```

第一次正式采集前，请先录一个 **30 秒 test**，确认：

```text
Status 出现 camera active | face detected
Saved windows 会增加
CSV 文件里有新增数据
```

测试完记得把测试的数据删掉。

---

## 2. 每个人采多少数据

每个人一共采 **15 个 session**：

```text
5 个 focused
5 个 distracted
5 个 fatigued
```

每个 session 录 **5–6 分钟**。

系统每 10 秒保存一行，所以每个 session 最好有：

```text
30–36 saved windows
```

如果少于 30 个 saved windows，说明这段太短，最好重新录。

---

## 3. participant_id 命名

每个人固定一个编号，不要中途改：

```text
P001
P002
P003
```

其中：

```text
P001 = 我
P002 = 开心
P003 = 番茄
```

比如你被分到 P002，那所有 session 的 participant_id 都填：

```text
P002
```

不要填真实姓名。

---

## 4. session_id 命名格式

统一用这个格式：

```text
P00X_label_编号
```

例如 P001：

```text
P001_focused_01
P001_focused_02
P001_focused_03
P001_focused_04
P001_focused_05

P001_distracted_01
P001_distracted_02
P001_distracted_03
P001_distracted_04
P001_distracted_05

P001_fatigued_01
P001_fatigued_02
P001_fatigued_03
P001_fatigued_04
P001_fatigued_05
```

如果你是 P002，就改成：

```text
P002_focused_01
P002_distracted_01
P002_fatigued_01
```

---

## 5. 三个 label 怎么录

### focused / 专注

做一个连续任务，比如阅读、写作、代码、整理资料。  
尽量不要切页面，不要看手机。

建议填写：

```text
label: focused
task_type: reading / writing / coding / research
pre_task_duration_min: 实际已经工作时间，最好 0–20
self_report_focus_score: 4 或 5
self_report_distraction_score: 1 或 2
self_report_fatigue_score: 1 或 2
condition_note: normal focused task
```

### distracted / 分心

故意让自己分心，比如切页面、看通知、看无关网页、短暂停顿、注意力跳走。

建议填写：

```text
label: distracted
task_type: browsing / reading / coding / research
pre_task_duration_min: 实际已经工作时间，最好 0–20
self_report_focus_score: 1 或 2
self_report_distraction_score: 4 或 5
self_report_fatigue_score: 1 或 2
condition_note: task switching / intentional interruptions
```

### fatigued / 疲劳

这个不要刚坐下就录。  
请在连续学习/工作 **至少 30 分钟后** 再录，最好是 40–60 分钟后。

建议填写：

```text
label: fatigued
task_type: reading / writing / coding / research
pre_task_duration_min: 30–60，填实际分钟数
self_report_focus_score: 1 或 2
self_report_distraction_score: 2 或 3
self_report_fatigue_score: 4 或 5
condition_note: after long study/work
```

如果你其实不累，fatigue score 只有 1 或 2，就不要硬录成 fatigued。

---

## 6. 采集顺序

focused 和 distracted 尽量交替录，不要永远先 focused 后 distracted。

可以这样：

```text
focused_01
distracted_01
focused_02
distracted_02
focused_03
focused_04
fatigued_01
distracted_03
...
```

fatigued 不需要一次性全部录完。  
只要每次是在连续学习/工作 30–60 分钟后录就可以。

比如今天学习 45 分钟后录：

```text
P001_fatigued_01
```

明天学习 40 分钟后再录：

```text
P001_fatigued_02
```

---

## 7. 每次录制时检查

点击 **Start Recording** 后，确认状态里出现：

```text
camera active | face detected
```

录制过程中，Saved windows 会每 10 秒增加一次。

每段结束时应该大约是：

```text
Saved windows: 30–36
```

也就是看 CSV 文件里面有没有增加合适的行数：每 10 秒增加一行，5 分钟大概有 30 行。

还需要检查：

```text
CSV 是否新增了对应 session_id
face_detected_ratio 是否大部分不是 0
```

如果 `face_detected_ratio` 长期接近 0，说明摄像头没拍到脸，那段数据基本废了。

如果一直显示 no face detected，要调整摄像头、光线和坐姿，否则那段数据可能不能用。

---

## 8. 数据文件怎么发

录完后，把这个文件发给我：

```text
attention_state_collector/data/attention_state_dataset.csv
```

发之前请复制出来并重命名，格式是：

```text
P00X_collector_raw.csv
```

例如：

```text
P001_collector_raw.csv
P002_collector_raw.csv
P003_collector_raw.csv
```

注意：因为所有测试数据最后都汇总在一个 CSV 文件里，一定要保证数据准确性。  
如果有错误的数据，比如专注的时候不小心录成了分心，一定要把那几行错误数据删掉。  
平时录制的时候多备份，以防不小心污染整个数据文件，到时候全部不能用。

不要把 CSV 上传到 GitHub。  
只把 CSV 私下发给我。
