# AICO-Meta：基于多智能体的企业级软件研发框架（**整合更新版**）

## 1. AICO-Meta 的定位

- **AICO-Meta** 并不是一个需要开发的具体业务系统，而是一个 **多智能体协同** 的 **企业级软件研发流程框架**。
- 框架通过配置各关键角色（如项目经理/PM、需求分析师/BA、产品经理/PDM、架构师/EA、开发/DEV、测试/QA、DevOps/DO 等）的 **SOP（标准作业流程）**，并结合 **LLM（大模型）** 或 **MetaGPT Agent** 提升角色的决策、文档生成、代码编写等能力，以 **规范并加速** 软件开发项目。

在此框架中，团队可灵活选择：

- "**真人角色 + Agent**" 协同；
- "**全自动 Agent**" 接管部分环节；
- 或纯粹人工流程（仅参考框架定义的 SOP 及文档模板）。

---

## 2. 分阶段实现规划 (P0 / P1 / P2)

AICO-Meta 的落地一般分为三个阶段，便于在不同企业环境中循序渐进：

1. **P0：最小可用闭环**

   - 搭建基础角色（BA、PDM、EA、DEV、QA、DO、PM），实现从需求到上线的**最小闭环**。
   - 目标：当用户提出业务/技术需求后，可完成一次"需求→设计→实现→测试→部署"的端到端流程。

2. **P1：增强阶段**

   - 在 P0 的基础上，引入**项目管理能力**（项目阶段、自动化评审流程、CI/CD、回归测试等）。
   - 目标：**提升研发效率与质量**，减少人工重复操作，让各角色之间更**高度协同**。

3. **P2：高级阶段**

   - 加入更多高级功能，如可观测性、性能/安全测试、用户反馈闭环等。
   - 目标：**支撑中大型企业软件交付**的完整流程，并能持续演进。

---

## 3. 角色与关键能力：分阶段说明

| 角色名称            | 核心业务能力 (Key Abilities)                                                                                                                                                 | 分阶段实现 (P0/P1/P2)                                                                 |
|---------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| **项目经理 (PM)**   | - 端到端需求管理（`initProject`/`updateProjectTracking`）<br>- 需求基线管理（`generateBaselineVersion`/`ReviewAllRequirements`）<br>- 任务拆解与分配（`assignDesignTasks`/`assignImpTasks`）<br>- 变更闭环管理（`reviewProjectChanges`） | **P0**：<br>• 三次基线评审（需求/设计/实现）<br>• 任务状态跟踪<br>**P1**：<br>• 迭代阶段管理<br>**P2**：<br>• 多项目协同            |
| 需求分析师 (BA)      | - 业务需求解析（`parseBizRequirement`）<br>- 用户故事生成（`update4ABiz`）<br>- 业务架构维护（`update4ABiz`）<br>- 需求状态反馈                                                                 | **P0**：<br>• 需求矩阵生成<br>• 用户故事初稿<br>**P1**：<br>• 需求变更影响分析<br>**P2**：<br>• 复杂业务建模              |
| 产品经理 (PDM)      | - PRD文档编写（`writePRD`）<br>- 验收标准定义<br>- 需求设计协同（响应`design:writePRD`信号）                                                                                                         | **P0**：<br>• PRD初稿生成<br>**P1**：<br>• 多版本PRD管理<br>**P2**：<br>• 用户反馈闭环                                  |
| 架构师 (EA)        | - 技术需求解析（`parseTechRequirements`）<br>- 4A架构设计（`update4ATech`）<br>- 技术方案评审（参与`ReviewAllDesigns`）<br>- 技术需求跟踪                                                                 | **P0**：<br>• 4A架构初稿<br>• 技术需求矩阵<br>**P1**：<br>• 架构变更控制<br>**P2**：<br>• 性能/安全专项优化           |
| 开发工程师 (DEV)     | - 微服务设计（`writeServiceDesign`）<br>- 代码实现（`writeCode`）<br>- 代码评审（参与`ReviewAllImpTasks`）<br>- 缺陷修复                                                                               | **P0**：<br>• 服务设计文档<br>• 核心功能代码<br>**P1**：<br>• 单测覆盖<br>**P2**：<br>• 持续重构                    |
| 测试工程师 (QA)      | - 测试用例设计（`writeTestCase`）<br>- 测试执行（`runTestCase`）<br>- 测试报告生成（响应`imp:writeTestCase`信号）                                                                                          | **P0**：<br>• 功能测试用例<br>• 基础测试报告<br>**P1**：<br>• 自动化回归<br>**P2**：<br>• 性能/安全测试              |
| DevOps 工程师 (DO) | - 环境配置（响应`imp:writeDeploy`信号）<br>- 部署脚本生成（`writeDeploy`）<br>- 构建脚本生成（`prepareBuild`）<br>- 部署验证                                                                 | **P0**：<br>• 基础环境搭建<br>• 部署脚本初稿<br>**P1**：<br>• CI/CD流水线<br>**P2**：<br>• 可观测性体系               |



> **说明**：在 4A 架构评审后，如果需要新增中间件（Redis、MQ、ElasticSearch 等），则由 **DevOps 工程师 (DO)** 在部署环境中做相应更新（如 Docker Compose、CI/CD 配置等）。

---

## 4. 整体流程：需求跟踪 → 用户故事 → 任务拆解

典型的需求实现流程如下：

1. **原始需求跟踪**
   - PM 统一管理 ProjectTasking.xlsx 的「原始需求」Sheet，记录所有原始材料
   - BA/EA 完成解析后向 PM 反馈状态（parsed_by_ba/parsed_by_ea）
   
2. **需求管理**
   - PM 根据 BA/EA 的解析结果更新「需求管理」Sheet
   - 执行`ReviewAllRequirements()`完成需求基线

3. **用户故事管理**
   - PM 根据 PDM/BA 的拆解结果维护「用户故事管理」Sheet
   - 用户故事状态通过任务完成情况自动更新

4. **任务跟踪**
   - PM 通过`assignTasks()`发布开发/测试/部署任务
   - 各角色完成任务后向 PM 反馈状态（通过publish机制）

对大型项目，可进一步扩展到 EPIC → Feature → Story → Task → Subtask 等多层结构。

---

## 5. 详细时序与信息流 (P0 阶段更新版)

```mermaid
sequenceDiagram
    participant PM as 项目经理 (PM)
    participant BA as 需求分析师 (BA)
    participant PDM as 产品经理 (PDM)
    participant EA as 架构师 (EA)
    participant DEV as 开发工程师 (DEV)
    participant QA as 测试工程师 (QA)
    participant DO as DevOps 工程师 (DO)
    participant ENV as <环境>ENV
    participant AI as <引擎>AI


    note over PM: 【项目启动】(P0)

    PM->>PM: initProject()
    PM->>ENV: publish(project:ready)
    
   rect rgb(191, 250, 253)
   note over PM,AI: 【需求收集和分析跟踪】
    PM->>BA: publish(requirment:bizParse)，提交原始需求分析
    BA->>AI: parseBizRequirement()
    AI-->>BA: LLM输出解析结果
    BA-->>PM: publish(requirment:bizParseDone)，标准业务需求解析结束

    PM->>EA: publish(requirment:techParse)，提交原始需求分析
    EA->>AI: parseTechRequirements() 
    AI-->>EA: LLM输出解析结果
    EA-->>PM: publish(requirment:techParseDone)，需求解析结束

    PM->>PM: generateBaselineVersion()，设定基线版本version
    PM->>PM: updateProjectTacking()，更新「需求管理」状态
    
    PM->>BA: publish(requirment:bizArchAnalysis,version)，提交业务架构分析
    BA->>AI: update4ABiz()，调用AI引擎，协助更新业务架构和用户故事
    AI-->>BA: 输出业务架构和用户故事
    BA-->>PM: publish(requirment:bizArchAnalysisDone)，需求解析结束
  
    PM->>EA: publish(requirment:techArchAnalysis,version)，提交技术架构分析
    EA->>AI: update4ATech()，调用AI引擎，协助更新技术架构（需要结合业务架构）
    AI-->>EA: 输出4A架构中的应用架构、数据架构、技术架构
    EA-->>PM: publish(requirment:techArchAnalysisDone)，需求解析结束
    PM->>PM: updateProjectTacking()，更新「需求管理」状态

    PM->>AI: ReviewAllRequirements()，人工复核修正 + 文档AI一致性检查
    AI-->>PM: 输出一致性结果
    PM->>PM: updateProjectTacking()，更新「需求管理」状态
    note over PM: 需求收集&分析结束，形成需求文档基线,version
    end
    rect rgb(176, 255, 208)
    note over PM,AI: 【需求设计跟踪】
    PM->>AI: assignDesignTasks()，调用AI引擎，拆解需求设计任务
    AI-->>PM: 输出迭代计划
    PM->>PM: updateProjectTacking()，更新「任务管理」状态
    PM->>PDM: publish(design:writePRD)

    PDM->>AI: writePRD()，调用AI引擎，协助生成PRD初稿
    AI-->>PDM: 输出PRD
    PDM-->>PM: publish(design:writePRDDone,version)
    PM->>PM: updateProjectTacking()，更新「任务管理」状态

    PM->>DEV: publish(design:writeServiceDesign)
    DEV->>AI: writeServiceDesign()，调用AI引擎，协助生成微服务设计文档初稿
    AI-->>DEV: 输出微服务设计文档初稿
    DEV-->>PM: publish(design:writeServiceDesignDone,version)
    PM->>PM: updateProjectTacking()，更新「任务管理」状态

    PM->>QA: publish(design:writeTestCase)
    QA->>AI: writeTestCase()，调用AI引擎，协助生成测试用例初稿
    AI-->>QA: 输出测试用例初稿
    QA-->>PM: publish(design:writeTestCaseDone)
    PM->>PM: updateProjectTacking()，更新「任务管理」状态

    PM->>AI: ReviewAllDesigns()，人工复核修正 + 文档AI一致性检查
    AI-->>PM: 输出一致性结果
    PM->>PM: updateProjectTacking()，更新「任务管理」状态
    note over PM: 需求设计结束，形成设计文档基线,version
    end
    rect rgb(231, 235, 243)
    note over PM,AI: 【需求实现跟踪】

    PM->>AI: assignImpTasks()，调用AI引擎，协助拆解需求实现任务
    AI-->>PM: 输出任务列表

    PM->>DO: publish(imp:writeDeploy,version)
    DO->>AI: writeDeploy()，调用AI引擎，协助生成环境部署脚本初稿
    AI-->>DO: 输出部署脚本初稿
    DO-->>PM: publish(imp:writeDeployDone,version)
    PM->>PM: updateProjectTacking()，更新「任务管理」状态

    PM->>DEV: publish(imp:writeCode,version)
    DEV->>AI: writeCode()，调用AI引擎，协助生成代码初稿
    AI-->>DEV: 输出代码
    DEV-->>PM: publish(imp:writeCodeDone,version)
    PM->>PM: updateProjectTacking()，更新「任务管理」状态
    
    PM->>QA: publish(imp:writeTestCase,version)
    QA->>AI: writeTestCase()，调用AI引擎，协助生成测试用例初稿
    AI-->>QA: 输出测试用例初稿
    QA-->>PM: publish(imp:writeTestCaseDone,version)
    PM->>PM: updateProjectTacking()，更新「任务管理」状态

    PM->>AI: ReviewAllImpTasks()，人工复核修正 + 代码AI一致性检查
    AI-->>PM: 输出一致性结果
    PM->>PM: updateProjectTacking()，更新「任务管理」状态
    note over PM: 需求实现结束，形成项目代码基线,version
    
   end
   rect rgb(250, 224, 252)
    note over PM,AI: 需求迭代结束
    PM->>AI: reviewProjectChanges(version-1, version)，总结分析项目版本之间的change log
    AI-->>PM: 输出change log，输出一致性分析报告
    PM->>PM: updateProjectTacking()，更新「需求管理」状态
    PM->>ENV: publish(project:IterDone,version)
    note over PM: 需求Flow结束，人工提交commit代码
    end
    
```

**流程阶段说明**：

1. **需求收集阶段（蓝色）**
   - **核心动作**：PM初始化项目 → BA/EA分别收集业务/技术需求 → AI辅助生成需求矩阵 → 人工复核确认
   - **关键产出**：业务需求矩阵、技术需求矩阵、4A架构初稿
   - **质量关卡**：PM执行`ReviewAllRequirements()`进行需求基线确认

2. **需求设计阶段（绿色）**
   - **核心动作**：AI生成迭代计划 → PDM生成PRD → DEV生成微服务设计 → QA生成测试用例 → 人工复核设计
   - **关键产出**：PRD文档、微服务设计文档、测试用例文档
   - **质量关卡**：PM执行`ReviewAllDesigns()`进行设计基线确认

3. **需求实现阶段（灰色）**
   - **核心动作**：任务拆解 → DO生成构建脚本 → DEV生成代码 → QA生成测试 → DO生成部署脚本 → 人工复核实现
   - **关键产出**：可运行代码、测试报告、部署脚本
   - **质量关卡**：PM执行`ReviewAllTasks()`进行代码基线确认

4. **迭代收尾阶段（紫色）**
   - **核心动作**：AI生成变更日志 → 文档代码一致性检查 → 人工确认上线
   - **关键产出**：变更日志、一致性分析报告

---

## 6. 各角色 Action 定义 & Observe/Publish

### 6.1 需求收集阶段角色

#### 项目经理 (PM)
- **Action**: 
  - `initProject()`：初始化项目环境
  - `generateBaselineVersion()`：生成需求基线版本
  - `updateProjectTracking(data)`：更新项目跟踪表
- **Publish**: 
  - `project:ready` 项目就绪信号
  - `requirment:bizParse` 触发业务需求分析
  - `requirment:techParse` 触发技术需求分析
  - `requirment:bizArchAnalysis` 触发业务架构分析
  - `requirment:techArchAnalysis` 触发技术架构分析

#### 需求分析师 (BA)
- **Observe**: `requirment:bizParse`, `requirment:bizArchAnalysis`
- **Action**:
  - `parseBizRequirement()`：解析原始业务需求
  - `update4ABiz()`：更新业务架构和用户故事
- **Publish**: 
  - `requirment:bizParseDone` 业务需求解析完成
  - `requirment:bizArchAnalysisDone` 业务架构分析完成

#### 架构师 (EA)
- **Observe**: `requirment:techParse`, `requirment:techArchAnalysis`
- **Action**:
  - `parseTechRequirements()`：解析技术需求
  - `update4ATech()`：更新技术架构
- **Publish**: 
  - `requirment:techParseDone` 技术需求解析完成
  - `requirment:techArchAnalysisDone` 技术架构分析完成

### 6.2 需求设计阶段角色

#### 项目经理 (PM)
- **Action**: 
  - `assignDesignTasks()`：分配设计任务
  - `ReviewAllDesigns()`：设计文档评审
- **Publish**:
  - `design:writePRD` 触发PRD编写
  - `design:writeServiceDesign` 触发服务设计
  - `design:writeTestCase` 触发测试用例设计

#### 产品经理 (PDM)
- **Observe**: `design:writePRD`
- **Action**: `writePRD()`：生成产品需求文档
- **Publish**: `design:writePRDDone` PRD文档完成

#### 开发工程师 (DEV)
- **Observe**: `design:writeServiceDesign`
- **Action**: `writeServiceDesign()`：生成微服务设计文档
- **Publish**: `design:writeServiceDesignDone` 服务设计完成

#### 测试工程师 (QA)
- **Observe**: `design:writeTestCase`
- **Action**: `writeTestCase()`：生成测试用例初稿
- **Publish**: `design:writeTestCaseDone` 测试用例设计完成

### 6.3 需求实现阶段角色

#### 项目经理 (PM)
- **Action**: 
  - `assignImpTasks()`：分配实现任务
  - `ReviewAllImpTasks()`：实现成果评审
- **Publish**: 
  - `imp:writeDeploy` 触发部署脚本编写
  - `imp:writeCode` 触发代码开发
  - `imp:writeTestCase` 触发测试用例执行

#### DevOps工程师 (DO)
- **Observe**: `imp:writeDeploy`
- **Action**: `writeDeploy()`：生成部署脚本
- **Publish**: `imp:writeDeployDone` 部署脚本完成

#### 开发工程师 (DEV)
- **Observe**: `imp:writeCode`
- **Action**: `writeCode()`：生成功能代码
- **Publish**: `imp:writeCodeDone` 代码开发完成

#### 测试工程师 (QA)
- **Observe**: `imp:writeTestCase`
- **Action**: 
  - `runTestCase()`：执行测试用例
  - `generateTestReport()`：生成测试报告
- **Publish**: `imp:writeTestCaseDone` 测试执行完成

### 6.4 迭代收尾阶段角色

#### 项目经理 (PM)
- **Action**: `reviewProjectChanges()`：分析版本变更
- **Publish**: `project:IterDone` 迭代完成信号
- **Observe**: 所有实现阶段的完成信号

---

## 7. P0 阶段 SOP 示范（流程细化）

1. **需求收集阶段**
   - PM：执行`initProject()` → 发布`{project:ready}`
   - BA：接收`{requirement:bizParse}` → 发布`{requirement:bizParseDone}`
   - EA：接收`{requirement:techParse}` → 发布`{requirement:techParseDone}`
   - PM：执行`trackRequirement()`更新跟踪表

2. **需求设计阶段**
   - PM：发布`{design:writePRD}`/`{design:writeServiceDesign}`/`{design:writeTestCase}`
   - PDM/DEV/QA：完成设计后发布完成信号（如`{design:writePRDDone}`）
   - PM：执行`updateProjectTracking()`更新「需求管理」状态

3. **需求实现阶段**
   - PM：执行`assignImpTasks()`发布`{tasks:build}`,`{tasks:Dev}`,`{tasks:deploy}`
   - DO/DEV/QA：并行处理构建/编码/测试 → 发布实现产物
   - PM：执行`ReviewAllTasks()`完成代码基线

4. **迭代收尾**
   - PM：调用`commitChanges()`生成变更日志
   - AI：自动执行文档代码一致性检查
   - PM：人工确认后发布`{上线完成}`

---



