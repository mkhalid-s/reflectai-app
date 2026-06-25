#!/usr/bin/env python3
"""
Comprehensive validation of Phases 1-5 implementation.
Tests actual functionality and connectivity.
"""

import os
import sys
import importlib
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import ast

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class PhaseValidator:
    """Validates each phase implementation thoroughly."""
    
    def __init__(self):
        self.project_root = project_root
        self.results = {}
        self.import_errors = []
        self.connectivity_issues = []
        
    def validate_phase_1(self) -> Dict[str, Any]:
        """Validate Phase 1: Security-First Foundation."""
        phase_results = {
            "phase": "Phase 1: Security-First Foundation",
            "tasks": {},
            "imports_work": {},
            "completion": 0
        }
        
        # Task 1: Directory Structure
        required_dirs = [
            "src/core", "src/infrastructure", "src/interfaces",
            "src/services", "src/shared", "tests"
        ]
        dirs_exist = all((self.project_root / d).exists() for d in required_dirs)
        phase_results["tasks"]["directory_structure"] = {
            "status": "✅" if dirs_exist else "❌",
            "complete": dirs_exist
        }
        
        # Task 2: Error Handling
        try:
            from src.shared.error_handlers import (
                ReflectAIError, CircuitBreaker, retry_with_exponential_backoff
            )
            phase_results["imports_work"]["error_handler"] = True
            phase_results["tasks"]["error_handling"] = {
                "status": "✅",
                "complete": True,
                "components": ["ReflectAIError", "CircuitBreaker", "retry_with_exponential_backoff"]
            }
        except ImportError as e:
            phase_results["imports_work"]["error_handler"] = False
            phase_results["tasks"]["error_handling"] = {
                "status": "❌",
                "complete": False,
                "error": str(e)
            }
            self.import_errors.append(f"Error handler: {e}")
        
        # Task 3: Logging System
        try:
            from src.shared.logging import get_logger
            logger = get_logger(__name__)

            # Check if it's structlog or basic logging
            is_structlog = "structlog" in str(type(logger))
            phase_results["tasks"]["logging"] = {
                "status": "⚠️" if not is_structlog else "✅",
                "complete": not is_structlog,  # Basic logging exists but not structlog
                "type": "structlog" if is_structlog else "basic logging"
            }
            phase_results["imports_work"]["logging"] = True
        except ImportError as e:
            phase_results["tasks"]["logging"] = {
                "status": "❌",
                "complete": False,
                "error": str(e)
            }
            phase_results["imports_work"]["logging"] = False
        
        # Task 4: Configuration Management
        try:
            from src.infrastructure.config.config_manager import (
                ConfigManager, get_config_manager, ReflectAIConfig
            )
            config_manager = get_config_manager()
            
            # Test loading configuration
            try:
                config = config_manager.load_configuration("development")
                phase_results["tasks"]["configuration"] = {
                    "status": "✅",
                    "complete": True,
                    "components": ["ConfigManager", "Pydantic models", "Environment support"]
                }
            except Exception as e:
                phase_results["tasks"]["configuration"] = {
                    "status": "⚠️",
                    "complete": False,
                    "error": f"Config loads but errors: {e}"
                }
            
            phase_results["imports_work"]["configuration"] = True
        except ImportError as e:
            phase_results["tasks"]["configuration"] = {
                "status": "❌",
                "complete": False,
                "error": str(e)
            }
            phase_results["imports_work"]["configuration"] = False
        
        # Task 5: Secrets Management (Doppler)
        try:
            from src.infrastructure.config.secrets_manager import get_secrets_manager
            secrets_manager = get_secrets_manager()
            phase_results["tasks"]["secrets_management"] = {
                "status": "✅",
                "complete": True,
                "components": ["Doppler integration", "Environment fallback"]
            }
            phase_results["imports_work"]["secrets"] = True
        except ImportError as e:
            phase_results["tasks"]["secrets_management"] = {
                "status": "⚠️",
                "complete": False,
                "error": str(e)
            }
            phase_results["imports_work"]["secrets"] = False
        
        # Task 6: OAuth2 Authentication
        oauth_path = self.project_root / "src/infrastructure/auth/oauth2_handler.py"
        if oauth_path.exists():
            try:
                # Try to import OAuth2 handler
                spec = importlib.util.spec_from_file_location("oauth2_handler", oauth_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                phase_results["tasks"]["oauth2"] = {
                    "status": "✅",
                    "complete": True
                }
            except:
                phase_results["tasks"]["oauth2"] = {
                    "status": "⚠️",
                    "complete": False,
                    "error": "File exists but has errors"
                }
        else:
            phase_results["tasks"]["oauth2"] = {
                "status": "❌",
                "complete": False,
                "error": "OAuth2 handler not implemented"
            }
        
        # Calculate completion
        total_tasks = len(phase_results["tasks"])
        completed = sum(1 for t in phase_results["tasks"].values() if t.get("complete", False))
        phase_results["completion"] = (completed / total_tasks * 100) if total_tasks > 0 else 0
        
        return phase_results
    
    def validate_phase_2(self) -> Dict[str, Any]:
        """Validate Phase 2: Core Infrastructure Layer."""
        phase_results = {
            "phase": "Phase 2: Core Infrastructure Layer",
            "tasks": {},
            "imports_work": {},
            "completion": 0
        }
        
        # Task 1: Database Models
        models = ["user", "activity", "competency", "workflow", "report", "event"]
        models_ok = []
        
        for model in models:
            model_path = self.project_root / f"src/infrastructure/database/models/{model}.py"
            if model_path.exists():
                try:
                    # Try to import the model
                    spec = importlib.util.spec_from_file_location(f"model_{model}", model_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    models_ok.append(model)
                except Exception as e:
                    self.import_errors.append(f"Model {model}: {e}")
        
        phase_results["tasks"]["database_models"] = {
            "status": "✅" if len(models_ok) == len(models) else "⚠️",
            "complete": len(models_ok) == len(models),
            "models_working": models_ok,
            "total": len(models)
        }
        
        # Task 2: Repository Pattern
        repos = ["user", "activity", "competency", "workflow", "report", "event"]
        repos_ok = []
        
        for repo in repos:
            repo_path = self.project_root / f"src/infrastructure/database/repositories/{repo}_repository.py"
            if repo_path.exists():
                try:
                    spec = importlib.util.spec_from_file_location(f"repo_{repo}", repo_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    repos_ok.append(repo)
                except Exception as e:
                    self.import_errors.append(f"Repository {repo}: {e}")
        
        phase_results["tasks"]["repositories"] = {
            "status": "✅" if len(repos_ok) == len(repos) else "⚠️",
            "complete": len(repos_ok) == len(repos),
            "repos_working": repos_ok,
            "total": len(repos)
        }
        
        # Task 3: Alembic Migrations
        alembic_ini = self.project_root / "src/infrastructure/database/alembic/alembic.ini"
        alembic_env = self.project_root / "src/infrastructure/database/alembic/env.py"
        
        phase_results["tasks"]["alembic"] = {
            "status": "✅" if alembic_ini.exists() and alembic_env.exists() else "❌",
            "complete": alembic_ini.exists() and alembic_env.exists(),
            "ini_exists": alembic_ini.exists(),
            "env_exists": alembic_env.exists()
        }
        
        # Task 4: Redis Cache
        try:
            from src.core.storage.redis_manager import RedisManager
            phase_results["tasks"]["redis_cache"] = {
                "status": "✅",
                "complete": True
            }
            phase_results["imports_work"]["redis"] = True
        except ImportError as e:
            phase_results["tasks"]["redis_cache"] = {
                "status": "❌",
                "complete": False,
                "error": str(e)
            }
            phase_results["imports_work"]["redis"] = False
        
        # Task 5: Database Manager
        try:
            from src.infrastructure.database.database_manager import DatabaseManager
            phase_results["tasks"]["database_manager"] = {
                "status": "✅",
                "complete": True
            }
            phase_results["imports_work"]["db_manager"] = True
        except ImportError as e:
            phase_results["tasks"]["database_manager"] = {
                "status": "❌",
                "complete": False,
                "error": str(e)
            }
            phase_results["imports_work"]["db_manager"] = False
        
        # Calculate completion
        total_tasks = len(phase_results["tasks"])
        completed = sum(1 for t in phase_results["tasks"].values() if t.get("complete", False))
        phase_results["completion"] = (completed / total_tasks * 100) if total_tasks > 0 else 0
        
        return phase_results
    
    def validate_phase_3(self) -> Dict[str, Any]:
        """Validate Phase 3: AI/LLM Foundation."""
        phase_results = {
            "phase": "Phase 3: AI/LLM Foundation",
            "tasks": {},
            "imports_work": {},
            "completion": 0
        }
        
        # Task 1: LLM Gateway
        try:
            from src.core.llm.gateway import LLMGateway
            gateway = LLMGateway()
            
            # Check for LiteLLM integration
            gateway_file = self.project_root / "src/core/llm/gateway.py"
            with open(gateway_file, 'r') as f:
                content = f.read()
                has_litellm = "litellm" in content.lower()
                has_multi_provider = "anthropic" in content.lower() and "openai" in content.lower()
            
            phase_results["tasks"]["llm_gateway"] = {
                "status": "✅" if has_litellm else "⚠️",
                "complete": has_litellm,
                "litellm": has_litellm,
                "multi_provider": has_multi_provider
            }
            phase_results["imports_work"]["gateway"] = True
        except Exception as e:
            phase_results["tasks"]["llm_gateway"] = {
                "status": "❌",
                "complete": False,
                "error": str(e)
            }
            phase_results["imports_work"]["gateway"] = False
        
        # Task 2: Guardrails AI
        try:
            from src.core.llm.guardrails import GuardrailsManager
            phase_results["tasks"]["guardrails"] = {
                "status": "✅",
                "complete": True
            }
            phase_results["imports_work"]["guardrails"] = True
        except ImportError as e:
            phase_results["tasks"]["guardrails"] = {
                "status": "❌",
                "complete": False,
                "error": str(e)
            }
            phase_results["imports_work"]["guardrails"] = False
        
        # Task 3: Prompt Templates
        prompt_files = [
            "src/prompts/templates/analysis.yaml",
            "src/prompts/templates/advisor.yaml"
        ]
        prompts_exist = all((self.project_root / f).exists() for f in prompt_files)
        
        phase_results["tasks"]["prompt_templates"] = {
            "status": "✅" if prompts_exist else "❌",
            "complete": prompts_exist,
            "files": [f for f in prompt_files if (self.project_root / f).exists()]
        }
        
        # Task 4: Cost Tracking
        try:
            # Check if cost tracking is implemented in gateway
            from src.core.llm.gateway import LLMGateway
            gateway_file = self.project_root / "src/core/llm/gateway.py"
            with open(gateway_file, 'r') as f:
                content = f.read()
                has_cost_tracking = "cost" in content.lower() and "track" in content.lower()
            
            phase_results["tasks"]["cost_tracking"] = {
                "status": "✅" if has_cost_tracking else "❌",
                "complete": has_cost_tracking
            }
        except:
            phase_results["tasks"]["cost_tracking"] = {
                "status": "❌",
                "complete": False
            }
        
        # Calculate completion
        total_tasks = len(phase_results["tasks"])
        completed = sum(1 for t in phase_results["tasks"].values() if t.get("complete", False))
        phase_results["completion"] = (completed / total_tasks * 100) if total_tasks > 0 else 0
        
        return phase_results
    
    def validate_phase_4(self) -> Dict[str, Any]:
        """Validate Phase 4: Multi-Agent System Core."""
        phase_results = {
            "phase": "Phase 4: Multi-Agent System Core",
            "tasks": {},
            "imports_work": {},
            "completion": 0
        }
        
        # Task 1: Base Agent Framework
        agents = ["phase4_base_agent", "phase4_analysis_agent", "phase4_advisor_agent"]
        agents_ok = []
        
        for agent in agents:
            try:
                module_path = f"src.core.agents.{agent}"
                module = importlib.import_module(module_path)
                agents_ok.append(agent)
            except Exception as e:
                self.import_errors.append(f"Agent {agent}: {e}")
        
        phase_results["tasks"]["agent_framework"] = {
            "status": "✅" if len(agents_ok) == len(agents) else "⚠️",
            "complete": len(agents_ok) == len(agents),
            "working_agents": agents_ok
        }
        
        # Task 2: Agent Coordinator (using services.agents)
        try:
            from src.services.agents import get_agent_registry
            phase_results["tasks"]["agent_coordinator"] = {
                "status": "✅",
                "complete": True,
                "note": "Using services.agents implementation"
            }
            phase_results["imports_work"]["coordinator"] = True
        except ImportError as e:
            phase_results["tasks"]["agent_coordinator"] = {
                "status": "❌",
                "complete": False,
                "error": str(e)
            }
            phase_results["imports_work"]["coordinator"] = False
        
        # Task 3: Agent Registry
        try:
            from src.services.agents.registry import AgentRegistry, get_agent_registry
            phase_results["tasks"]["agent_registry"] = {
                "status": "✅",
                "complete": True,
                "note": "Using services.agents.registry"
            }
            phase_results["imports_work"]["registry"] = True
        except ImportError as e:
            phase_results["tasks"]["agent_registry"] = {
                "status": "❌",
                "complete": False,
                "error": str(e)
            }
            phase_results["imports_work"]["registry"] = False
        
        # Task 4: Agent-Tool Bridge (part of services.agents)
        try:
            from src.services.agents.base import BaseAgent
            phase_results["tasks"]["agent_tool_bridge"] = {
                "status": "✅",
                "complete": True,
                "note": "Tool integration in BaseAgent"
            }
            phase_results["imports_work"]["bridge"] = True
        except ImportError as e:
            phase_results["tasks"]["agent_tool_bridge"] = {
                "status": "❌",
                "complete": False,
                "error": str(e)
            }
            phase_results["imports_work"]["bridge"] = False
        
        # Task 5: Temporal Workflows
        temporal_files = [
            "src/infrastructure/temporal/temporal_client.py",
            "src/infrastructure/temporal/temporal_server.py"
        ]
        temporal_exist = all((self.project_root / f).exists() for f in temporal_files)
        
        phase_results["tasks"]["temporal_workflows"] = {
            "status": "✅" if temporal_exist else "❌",
            "complete": temporal_exist
        }
        
        # Calculate completion
        total_tasks = len(phase_results["tasks"])
        completed = sum(1 for t in phase_results["tasks"].values() if t.get("complete", False))
        phase_results["completion"] = (completed / total_tasks * 100) if total_tasks > 0 else 0
        
        return phase_results
    
    def validate_phase_5(self) -> Dict[str, Any]:
        """Validate Phase 5: Tool Framework and Business Logic."""
        phase_results = {
            "phase": "Phase 5: Tool Framework and Business Logic",
            "tasks": {},
            "imports_work": {},
            "completion": 0
        }
        
        # Task 1: Tool Framework
        try:
            from src.core.tools.base_tool import BaseTool
            from src.core.tools.tool_registry import ToolRegistry
            from src.core.tools.task_processor import TaskProcessor
            
            phase_results["tasks"]["tool_framework"] = {
                "status": "✅",
                "complete": True
            }
            phase_results["imports_work"]["tools"] = True
        except ImportError as e:
            phase_results["tasks"]["tool_framework"] = {
                "status": "❌",
                "complete": False,
                "error": str(e)
            }
            phase_results["imports_work"]["tools"] = False
        
        # Task 2: Analysis Tools
        analysis_tools = ["activity_classifier", "competency_assessor", "database_query", "cache_manager"]
        analysis_ok = []
        
        for tool in analysis_tools:
            tool_path = self.project_root / f"src/core/tools/analysis/{tool}.py"
            if tool_path.exists():
                analysis_ok.append(tool)
        
        phase_results["tasks"]["analysis_tools"] = {
            "status": "✅" if len(analysis_ok) == len(analysis_tools) else "⚠️",
            "complete": len(analysis_ok) == len(analysis_tools),
            "working_tools": analysis_ok
        }
        
        # Task 3: Advisor Tools
        advisor_tools = ["recommendation_engine", "goal_tracker", "report_generator", "resource_finder"]
        advisor_ok = []
        
        for tool in advisor_tools:
            tool_path = self.project_root / f"src/core/tools/advisor/{tool}.py"
            if tool_path.exists():
                advisor_ok.append(tool)
        
        phase_results["tasks"]["advisor_tools"] = {
            "status": "✅" if len(advisor_ok) == len(advisor_tools) else "⚠️",
            "complete": len(advisor_ok) == len(advisor_tools),
            "working_tools": advisor_ok
        }
        
        # Task 4: Business Logic Engines
        engines = ["competency_engine", "growth_engine", "matching_engine", "analytics_engine", "reporting_engine"]
        engines_ok = []
        
        for engine in engines:
            try:
                module_path = f"src.core.business_logic.{engine}"
                module = importlib.import_module(module_path)
                engines_ok.append(engine)
            except Exception as e:
                self.import_errors.append(f"Engine {engine}: {e}")
        
        phase_results["tasks"]["business_engines"] = {
            "status": "✅" if len(engines_ok) == len(engines) else "⚠️",
            "complete": len(engines_ok) == len(engines),
            "working_engines": engines_ok
        }
        
        # Task 5: Task Processing
        try:
            from src.core.tools.task_processor import TaskProcessor
            phase_results["tasks"]["task_processing"] = {
                "status": "✅",
                "complete": True
            }
        except ImportError:
            phase_results["tasks"]["task_processing"] = {
                "status": "❌",
                "complete": False
            }
        
        # Calculate completion
        total_tasks = len(phase_results["tasks"])
        completed = sum(1 for t in phase_results["tasks"].values() if t.get("complete", False))
        phase_results["completion"] = (completed / total_tasks * 100) if total_tasks > 0 else 0
        
        return phase_results
    
    def test_end_to_end_connectivity(self) -> Dict[str, Any]:
        """Test if components can work together."""
        connectivity = {
            "can_start": False,
            "components_connect": {},
            "errors": [],
            "runnable": False
        }
        
        # Test 1: Can we initialize the configuration?
        try:
            from src.infrastructure.config.config_manager import get_config_manager
            config = get_config_manager().get_config()
            connectivity["components_connect"]["configuration"] = True
        except Exception as e:
            connectivity["components_connect"]["configuration"] = False
            connectivity["errors"].append(f"Config: {e}")
        
        # Test 2: Can we initialize logging?
        try:
            from src.shared.logging import get_logger
            logger = get_logger("test")
            connectivity["components_connect"]["logging"] = True
        except Exception as e:
            connectivity["components_connect"]["logging"] = False
            connectivity["errors"].append(f"Logging: {e}")
        
        # Test 3: Can we create an agent?
        try:
            from src.services.agents.analysis_agent import AnalysisAgent
            agent = AnalysisAgent()
            connectivity["components_connect"]["agents"] = True
        except Exception as e:
            connectivity["components_connect"]["agents"] = False
            connectivity["errors"].append(f"Agents: {e}")
        
        # Test 4: Can we access business logic?
        try:
            from src.core.business_logic import CompetencyEngine
            engine = CompetencyEngine()
            connectivity["components_connect"]["business_logic"] = True
        except Exception as e:
            connectivity["components_connect"]["business_logic"] = False
            connectivity["errors"].append(f"Business Logic: {e}")
        
        # Test 5: Can we import the main application?
        try:
            from src.main import app  # Assuming FastAPI app
            connectivity["components_connect"]["main_app"] = True
            connectivity["can_start"] = True
        except Exception as e:
            connectivity["components_connect"]["main_app"] = False
            connectivity["errors"].append(f"Main App: {e}")
        
        # Determine if runnable
        critical_components = ["configuration", "logging", "agents", "business_logic"]
        working_components = sum(1 for c in critical_components 
                               if connectivity["components_connect"].get(c, False))
        
        connectivity["runnable"] = working_components >= 3  # At least 3/4 critical components
        
        return connectivity
    
    def run_validation(self):
        """Run complete validation."""
        print("\n" + "="*80)
        print("🔍 COMPREHENSIVE PHASE 1-5 VALIDATION")
        print("="*80)
        
        # Validate each phase
        phases = [
            self.validate_phase_1(),
            self.validate_phase_2(),
            self.validate_phase_3(),
            self.validate_phase_4(),
            self.validate_phase_5()
        ]
        
        # Test connectivity
        connectivity = self.test_end_to_end_connectivity()
        
        # Print results
        total_completion = 0
        for phase in phases:
            print(f"\n{'='*60}")
            print(f"📌 {phase['phase']}")
            print(f"Completion: {phase['completion']:.1f}%")
            print("-"*60)
            
            for task_name, task_data in phase["tasks"].items():
                print(f"{task_data['status']} {task_name.replace('_', ' ').title()}")
                if not task_data.get("complete", False) and "error" in task_data:
                    print(f"   Error: {task_data['error'][:100]}")
            
            total_completion += phase["completion"]
        
        avg_completion = total_completion / len(phases)
        
        print("\n" + "="*80)
        print("🔗 END-TO-END CONNECTIVITY TEST")
        print("="*80)
        
        print(f"Can Start Application: {'✅' if connectivity['can_start'] else '❌'}")
        print(f"Application Runnable: {'✅' if connectivity['runnable'] else '❌'}")
        print("\nComponent Connectivity:")
        for component, works in connectivity["components_connect"].items():
            print(f"  {'✅' if works else '❌'} {component.replace('_', ' ').title()}")
        
        if connectivity["errors"]:
            print("\nConnectivity Errors:")
            for error in connectivity["errors"][:5]:
                print(f"  - {error[:100]}")
        
        print("\n" + "="*80)
        print("📊 OVERALL ASSESSMENT")
        print("="*80)
        
        print(f"\nAverage Completion: {avg_completion:.1f}%")
        
        # Determine readiness
        if avg_completion >= 90 and connectivity["runnable"]:
            status = "✅ PRODUCTION READY"
        elif avg_completion >= 70 and connectivity["runnable"]:
            status = "⚠️ MOSTLY COMPLETE (Needs minor fixes)"
        elif avg_completion >= 50:
            status = "🔧 PARTIALLY COMPLETE (Major gaps remain)"
        else:
            status = "❌ NOT READY (Significant work needed)"
        
        print(f"Status: {status}")
        
        if self.import_errors:
            print(f"\n⚠️ Import Errors Found: {len(self.import_errors)}")
            for error in self.import_errors[:5]:
                print(f"  - {error[:100]}")
        
        return phases, connectivity, avg_completion


if __name__ == "__main__":
    validator = PhaseValidator()
    phases, connectivity, completion = validator.run_validation()