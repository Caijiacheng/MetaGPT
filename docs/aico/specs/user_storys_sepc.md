# 用户故事管理规范

## 文件结构
```
docs/
└── requirements/
    └── user_stories/
        └── {project_id}_user_stories_{version}.md
```

## 内容格式
```markdown
# 项目用户故事（版本: {version}）

## 标准需求 {std_req_id}
### 用户故事 {story_id}
**标题**: {title}  
**状态**: {status}  
**验收标准**:  
{acceptance_criteria}

### 用户故事 {story_id}
...

## 标准需求 {std_req_id}
...
```

## 命名规则
- 文件名：`{项目ID}_user_stories_vX.Y.Z.md`
- 版本号：`主版本.次版本.修订版本`（例：1.2.3）
- 标准需求ID：`SR-项目简写-需求分类-序号`（例：SR-ECOM-AUTH-001）
- 用户故事ID：`US-标准需求ID-序号`（例：US-SR-ECOM-AUTH-001-01）

## 版本管理规则
1. 版本格式：`主版本.次版本.修订版本`（例：1.2.3）
2. 版本递增规则：
   - 主版本：架构重大变更时递增
   - 次版本：每次需求基线更新递增
   - 修订版本：问题修复时递增
3. 文件命名：`{项目ID}_user_stories_vX.Y.Z.md`
4. 默认保留策略：
   - 保留所有主版本
   - 每个主版本保留最近3个次版本
   - 每个次版本保留最近2个修订版本
