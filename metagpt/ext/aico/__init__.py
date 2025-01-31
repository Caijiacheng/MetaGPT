"""
AICO-Meta: 基于多智能体的企业级软件研发框架
"""

from metagpt.environment.aico.aico_env import AICOEnvironment
from .roles.project_manager import ProjectManager
from .roles.business_analyst import BusinessAnalyst
from .roles.product_manager import ProductManager
from .roles.architect import EnterpriseArchitect
from .roles.developer import Developer
from .roles.tester import Tester
from .roles.devops import DevOpsEngineer

__all__ = [
    'AICOEnvironment',
    'ProjectManager',
    'BusinessAnalyst', 
    'ProductManager',
    'EnterpriseArchitect',
    'Developer',
    'Tester',
    'DevOpsEngineer'
] 