# 测试 @metagpt/ext/aico/roles/project_manager.py
## project_manager代码目标覆盖率：80%以上
## 测试的目录和数据放在 @tests/data/aico/roles/project_manager
## 测试要求：
### 模拟外部调用的场景，测试完整的项目管理流程workflow，可以调用到所有的函数(暂时只到第一阶段ReviewRequirement，后面阶段暂时不测试，用TODO代替）
### 针对每个函数，提供单元测试，确保函数功能正确，并且有异常测试的场景，覆盖到80%以上的代码

# 运行测试
# pytest tests/metagpt/ext/aico/roles/test_project_manager.py -v --cov=metagpt --cov-report=term

# coverage report --include="metagpt/ext/aico/**/project_manager.py"