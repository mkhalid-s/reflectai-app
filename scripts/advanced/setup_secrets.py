#!/usr/bin/env python3
"""
Production Secrets Setup Script for ReflectAI

This script helps set up production-ready API keys and secrets for ReflectAI.
It supports multiple secret management approaches:

1. Doppler (Recommended for production)
2. Environment variables (.env file)
3. AWS Secrets Manager (future)
4. Azure Key Vault (future)
"""

import os
import sys
import secrets
import base64
import getpass
from pathlib import Path
from typing import Dict, Optional, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from infrastructure.config import get_secrets_manager
    from shared import get_logger
    REFLECTAI_AVAILABLE = True
except ImportError:
    REFLECTAI_AVAILABLE = False


class SecretsSetup:
    """Interactive secrets setup for ReflectAI"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.secrets = {}
        
    def _setup_logger(self):
        """Setup basic logging"""
        import logging
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    def run(self):
        """Run interactive secrets setup"""
        print("🔐 ReflectAI Production Secrets Setup")
        print("=" * 50)
        
        # Choose setup method
        method = self._choose_setup_method()
        
        if method == "doppler":
            self._setup_doppler()
        elif method == "env":
            self._setup_env_file()
        elif method == "validate":
            self._validate_existing()
        else:
            print("❌ Invalid choice. Exiting.")
            return 1
        
        print("\n✅ Secrets setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Verify all secrets are accessible")
        print("2. Test API connections")
        print("3. Run the application")
        
        return 0
    
    def _choose_setup_method(self) -> str:
        """Choose secrets management method"""
        print("\n🎯 Choose secrets management method:")
        print("1. Doppler (Recommended for production)")
        print("2. Environment file (.env)")
        print("3. Validate existing configuration")
        
        while True:
            choice = input("\nEnter choice (1-3): ").strip()
            if choice == "1":
                return "doppler"
            elif choice == "2":
                return "env"
            elif choice == "3":
                return "validate"
            else:
                print("❌ Please enter 1, 2, or 3")
    
    def _setup_doppler(self):
        """Setup Doppler configuration"""
        print("\n🌊 Setting up Doppler secrets management...")
        
        # Get Doppler configuration
        project = input("Doppler project name [reflectai]: ").strip() or "reflectai"
        environment = input("Doppler environment [development]: ").strip() or "development"
        
        print(f"\n📝 Instructions for Doppler setup:")
        print(f"1. Install Doppler CLI: https://docs.doppler.com/docs/install-cli")
        print(f"2. Create project: doppler projects create {project}")
        print(f"3. Setup environment: doppler environments create {environment} --project {project}")
        print(f"4. Get service token: doppler configs tokens create --project {project} --config {environment}")
        print(f"5. Set DOPPLER_TOKEN environment variable with the service token")
        
        print(f"\n⚙️ Add these secrets to your Doppler project:")
        self._print_required_secrets()
        
        # Offer to set environment variables for Doppler
        if input("\nSet Doppler environment variables now? (y/n): ").lower().startswith('y'):
            self._create_doppler_env()
    
    def _setup_env_file(self):
        """Setup .env file configuration"""
        print("\n📄 Setting up .env file...")
        
        env_file = Path(".env")
        if env_file.exists():
            overwrite = input("⚠️  .env file exists. Overwrite? (y/n): ")
            if not overwrite.lower().startswith('y'):
                print("Keeping existing .env file.")
                return
        
        # Copy template
        template = Path(".env.example")
        if not template.exists():
            print("❌ .env.example template not found!")
            return
        
        # Interactive secret gathering
        secrets_to_set = self._gather_secrets_interactive()
        
        # Create .env file
        self._create_env_file(secrets_to_set)
        
        print(f"✅ Created .env file with {len(secrets_to_set)} secrets")
        print("⚠️  Remember to add .env to your .gitignore!")
    
    def _validate_existing(self):
        """Validate existing configuration"""
        print("\n🔍 Validating existing secrets configuration...")
        
        if not REFLECTAI_AVAILABLE:
            print("❌ ReflectAI modules not available. Install dependencies first.")
            return
        
        try:
            secrets_manager = get_secrets_manager()
            
            # Test required secrets
            required_secrets = [
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY", 
                "DATABASE_URL",
                "REDIS_URL",
                "JWT_SECRET_KEY"
            ]
            
            results = {}
            for secret in required_secrets:
                try:
                    value = secrets_manager.get_secret(secret)
                    results[secret] = "✅ Found" if value else "❌ Missing"
                except Exception as e:
                    results[secret] = f"❌ Error: {e}"
            
            print("\n📊 Secrets validation results:")
            for secret, status in results.items():
                print(f"  {secret}: {status}")
            
            # Test API connections
            print("\n🔗 Testing API connections...")
            self._test_api_connections(secrets_manager)
            
        except Exception as e:
            print(f"❌ Error validating secrets: {e}")
    
    def _gather_secrets_interactive(self) -> Dict[str, str]:
        """Gather secrets interactively"""
        secrets = {}
        
        print("\n🔑 Enter API keys and secrets:")
        print("(Press Enter to skip optional secrets)")
        
        # Required LLM API keys
        print("\n--- LLM Provider API Keys (Required) ---")
        secrets["OPENAI_API_KEY"] = self._get_secret_input(
            "OpenAI API Key (sk-...)", required=True
        )
        secrets["ANTHROPIC_API_KEY"] = self._get_secret_input(
            "Anthropic API Key (sk-ant-...)", required=True
        )
        
        # Optional AWS for Bedrock
        print("\n--- AWS Bedrock (Optional) ---")
        aws_key = self._get_secret_input("AWS Access Key ID", required=False)
        if aws_key:
            secrets["AWS_ACCESS_KEY_ID"] = aws_key
            secrets["AWS_SECRET_ACCESS_KEY"] = self._get_secret_input(
                "AWS Secret Access Key", required=True, sensitive=True
            )
            secrets["AWS_REGION"] = input("AWS Region [us-east-1]: ").strip() or "us-east-1"
        
        # Database
        print("\n--- Database Configuration ---")
        secrets["DATABASE_URL"] = self._get_secret_input(
            "Database URL", 
            default="postgresql://reflectai_user:password@localhost:5432/reflectai",
            required=True
        )
        secrets["REDIS_URL"] = self._get_secret_input(
            "Redis URL",
            default="redis://localhost:6379/0", 
            required=True
        )
        
        # Security keys
        print("\n--- Security Keys ---")
        if input("Generate random JWT secret? (y/n) [y]: ").lower() != 'n':
            secrets["JWT_SECRET_KEY"] = self._generate_secure_key(64)
            print("✅ Generated JWT secret key")
        else:
            secrets["JWT_SECRET_KEY"] = self._get_secret_input(
                "JWT Secret Key", required=True, sensitive=True
            )
        
        if input("Generate random encryption key? (y/n) [y]: ").lower() != 'n':
            secrets["ENCRYPTION_KEY"] = self._generate_secure_key(32, base64_encode=True)
            print("✅ Generated encryption key")
        else:
            secrets["ENCRYPTION_KEY"] = self._get_secret_input(
                "Encryption Key", required=True, sensitive=True
            )
        
        # Optional Slack
        print("\n--- Slack Integration (Optional) ---")
        slack_token = self._get_secret_input("Slack Bot Token (xoxb-...)", required=False)
        if slack_token:
            secrets["SLACK_BOT_TOKEN"] = slack_token
            secrets["SLACK_SIGNING_SECRET"] = self._get_secret_input(
                "Slack Signing Secret", required=True, sensitive=True
            )
        
        return {k: v for k, v in secrets.items() if v}
    
    def _get_secret_input(
        self, 
        prompt: str, 
        required: bool = False, 
        sensitive: bool = False,
        default: str = None
    ) -> str:
        """Get secret input with validation"""
        full_prompt = f"{prompt}"
        if default:
            full_prompt += f" [{default}]"
        if not required:
            full_prompt += " (optional)"
        full_prompt += ": "
        
        while True:
            if sensitive:
                value = getpass.getpass(full_prompt)
            else:
                value = input(full_prompt).strip()
            
            if not value and default:
                value = default
                
            if not value and required:
                print("❌ This field is required!")
                continue
                
            return value
    
    def _generate_secure_key(self, length: int, base64_encode: bool = False) -> str:
        """Generate a cryptographically secure random key"""
        key_bytes = secrets.token_bytes(length)
        if base64_encode:
            return base64.b64encode(key_bytes).decode('ascii')
        else:
            return key_bytes.hex()
    
    def _create_env_file(self, secrets_to_set: Dict[str, str]):
        """Create .env file from template with secrets"""
        template_path = Path(".env.example")
        env_path = Path(".env")
        
        # Read template
        template_content = template_path.read_text()
        
        # Replace placeholder values
        env_content = template_content
        for key, value in secrets_to_set.items():
            # Replace the template value
            pattern = f"{key}=.*"
            replacement = f"{key}={value}"
            env_content = re.sub(pattern, replacement, env_content)
        
        # Write .env file
        env_path.write_text(env_content)
    
    def _create_doppler_env(self):
        """Create Doppler environment configuration"""
        env_content = f"""# Doppler Configuration
DOPPLER_PROJECT=reflectai
DOPPLER_ENVIRONMENT=development
SECRETS_FALLBACK_TO_ENV=true

# Set DOPPLER_TOKEN with your service token:
# export DOPPLER_TOKEN=dp.st.your_service_token_here
"""
        Path(".env.doppler").write_text(env_content)
        print("✅ Created .env.doppler with Doppler configuration")
    
    def _print_required_secrets(self):
        """Print list of required secrets"""
        secrets_list = [
            "OPENAI_API_KEY - Your OpenAI API key",
            "ANTHROPIC_API_KEY - Your Anthropic API key", 
            "DATABASE_URL - PostgreSQL connection string",
            "REDIS_URL - Redis connection string",
            "JWT_SECRET_KEY - JWT signing secret (64+ chars)",
            "ENCRYPTION_KEY - Data encryption key (32 bytes, base64)",
            "SLACK_BOT_TOKEN - Slack bot token (optional)",
            "SLACK_SIGNING_SECRET - Slack signing secret (optional)",
            "AWS_ACCESS_KEY_ID - AWS access key for Bedrock (optional)",
            "AWS_SECRET_ACCESS_KEY - AWS secret key (optional)"
        ]
        
        for secret in secrets_list:
            print(f"  • {secret}")
    
    def _test_api_connections(self, secrets_manager):
        """Test API connections"""
        # This would test actual API connections
        print("🧪 API connection testing not implemented yet")
        print("   Run application tests to verify connections")


def main():
    """Main entry point"""
    try:
        setup = SecretsSetup()
        return setup.run()
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup cancelled by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    import re
    sys.exit(main())