#!/usr/bin/env python3
"""
Redis Development Environment Setup Script

This script sets up a complete Redis development environment for ReflectAI including:
1. Redis Stack with all modules
2. Development data seeding
3. Cache warming with sample data
4. Task queue initialization
5. Development user profiles and sessions
6. Performance monitoring setup

Usage:
    python scripts/setup_redis_dev.py --full-setup
    python scripts/setup_redis_dev.py --seed-data --warm-cache
    python scripts/setup_redis_dev.py --create-test-tasks
    python scripts/setup_redis_dev.py --reset-development-data
"""

import asyncio
import json
import random
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

try:
    import redis.asyncio as redis
except ImportError:
    print("ERROR: redis package not found. Install with: pip install redis[hiredis]")
    sys.exit(1)

from core.storage.redis_manager import RedisManager, RedisConnectionConfig
from core.tools.task_processor import TaskProcessor, TaskRequest, TaskPriority
from core.tools.base_tool import ToolRequest, ToolResponse, ToolStatus
from shared import get_logger


class RedisDevSetup:
    """Redis development environment setup and management"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, redis_password: Optional[str] = None):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_password = redis_password
        self.logger = get_logger("redis.dev.setup")
        
        # Components
        self.redis_manager: Optional[RedisManager] = None
        self.task_processor: Optional[TaskProcessor] = None
        
        # Sample data
        self.sample_users = self._generate_sample_users()
        self.sample_conversations = self._generate_sample_conversations()
        self.sample_competencies = self._generate_sample_competencies()
    
    async def initialize(self) -> bool:
        """Initialize Redis components"""
        try:
            # Setup Redis manager
            config = RedisConnectionConfig(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                enable_json=True,
                enable_search=True,
                enable_timeseries=True
            )
            
            self.redis_manager = RedisManager(config)
            await self.redis_manager.initialize()
            
            # Setup task processor
            self.task_processor = TaskProcessor(
                redis_host=self.redis_host,
                redis_port=self.redis_port,
                redis_password=self.redis_password,
                queue_prefix="reflectai:dev:tasks"
            )
            await self.task_processor.initialize()
            
            self.logger.info("Redis development environment initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis dev environment: {str(e)}")
            return False
    
    async def cleanup(self) -> None:
        """Cleanup connections"""
        try:
            if self.task_processor:
                await self.task_processor.shutdown()
            if self.redis_manager:
                await self.redis_manager.close()
        except Exception as e:
            self.logger.error(f"Cleanup error: {str(e)}")
    
    def _generate_sample_users(self) -> List[Dict[str, Any]]:
        """Generate sample user data"""
        return [
            {
                "user_id": "dev_user_001",
                "slack_id": "U01DEV001",
                "name": "Alice Developer",
                "email": "alice@reflectai-dev.com",
                "role": "Software Engineer",
                "role_level": "senior",
                "department": "Engineering",
                "competencies": ["Python", "React", "AWS", "Leadership"],
                "preferences": {
                    "notification_frequency": "daily",
                    "analysis_depth": "detailed",
                    "home_tab_sections": ["recent_activity", "recommendations", "analytics"]
                },
                "activity_patterns": {
                    "peak_hours": [9, 10, 14, 15, 16],
                    "avg_sessions_per_day": 8,
                    "avg_session_duration": 45
                }
            },
            {
                "user_id": "dev_user_002",
                "slack_id": "U02DEV002", 
                "name": "Bob Manager",
                "email": "bob@reflectai-dev.com",
                "role": "Engineering Manager",
                "role_level": "manager",
                "department": "Engineering",
                "competencies": ["Team Leadership", "Strategy", "Agile", "Mentoring"],
                "preferences": {
                    "notification_frequency": "weekly",
                    "analysis_depth": "summary",
                    "home_tab_sections": ["team_overview", "goals", "reports"]
                },
                "activity_patterns": {
                    "peak_hours": [8, 9, 13, 17],
                    "avg_sessions_per_day": 5,
                    "avg_session_duration": 30
                }
            },
            {
                "user_id": "dev_user_003",
                "slack_id": "U03DEV003",
                "name": "Carol Analyst",
                "email": "carol@reflectai-dev.com", 
                "role": "Data Analyst",
                "role_level": "mid",
                "department": "Data",
                "competencies": ["SQL", "Python", "Tableau", "Statistics"],
                "preferences": {
                    "notification_frequency": "immediate",
                    "analysis_depth": "comprehensive",
                    "home_tab_sections": ["analytics", "insights", "trends"]
                },
                "activity_patterns": {
                    "peak_hours": [10, 11, 14, 15, 16, 17],
                    "avg_sessions_per_day": 12,
                    "avg_session_duration": 60
                }
            }
        ]
    
    def _generate_sample_conversations(self) -> List[Dict[str, Any]]:
        """Generate sample conversation data"""
        conversations = []
        
        for i, user in enumerate(self.sample_users):
            for day_offset in range(7):  # Last 7 days
                date = datetime.utcnow() - timedelta(days=day_offset)
                
                conversations.extend([
                    {
                        "conversation_id": f"conv_{user['user_id']}_{day_offset}_{j}",
                        "user_id": user["user_id"],
                        "timestamp": date - timedelta(hours=random.randint(1, 23)),
                        "type": random.choice(["question", "analysis_request", "reflection", "goal_setting"]),
                        "topic": random.choice(["career_development", "technical_skills", "leadership", "project_planning"]),
                        "sentiment": random.choice(["positive", "neutral", "curious", "concerned"]),
                        "keywords": random.sample(["growth", "learning", "challenges", "team", "strategy", "innovation"], k=3),
                        "summary": f"User discussed {random.choice(['career growth', 'technical challenges', 'team dynamics', 'project goals'])}",
                        "insights": [
                            f"Shows interest in {random.choice(['leadership development', 'technical growth', 'team collaboration'])}",
                            f"Demonstrates {random.choice(['analytical thinking', 'strategic planning', 'problem-solving'])} skills"
                        ]
                    }
                    for j in range(random.randint(1, 4))  # 1-4 conversations per day
                ])
        
        return conversations
    
    def _generate_sample_competencies(self) -> Dict[str, Any]:
        """Generate sample competency data"""
        return {
            "technical_skills": {
                "Python": {
                    "category": "Programming Languages",
                    "level_ranges": {"junior": [1, 3], "mid": [3, 6], "senior": [6, 8], "expert": [8, 10]},
                    "learning_resources": [
                        {"type": "course", "title": "Advanced Python Patterns", "url": "https://example.com/python-advanced"},
                        {"type": "book", "title": "Effective Python", "author": "Brett Slatkin"},
                        {"type": "practice", "title": "Python Coding Challenges", "url": "https://example.com/challenges"}
                    ]
                },
                "React": {
                    "category": "Frontend Frameworks",
                    "level_ranges": {"junior": [1, 4], "mid": [4, 7], "senior": [7, 9], "expert": [9, 10]},
                    "learning_resources": [
                        {"type": "course", "title": "React Advanced Patterns", "url": "https://example.com/react-advanced"},
                        {"type": "documentation", "title": "React Official Docs", "url": "https://react.dev"}
                    ]
                },
                "AWS": {
                    "category": "Cloud Platforms",
                    "level_ranges": {"junior": [1, 3], "mid": [3, 6], "senior": [6, 8], "expert": [8, 10]},
                    "learning_resources": [
                        {"type": "certification", "title": "AWS Solutions Architect", "url": "https://aws.amazon.com/certification/"},
                        {"type": "course", "title": "AWS DeepDive", "url": "https://example.com/aws-deepdive"}
                    ]
                }
            },
            "soft_skills": {
                "Leadership": {
                    "category": "Management",
                    "level_ranges": {"emerging": [1, 3], "developing": [3, 6], "proficient": [6, 8], "advanced": [8, 10]},
                    "learning_resources": [
                        {"type": "book", "title": "The Manager's Path", "author": "Camille Fournier"},
                        {"type": "course", "title": "Leadership Fundamentals", "url": "https://example.com/leadership"}
                    ]
                },
                "Communication": {
                    "category": "Interpersonal",
                    "level_ranges": {"basic": [1, 3], "intermediate": [3, 6], "advanced": [6, 8], "expert": [8, 10]},
                    "learning_resources": [
                        {"type": "workshop", "title": "Effective Communication", "url": "https://example.com/communication"},
                        {"type": "book", "title": "Crucial Conversations", "author": "Kerry Patterson"}
                    ]
                }
            }
        }
    
    async def setup_full_environment(self) -> bool:
        """Setup complete development environment"""
        try:
            self.logger.info("Setting up full Redis development environment")
            
            # Step 1: Clear existing development data
            await self.reset_development_data()
            
            # Step 2: Seed base data
            await self.seed_user_profiles()
            await self.seed_conversations()
            await self.seed_competency_data()
            
            # Step 3: Warm caches
            await self.warm_caches()
            
            # Step 4: Create sample tasks
            await self.create_sample_tasks()
            
            # Step 5: Setup monitoring data
            await self.setup_monitoring_data()
            
            self.logger.info("Full development environment setup completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Full environment setup failed: {str(e)}")
            return False
    
    async def reset_development_data(self) -> bool:
        """Reset all development data"""
        try:
            self.logger.info("Resetting development data")
            
            # Clear development namespaces
            namespaces_to_clear = ["user", "session", "activity", "competency", "home_tab", "llm"]
            
            for namespace in namespaces_to_clear:
                cleared_count = await self.redis_manager.invalidate_pattern(namespace, "*")
                self.logger.info(f"Cleared {cleared_count} keys from {namespace} namespace")
            
            # Clear task queues
            client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port, 
                password=self.redis_password,
                decode_responses=True
            )
            
            # Clear development task patterns
            task_patterns = ["reflectai:dev:tasks:*", "reflectai:tasks:*"]
            total_cleared = 0
            
            for pattern in task_patterns:
                keys = await client.keys(pattern)
                if keys:
                    await client.delete(*keys)
                    total_cleared += len(keys)
            
            await client.close()
            
            self.logger.info(f"Cleared {total_cleared} task queue keys")
            return True
            
        except Exception as e:
            self.logger.error(f"Reset development data failed: {str(e)}")
            return False
    
    async def seed_user_profiles(self) -> bool:
        """Seed user profile data"""
        try:
            self.logger.info("Seeding user profile data")
            
            for user in self.sample_users:
                # Store user profile
                await self.redis_manager.set("user", f"profile:{user['user_id']}", user)
                
                # Create active session
                session_data = {
                    "user_id": user["user_id"],
                    "slack_id": user["slack_id"],
                    "session_start": (datetime.utcnow() - timedelta(hours=random.randint(1, 8))).isoformat(),
                    "last_activity": (datetime.utcnow() - timedelta(minutes=random.randint(5, 60))).isoformat(),
                    "activity_count": random.randint(5, 20),
                    "current_context": {
                        "current_topic": random.choice(["career_development", "technical_skills", "project_planning"]),
                        "interaction_mode": random.choice(["analysis", "conversation", "reflection"]),
                        "session_goals": [
                            random.choice(["skill_assessment", "goal_setting", "progress_review"])
                        ]
                    }
                }
                
                session_id = f"dev_session_{user['user_id']}_{int(datetime.utcnow().timestamp())}"
                await self.redis_manager.set_session(session_id, session_data, user["user_id"])
                
                self.logger.info(f"Created profile and session for {user['name']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Seed user profiles failed: {str(e)}")
            return False
    
    async def seed_conversations(self) -> bool:
        """Seed conversation data"""
        try:
            self.logger.info("Seeding conversation data")
            
            for conversation in self.sample_conversations:
                # Store conversation in activity namespace
                key = f"conversation:{conversation['conversation_id']}"
                await self.redis_manager.set("activity", key, conversation)
                
                # Store conversation summary for quick access
                summary_key = f"summary:{conversation['user_id']}:{conversation['timestamp'].date()}"
                summary_data = {
                    "date": conversation['timestamp'].date().isoformat(),
                    "user_id": conversation["user_id"],
                    "conversation_count": 1,
                    "topics": [conversation["topic"]],
                    "sentiment_summary": conversation["sentiment"],
                    "key_insights": conversation.get("insights", [])
                }
                
                # Check if summary already exists and merge
                existing_summary = await self.redis_manager.get("activity", summary_key)
                if existing_summary:
                    summary_data["conversation_count"] = existing_summary.get("conversation_count", 0) + 1
                    summary_data["topics"] = list(set(existing_summary.get("topics", []) + summary_data["topics"]))
                    summary_data["key_insights"] = existing_summary.get("key_insights", []) + summary_data["key_insights"]
                
                await self.redis_manager.set("activity", summary_key, summary_data)
            
            self.logger.info(f"Seeded {len(self.sample_conversations)} conversations")
            return True
            
        except Exception as e:
            self.logger.error(f"Seed conversations failed: {str(e)}")
            return False
    
    async def seed_competency_data(self) -> bool:
        """Seed competency reference data"""
        try:
            self.logger.info("Seeding competency data")
            
            # Store competency definitions
            await self.redis_manager.set("competency", "definitions", self.sample_competencies)
            
            # Create user competency assessments
            for user in self.sample_users:
                user_competencies = {}
                
                for competency in user["competencies"]:
                    # Find competency in technical or soft skills
                    competency_data = None
                    if competency in self.sample_competencies["technical_skills"]:
                        competency_data = self.sample_competencies["technical_skills"][competency]
                    elif competency in self.sample_competencies["soft_skills"]:
                        competency_data = self.sample_competencies["soft_skills"][competency]
                    
                    if competency_data:
                        # Generate assessment based on user role level
                        level_ranges = competency_data["level_ranges"]
                        user_level = user.get("role_level", "mid")
                        
                        if user_level in level_ranges:
                            min_score, max_score = level_ranges[user_level]
                            current_score = random.randint(min_score, max_score)
                        else:
                            current_score = random.randint(3, 7)
                        
                        user_competencies[competency] = {
                            "current_level": current_score,
                            "target_level": min(current_score + random.randint(1, 3), 10),
                            "last_assessment": (datetime.utcnow() - timedelta(days=random.randint(7, 30))).isoformat(),
                            "learning_resources": competency_data["learning_resources"][:2],  # First 2 resources
                            "progress_history": [
                                {
                                    "date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                                    "score": max(1, current_score - random.randint(0, 2))
                                },
                                {
                                    "date": datetime.utcnow().isoformat(),
                                    "score": current_score
                                }
                            ]
                        }
                
                competency_key = f"assessment:{user['user_id']}"
                await self.redis_manager.set("competency", competency_key, user_competencies)
                
                self.logger.info(f"Created competency assessment for {user['name']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Seed competency data failed: {str(e)}")
            return False
    
    async def warm_caches(self) -> bool:
        """Warm caches with frequently accessed data"""
        try:
            self.logger.info("Warming caches")
            
            # Warm user cache with frequently accessed profiles
            user_cache_data = {}
            for user in self.sample_users:
                user_cache_data[f"quick_profile:{user['user_id']}"] = {
                    "user_id": user["user_id"],
                    "name": user["name"],
                    "role": user["role"],
                    "role_level": user["role_level"],
                    "preferences": user["preferences"],
                    "cached_at": datetime.utcnow().isoformat()
                }
            
            warmed_count = await self.redis_manager.warm_cache("user", user_cache_data)
            self.logger.info(f"Warmed user cache with {warmed_count} entries")
            
            # Warm LLM cache with common prompts and responses
            llm_cache_data = {}
            common_prompts = [
                "analyze_user_goals",
                "recommend_competencies", 
                "summarize_progress",
                "suggest_learning_resources",
                "generate_reflection_questions"
            ]
            
            for prompt in common_prompts:
                for user in self.sample_users:
                    cache_key = f"{prompt}:{user['user_id']}"
                    llm_cache_data[cache_key] = {
                        "prompt": prompt,
                        "user_context": user["user_id"],
                        "response": f"Sample {prompt} response for {user['name']}",
                        "generated_at": datetime.utcnow().isoformat(),
                        "confidence": random.uniform(0.8, 0.95)
                    }
            
            llm_warmed = await self.redis_manager.warm_cache("llm", llm_cache_data)
            self.logger.info(f"Warmed LLM cache with {llm_warmed} entries")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Cache warming failed: {str(e)}")
            return False
    
    async def create_sample_tasks(self) -> bool:
        """Create sample tasks for testing"""
        try:
            self.logger.info("Creating sample tasks")
            
            task_types = [
                {
                    "tool_name": "analyze_user_profile",
                    "agent_type": "analysis",
                    "priority": TaskPriority.NORMAL,
                    "base_params": {"depth": "full", "include_recommendations": True}
                },
                {
                    "tool_name": "update_home_tab",
                    "agent_type": "analysis", 
                    "priority": TaskPriority.LOW,
                    "base_params": {"sections": ["recent_activity", "recommendations"]}
                },
                {
                    "tool_name": "recommend_competencies",
                    "agent_type": "advisor",
                    "priority": TaskPriority.HIGH,
                    "base_params": {"max_recommendations": 5, "include_learning_paths": True}
                },
                {
                    "tool_name": "generate_insights",
                    "agent_type": "analysis",
                    "priority": TaskPriority.NORMAL,
                    "base_params": {"time_range": "7d", "include_trends": True}
                }
            ]
            
            created_tasks = []
            
            for user in self.sample_users:
                for task_type in task_types:
                    # Create 1-2 tasks of each type per user
                    for _ in range(random.randint(1, 2)):
                        params = {**task_type["base_params"], "user_id": user["user_id"]}
                        
                        tool_request = ToolRequest(
                            tool_name=task_type["tool_name"],
                            parameters=params,
                            user_context={"user_id": user["user_id"], "role_level": user["role_level"]}
                        )
                        
                        task_id = await self.task_processor.enqueue_task(
                            agent_type=task_type["agent_type"],
                            tool_request=tool_request,
                            priority=task_type["priority"],
                            delay_seconds=random.randint(0, 300)  # Random delay up to 5 minutes
                        )
                        
                        created_tasks.append({
                            "task_id": task_id,
                            "tool_name": task_type["tool_name"],
                            "user_id": user["user_id"],
                            "agent_type": task_type["agent_type"]
                        })
            
            self.logger.info(f"Created {len(created_tasks)} sample tasks")
            
            # Store task metadata for reference
            await self.redis_manager.set("activity", "sample_tasks", {
                "created_at": datetime.utcnow().isoformat(),
                "task_count": len(created_tasks),
                "tasks": created_tasks
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Create sample tasks failed: {str(e)}")
            return False
    
    async def setup_monitoring_data(self) -> bool:
        """Setup monitoring and analytics data"""
        try:
            self.logger.info("Setting up monitoring data")
            
            # Create performance metrics
            perf_data = {
                "system_metrics": {
                    "avg_response_time": random.uniform(0.1, 0.5),
                    "cache_hit_rate": random.uniform(0.85, 0.95),
                    "task_completion_rate": random.uniform(0.95, 0.99),
                    "error_rate": random.uniform(0.01, 0.05),
                    "active_users": len(self.sample_users),
                    "total_conversations": len(self.sample_conversations)
                },
                "user_engagement": {
                    user["user_id"]: {
                        "daily_sessions": random.randint(3, 12),
                        "avg_session_duration": random.randint(20, 90),
                        "feature_usage": {
                            "analysis": random.randint(5, 15),
                            "recommendations": random.randint(2, 8), 
                            "reflections": random.randint(1, 5),
                            "goal_setting": random.randint(0, 3)
                        },
                        "satisfaction_score": random.uniform(4.0, 5.0)
                    }
                    for user in self.sample_users
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.redis_manager.set("activity", "monitoring_data", perf_data)
            
            # Create health check data
            health_data = {
                "redis": {"status": "healthy", "response_time": 0.002},
                "task_processor": {"status": "healthy", "queue_depth": random.randint(5, 20)},
                "llm_gateway": {"status": "healthy", "avg_response_time": random.uniform(0.8, 2.0)},
                "database": {"status": "healthy", "connection_pool": "optimal"},
                "last_check": datetime.utcnow().isoformat()
            }
            
            await self.redis_manager.set("activity", "health_status", health_data)
            
            self.logger.info("Monitoring data setup completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Setup monitoring data failed: {str(e)}")
            return False
    
    async def get_environment_status(self) -> Dict[str, Any]:
        """Get development environment status"""
        try:
            # Get cache metrics
            cache_metrics = await self.redis_manager.get_cache_metrics()
            
            # Get task queue stats
            analysis_stats = await self.task_processor.get_queue_stats("analysis")
            advisor_stats = await self.task_processor.get_queue_stats("advisor") 
            
            # Get health status
            redis_health = await self.redis_manager.health_check()
            processor_health = await self.task_processor.get_health_status()
            
            return {
                "environment": "development",
                "status": "active",
                "cache_metrics": cache_metrics,
                "task_queues": {
                    "analysis": analysis_stats,
                    "advisor": advisor_stats
                },
                "health_status": {
                    "redis": redis_health,
                    "task_processor": processor_health
                },
                "sample_data": {
                    "users": len(self.sample_users),
                    "conversations": len(self.sample_conversations),
                    "competencies": len(self.sample_competencies["technical_skills"]) + len(self.sample_competencies["soft_skills"])
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Get environment status failed: {str(e)}")
            return {"status": "error", "error": str(e)}


async def main():
    """Main setup script entry point"""
    parser = argparse.ArgumentParser(description="Redis Development Environment Setup")
    parser.add_argument("--redis-host", default="localhost", help="Redis host")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis port") 
    parser.add_argument("--redis-password", help="Redis password")
    parser.add_argument("--full-setup", action="store_true", help="Run full environment setup")
    parser.add_argument("--seed-data", action="store_true", help="Seed development data")
    parser.add_argument("--warm-cache", action="store_true", help="Warm caches")
    parser.add_argument("--create-test-tasks", action="store_true", help="Create test tasks")
    parser.add_argument("--reset-development-data", action="store_true", help="Reset all development data")
    parser.add_argument("--status", action="store_true", help="Show environment status")
    parser.add_argument("--output", help="Output file for status (JSON)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create setup manager
    setup = RedisDevSetup(
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        redis_password=args.redis_password
    )
    
    try:
        # Initialize
        if not await setup.initialize():
            print("❌ Failed to initialize Redis development setup")
            sys.exit(1)
        
        success = True
        
        # Run requested operations
        if args.full_setup:
            print("🚀 Setting up full Redis development environment...")
            success = await setup.setup_full_environment()
        elif args.reset_development_data:
            print("🗑️  Resetting development data...")
            success = await setup.reset_development_data()
        else:
            # Run individual operations
            if args.seed_data:
                print("🌱 Seeding development data...")
                success &= await setup.seed_user_profiles()
                success &= await setup.seed_conversations()
                success &= await setup.seed_competency_data()
            
            if args.warm_cache:
                print("🔥 Warming caches...")
                success &= await setup.warm_caches()
            
            if args.create_test_tasks:
                print("⚙️  Creating test tasks...")
                success &= await setup.create_sample_tasks()
        
        # Show status if requested or after setup
        if args.status or args.full_setup:
            print("\n📊 Environment Status:")
            status = await setup.get_environment_status()
            
            print(f"Status: {status.get('status', 'unknown')}")
            
            if 'sample_data' in status:
                sample_data = status['sample_data']
                print(f"Sample Data: {sample_data['users']} users, {sample_data['conversations']} conversations")
            
            if 'cache_metrics' in status and 'total' in status['cache_metrics']:
                total_metrics = status['cache_metrics']['total']
                print(f"Cache: {total_metrics['hit_count']} hits, {total_metrics['set_count']} sets, {total_metrics.get('hit_rate', 0):.2%} hit rate")
            
            if 'task_queues' in status:
                queues = status['task_queues']
                for agent_type, stats in queues.items():
                    if 'processing_stats' in stats:
                        proc_stats = stats['processing_stats']
                        print(f"Tasks ({agent_type}): {proc_stats.get('tasks_processed', 0)} processed")
            
            # Save detailed status if requested
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(status, f, indent=2, default=str)
                print(f"Detailed status saved to: {args.output}")
        
        # Cleanup
        await setup.cleanup()
        
        if success:
            print(f"\n✅ Redis development environment setup completed successfully!")
        else:
            print(f"\n❌ Setup completed with some errors. Check logs for details.")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⏹️  Setup interrupted by user")
        await setup.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {str(e)}")
        await setup.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())