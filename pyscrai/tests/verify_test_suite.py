"""Test suite verification script for PyScrAI Universalis.

This script verifies the completeness and correctness of the test suite.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
import importlib.util
import inspect


class TestSuiteVerifier:
    """Verifies the completeness and correctness of the test suite."""
    
    def __init__(self, tests_dir: Path):
        self.tests_dir = tests_dir
        self.issues = []
        self.warnings = []
        self.stats = {
            'total_files': 0,
            'test_files': 0,
            'unit_tests': 0,
            'integration_tests': 0,
            'functional_tests': 0,
            'total_test_methods': 0
        }
    
    def verify_structure(self) -> bool:
        """Verify the test directory structure is correct."""
        required_files = [
            'conftest.py',
            'test_config.py',
            'unit/__init__.py',
            'unit/test_schemas.py',
            'unit/test_spatial_math.py',
            'integration/__init__.py',
            'integration/test_duckdb.py',
            'integration/test_memory.py',
            'integration/test_engine.py',
            'functional/__init__.py',
            'functional/test_seeding_pipeline.py'
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.tests_dir / file_path
            if not full_path.exists():
                missing_files.append(str(full_path))
                self.issues.append(f"Missing required file: {file_path}")
        
        if missing_files:
            print(f"❌ Missing {len(missing_files)} required files")
            for file in missing_files:
                print(f"   - {file}")
            return False
        
        print(f"✅ All {len(required_files)} required files present")
        return True
    
    def analyze_test_files(self) -> Dict[str, Any]:
        """Analyze test files and collect statistics."""
        test_files = []
        for root, dirs, files in os.walk(self.tests_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(Path(root) / file)
        
        self.stats['test_files'] = len(test_files)
        self.stats['total_files'] = len(list(self.tests_dir.rglob('*.py')))
        
        for test_file in test_files:
            self._analyze_test_file(test_file)
        
        return self.stats
    
    def _analyze_test_file(self, test_file: Path) -> None:
        """Analyze a single test file."""
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location("test_module", test_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Count test methods
                test_methods = []
                for name, obj in inspect.getmembers(module):
                    if (inspect.isfunction(obj) or inspect.ismethod(obj)) and name.startswith('test_'):
                        test_methods.append(name)
                
                # Categorize by directory
                if 'unit' in str(test_file):
                    self.stats['unit_tests'] += len(test_methods)
                elif 'integration' in str(test_file):
                    self.stats['integration_tests'] += len(test_methods)
                elif 'functional' in str(test_file):
                    self.stats['functional_tests'] += len(test_methods)
                
                self.stats['total_test_methods'] += len(test_methods)
                
        except Exception as e:
            self.warnings.append(f"Could not analyze {test_file}: {e}")
    
    def verify_fixtures(self) -> bool:
        """Verify that required fixtures are present in conftest.py."""
        conftest_path = self.tests_dir / 'conftest.py'
        if not conftest_path.exists():
            self.issues.append("conftest.py not found")
            return False
        
        try:
            with open(conftest_path, 'r') as f:
                content = f.read()
            
            required_fixtures = [
                'test_config',
                'clean_config', 
                'duckdb_manager',
                'lancedb_memory',
                'sample_world_state',
                'sample_terrain',
                'sample_memory_data'
            ]
            
            missing_fixtures = []
            for fixture in required_fixtures:
                if f"def {fixture}" not in content:
                    missing_fixtures.append(fixture)
                    self.issues.append(f"Missing fixture: {fixture}")
            
            if missing_fixtures:
                print(f"❌ Missing {len(missing_fixtures)} fixtures in conftest.py")
                for fixture in missing_fixtures:
                    print(f"   - {fixture}")
                return False
            
            print(f"✅ All {len(required_fixtures)} required fixtures present in conftest.py")
            return True
            
        except Exception as e:
            self.issues.append(f"Error reading conftest.py: {e}")
            return False
    
    def verify_test_utilities(self) -> bool:
        """Verify that test utilities are present."""
        test_config_path = self.tests_dir / 'test_config.py'
        if not test_config_path.exists():
            self.issues.append("test_config.py not found")
            return False
        
        try:
            with open(test_config_path, 'r') as f:
                content = f.read()
            
            required_classes = [
                'TestDataFactory',
                'TestConfigHelper',
                'TestDatabaseHelper',
                'TestMemoryHelper',
                'TestSpatialHelper',
                'TestEngineHelper',
                'TestValidationHelper',
                'TestPerformanceHelper',
                'TestAsyncHelper'
            ]
            
            missing_classes = []
            for class_name in required_classes:
                if f"class {class_name}" not in content:
                    missing_classes.append(class_name)
                    self.issues.append(f"Missing utility class: {class_name}")
            
            if missing_classes:
                print(f"❌ Missing {len(missing_classes)} utility classes in test_config.py")
                for class_name in missing_classes:
                    print(f"   - {class_name}")
                return False
            
            print(f"✅ All {len(required_classes)} utility classes present in test_config.py")
            return True
            
        except Exception as e:
            self.issues.append(f"Error reading test_config.py: {e}")
            return False
    
    def verify_pytest_compatibility(self) -> bool:
        """Verify that tests are compatible with pytest."""
        test_files = list(self.tests_dir.glob('**/test_*.py'))
        incompatible_files = []
        
        for test_file in test_files:
            try:
                with open(test_file, 'r') as f:
                    content = f.read()
                
                # Check for pytest-specific patterns
                has_pytest_imports = any(pattern in content for pattern in ['import pytest', 'from pytest'])
                has_test_functions = 'def test_' in content
                has_fixtures = '@pytest.fixture' in content or 'def ' in content and 'fixture' in content
                
                if not (has_pytest_imports or has_test_functions or has_fixtures):
                    incompatible_files.append(test_file)
                    self.warnings.append(f"File may not be pytest-compatible: {test_file}")
                
            except Exception as e:
                self.warnings.append(f"Could not analyze {test_file}: {e}")
        
        if incompatible_files:
            print(f"⚠️  Found {len(incompatible_files)} potentially incompatible files")
            return False
        
        print("✅ All test files appear to be pytest-compatible")
        return True
    
    def verify_test_coverage(self) -> bool:
        """Verify that tests cover the main components."""
        coverage_issues = []
        
        # Check if we have tests for main components
        main_components = {
            'schemas': self.tests_dir / 'unit' / 'test_schemas.py',
            'spatial_math': self.tests_dir / 'unit' / 'test_spatial_math.py',
            'duckdb': self.tests_dir / 'integration' / 'test_duckdb.py',
            'memory': self.tests_dir / 'integration' / 'test_memory.py',
            'engine': self.tests_dir / 'integration' / 'test_engine.py',
            'seeding': self.tests_dir / 'functional' / 'test_seeding_pipeline.py'
        }
        
        missing_components = []
        for component, file_path in main_components.items():
            if not file_path.exists():
                missing_components.append(component)
                coverage_issues.append(f"Missing tests for {component}")
        
        if missing_components:
            print(f"❌ Missing tests for {len(missing_components)} main components")
            for component in missing_components:
                print(f"   - {component}")
            return False
        
        print(f"✅ Tests cover all {len(main_components)} main components")
        return True
    
    def generate_report(self) -> str:
        """Generate a comprehensive test suite report."""
        report = []
        report.append("=" * 60)
        report.append("PyScrAI Universalis Test Suite Verification Report")
        report.append("=" * 60)
        report.append("")
        
        # Statistics
        report.append("📊 Test Suite Statistics:")
        report.append(f"   Total Python files: {self.stats['total_files']}")
        report.append(f"   Test files: {self.stats['test_files']}")
        report.append(f"   Unit tests: {self.stats['unit_tests']}")
        report.append(f"   Integration tests: {self.stats['integration_tests']}")
        report.append(f"   Functional tests: {self.stats['functional_tests']}")
        report.append(f"   Total test methods: {self.stats['total_test_methods']}")
        report.append("")
        
        # Issues
        if self.issues:
            report.append("❌ Issues Found:")
            for issue in self.issues:
                report.append(f"   - {issue}")
            report.append("")
        else:
            report.append("✅ No critical issues found!")
            report.append("")
        
        # Warnings
        if self.warnings:
            report.append("⚠️  Warnings:")
            for warning in self.warnings:
                report.append(f"   - {warning}")
            report.append("")
        
        # Recommendations
        report.append("💡 Recommendations:")
        report.append("   1. Run 'pytest pyscrai/tests/ --cov=pyscrai' to check coverage")
        report.append("   2. Run 'pytest pyscrai/tests/ -v' to execute all tests")
        report.append("   3. Consider adding performance benchmarks for large datasets")
        report.append("   4. Add integration tests for LLM provider mocking")
        report.append("   5. Consider adding property-based tests with hypothesis")
        report.append("")
        
        # Test Pyramid Verification
        report.append("🏗️  Test Pyramid Verification:")
        if self.stats['unit_tests'] > self.stats['integration_tests'] > self.stats['functional_tests']:
            report.append("   ✅ Test pyramid structure is correct (Unit > Integration > Functional)")
        else:
            report.append("   ⚠️  Test pyramid may need adjustment")
            report.append(f"      Unit: {self.stats['unit_tests']}, Integration: {self.stats['integration_tests']}, Functional: {self.stats['functional_tests']}")
        report.append("")
        
        report.append("=" * 60)
        report.append("End of Report")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def run_verification(self) -> bool:
        """Run the complete verification process."""
        print("🔍 Starting test suite verification...")
        print("")
        
        # Run all verification steps
        structure_ok = self.verify_structure()
        fixtures_ok = self.verify_fixtures()
        utilities_ok = self.verify_test_utilities()
        pytest_ok = self.verify_pytest_compatibility()
        coverage_ok = self.verify_test_coverage()
        stats = self.analyze_test_files()
        
        print("")
        print("📈 Test Statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        print("")
        
        # Generate report
        report = self.generate_report()
        print(report)
        
        # Return overall success
        return all([structure_ok, fixtures_ok, utilities_ok, pytest_ok, coverage_ok])


def main():
    """Main entry point for test suite verification."""
    tests_dir = Path(__file__).parent
    
    verifier = TestSuiteVerifier(tests_dir)
    success = verifier.run_verification()
    
    if success:
        print("🎉 Test suite verification completed successfully!")
        sys.exit(0)
    else:
        print("⚠️  Test suite verification found issues that should be addressed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
