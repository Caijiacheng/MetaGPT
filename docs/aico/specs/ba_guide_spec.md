# AICO 业务分析规范 (BA Guide)

## 1. 概述

本规范定义了业务分析师 (BA) 在 AICO 框架中的主要职责、工作流程和产出物标准。

## 2. 主要职责

*   **需求解析**: 将原始业务需求转化为标准化的需求描述。
*   **业务建模**: 构建业务流程图、用户故事等模型。
*   **需求沟通**: 与项目经理 (PM)、产品经理 (PDM) 和架构师 (EA) 沟通需求。

## 3. 工作流程

1.  **接收需求**: 从 PM 处接收原始需求。
2.  **需求分析**:
    *   理解业务背景和目标。
    *   识别关键业务流程。
    *   定义用户角色和用户故事。
3.  **文档编写**:
    *   编写需求分析报告 (包含业务流程图和用户故事)。
    *   更新业务架构文档 (如果需要)。
4.  **需求确认**: 与 PM、PDM 和 EA 确认需求分析结果。

## 4. 产出物标准

### 4.1 需求分析报告

*   **文件路径**: `docs/requirements/analyzed/v{版本号}/req-{需求ID}/biz_analysis.md`
*   **内容**:
    *   **需求概述**: 简要描述需求背景和目标。
    *   **业务流程图**: 使用 Mermaid 语法绘制业务流程图 (graph TD)。
    *   **用户故事**:
        *   格式: As a \[user role], I want \[goal/desire] so that \[benefit].
        *   包含验收标准。
    *   **需求优先级**: (可选) 根据业务价值和紧急程度划分需求优先级。

### 4.2 业务架构文档 (可选)

*   **文件路径**: `docs/ea/biz_arch/v{版本号}/biz_arch.md`
*   **内容**:
    *   业务能力模型。
    *   业务流程图 (更全面的视图)。
    *   组织结构和角色职责 (如果需要)。

## 5. 工具

*   **Mermaid**: 用于绘制流程图和 ER 图。
*   **Markdown**: 用于编写文档。
*   **ProjectTracking.xlsx**: 用于跟踪需求状态。

## 6. 版本控制
* 需求分析报告：每个需求独立更新版本
* 业务架构文档：次版本变更时更新
