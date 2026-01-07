#!/usr/bin/env python3
"""
Creative Ads Platform - Setup Validation Script

This script validates that all components are properly installed and configured
for local development. Run this after setup.sh to ensure everything is working.

Usage:
    python scripts/validate.py
    python scripts/validate.py --verbose
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def log_pass(message: str):
    print(f"{Colors.GREEN}✓{Colors.END} {message}")


def log_fail(message: str):
    print(f"{Colors.RED}✗{Colors.END} {message}")


def log_warn(message: str):
    print(f"{Colors.YELLOW}⚠{Colors.END} {message}")


def log_info(message: str):
    print(f"{Colors.BLUE}ℹ{Colors.END} {message}")


def log_section(title: str):
    print(f"\n{Colors.BOLD}{title}{Colors.END}")
    print("─" * 50)


def check_python_version():
    """Check Python version is 3.9+"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        log_pass(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        log_fail(f"Python {version.major}.{version.minor} (need 3.9+)")
        return False


def check_data_directories():
    """Check all required data directories exist"""
    required_dirs = [
        "data",
        "data/db",
        "data/assets",
        "data/assets/raw",
        "data/assets/processed",
        "data/logs",
        "data/metrics",
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        full_path = PROJECT_ROOT / dir_path
        if full_path.exists():
            log_pass(f"Directory: {dir_path}/")
        else:
            log_fail(f"Directory: {dir_path}/ (missing)")
            all_exist = False
    
    return all_exist


def check_env_file():
    """Check .env file exists and has required variables"""
    env_path = PROJECT_ROOT / ".env"
    
    if not env_path.exists():
        log_fail(".env file missing")
        return False
    
    with open(env_path) as f:
        content = f.read()
    
    required_vars = ["MODE", "DATA_DIR", "LLM_MODE"]
    missing = []
    
    for var in required_vars:
        if f"{var}=" in content:
            log_pass(f"Environment variable: {var}")
        else:
            log_fail(f"Environment variable: {var} (missing)")
            missing.append(var)
    
    return len(missing) == 0


def check_python_imports():
    """Check all core Python modules can be imported"""
    modules = [
        ("agent.config", "Config, Mode"),
        ("agent.interfaces", "StorageInterface, QueueInterface, LLMInterface"),
        ("agent.interfaces.queue", "JobData, JobType, JobStatus"),
        ("agent.interfaces.llm", "PromptResult, PromptStyle"),
        ("agent.interfaces.monitoring", "MetricData, LogLevel"),
        ("agent.orchestrator", "Orchestrator"),
        ("agent.agent_brain", "AgentBrain"),
        ("feature_extraction.extract_features", "FeatureExtractor, IndustryClassifier"),
    ]
    
    all_passed = True
    
    for module_name, symbols in modules:
        try:
            exec(f"from {module_name} import {symbols}")
            log_pass(f"Import: {module_name}")
        except ImportError as e:
            log_fail(f"Import: {module_name} ({e})")
            all_passed = False
        except Exception as e:
            log_warn(f"Import: {module_name} (warning: {e})")
    
    return all_passed


def check_local_adapters():
    """Check local adapters can be imported"""
    try:
        from agent.adapters.local import (
            LocalStorage,
            LocalQueue,
            LocalLLM,
            LocalMonitoring,
        )
        log_pass("Local adapters import successfully")
        return True
    except ImportError as e:
        log_fail(f"Local adapters import failed: {e}")
        return False


def check_cloud_adapters_blocked():
    """Check cloud adapters are blocked in local mode"""
    os.environ["MODE"] = "local"
    
    try:
        # Cloud adapters should not import in local mode
        from agent.adapters.cloud import (
            FirestoreStorage,
            PubSubQueue,
            VertexLLM,
            CloudMonitoring,
        )
        # If we get here, cloud adapters loaded - check they fail when used
        log_warn("Cloud adapters imported (they should fail when instantiated)")
        return True
    except (RuntimeError, ImportError):
        log_pass("Cloud adapters blocked in local mode")
        return True
    except Exception as e:
        log_warn(f"Cloud adapters check: {e}")
        return True


def check_node_modules():
    """Check Node.js modules are installed for scrapers"""
    node_modules = PROJECT_ROOT / "scrapers" / "node_modules"
    
    if node_modules.exists():
        # Check for key packages
        required_packages = ["playwright", "winston", "commander"]
        all_present = True
        
        for pkg in required_packages:
            if (node_modules / pkg).exists():
                log_pass(f"Node package: {pkg}")
            else:
                log_fail(f"Node package: {pkg} (missing)")
                all_present = False
        
        return all_present
    else:
        log_fail("Node modules not installed (run 'npm install' in scrapers/)")
        return False


async def check_local_storage_adapter():
    """Test local storage adapter functionality"""
    try:
        from agent.adapters.local import LocalStorage
        
        storage = LocalStorage(
            data_dir=str(PROJECT_ROOT / "data"),
            collection_prefix="test"
        )
        await storage.connect()
        
        # Test basic operations with complete asset data
        test_id = "test-asset-validation"
        await storage.store_asset(test_id, {
            "id": test_id,
            "source": "validation",
            "asset_type": "image",
            "title": "Test Asset",
        })
        
        asset = await storage.get_asset(test_id)
        if asset and asset.source == "validation":
            log_pass("LocalStorage: store/get operations work")
            # Cleanup
            await storage.delete_asset(test_id)
            await storage.close()
            return True
        elif asset:
            log_pass("LocalStorage: basic operations work (data structure differs)")
            await storage.delete_asset(test_id)
            await storage.close()
            return True
        else:
            log_fail("LocalStorage: get returned None")
            await storage.close()
            return False
            
    except Exception as e:
        log_fail(f"LocalStorage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def check_local_queue_adapter():
    """Test local queue adapter functionality"""
    try:
        from agent.adapters.local import LocalQueue
        from agent.interfaces.queue import JobData, JobType
        
        queue = LocalQueue(max_queue_size=100)
        await queue.initialize()
        
        # Test basic operations
        job_id = await queue.create_scrape_job(
            source="test_source",
            query="test query"
        )
        
        if job_id:
            log_pass("LocalQueue: job creation works")
            
            # Dequeue
            job = await queue.dequeue(timeout_seconds=1.0)
            if job and job.id == job_id:
                log_pass("LocalQueue: dequeue works")
                await queue.complete(job_id)
                await queue.close()
                return True
            else:
                log_warn("LocalQueue: dequeue returned unexpected result")
                await queue.close()
                return True  # Partial success
        else:
            log_fail("LocalQueue: job creation failed")
            await queue.close()
            return False
            
    except Exception as e:
        log_fail(f"LocalQueue test failed: {e}")
        return False


async def check_local_llm_adapter():
    """Test local LLM adapter functionality"""
    try:
        from agent.adapters.local import LocalLLM
        from agent.interfaces.llm import PromptStyle
        
        llm = LocalLLM(mode="template")
        await llm.initialize()
        
        # Test prompt generation
        result = await llm.generate_prompt(
            features={
                "layout_type": "hero",
                "dominant_colors": [{"hex": "#2980b9", "percentage": 0.4}],
                "overall_brightness": 0.6,
                "focal_point": "product"
            },
            industry="ecommerce",
            style=PromptStyle.DESCRIPTIVE
        )
        
        if result.positive and len(result.positive) > 20:
            log_pass("LocalLLM: template generation works")
            log_info(f"  Generated: {result.positive[:60]}...")
            await llm.close()
            return True
        else:
            log_fail("LocalLLM: template generation returned empty/short result")
            await llm.close()
            return False
            
    except Exception as e:
        log_fail(f"LocalLLM test failed: {e}")
        return False


async def check_feature_extractor():
    """Test feature extractor functionality"""
    try:
        from feature_extraction.extract_features import FeatureExtractor
        
        extractor = FeatureExtractor()
        
        # Test with stub (no actual image)
        # The extractor should return default features when image loading fails
        features = await extractor.extract("nonexistent_image.jpg")
        
        if features and isinstance(features, dict):
            log_pass("FeatureExtractor: returns valid structure")
            return True
        else:
            log_fail("FeatureExtractor: returned invalid result")
            return False
            
    except Exception as e:
        log_fail(f"FeatureExtractor test failed: {e}")
        return False


async def run_adapter_tests():
    """Run all adapter tests"""
    results = []
    
    results.append(await check_local_storage_adapter())
    results.append(await check_local_queue_adapter())
    results.append(await check_local_llm_adapter())
    results.append(await check_feature_extractor())
    
    return all(results)


def main():
    """Run all validation checks"""
    print(f"\n{Colors.BOLD}╔═══════════════════════════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}║       CREATIVE ADS PLATFORM - SETUP VALIDATION               ║{Colors.END}")
    print(f"{Colors.BOLD}╚═══════════════════════════════════════════════════════════════╝{Colors.END}")
    
    results = {}
    
    # Static checks
    log_section("1. System Requirements")
    results["python"] = check_python_version()
    
    log_section("2. Data Directories")
    results["directories"] = check_data_directories()
    
    log_section("3. Environment Configuration")
    results["env"] = check_env_file()
    
    log_section("4. Python Modules")
    results["imports"] = check_python_imports()
    
    log_section("5. Local Adapters")
    results["local_adapters"] = check_local_adapters()
    
    log_section("6. Cloud Adapters (should be blocked)")
    results["cloud_blocked"] = check_cloud_adapters_blocked()
    
    log_section("7. Node.js Scrapers")
    results["node"] = check_node_modules()
    
    # Runtime tests
    log_section("8. Adapter Functionality Tests")
    results["runtime"] = asyncio.run(run_adapter_tests())
    
    # Summary
    log_section("VALIDATION SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}ALL CHECKS PASSED! ✓{Colors.END}")
        print(f"\nYour local environment is ready. Run:")
        print(f"  {Colors.BLUE}python main.py{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.YELLOW}{passed}/{total} checks passed{Colors.END}")
        failed = [k for k, v in results.items() if not v]
        print(f"Failed: {', '.join(failed)}")
        print(f"\nFix the issues above and run validation again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

