# PyScrAI Universalis Test Suite

This directory contains the comprehensive test suite for PyScrAI Universalis (GeoScrAI), following a "Testing Pyramid" approach with unit, integration, and functional tests.

## Test Structure

```text
pyscrai/tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Shared fixtures and configuration
├── test_config.py           # Test utilities and helpers
├── unit/                    # Fast, isolated unit tests
│   ├── __init__.py
│   ├── test_schemas.py      # Schema and model validation
│   └── test_spatial_math.py # Spatial calculations and utilities
├── integration/             # Real database integration tests
│   ├── __init__.py
│   ├── test_duckdb.py       # DuckDB state management
│   ├── test_memory.py       # LanceDB memory operations
│   └── test_engine.py       # Simulation engine functionality
└── functional/              # End-to-end workflow tests
    ├── __init__.py
    └── test_seeding_pipeline.py  # Complete seeding workflows
```

## Test Categories

### Unit Tests (`unit/`)
- **Purpose**: Fast, isolated tests for individual components
- **No I/O**: No database or external dependencies
- **Focus**: Data validation, serialization, business logic
- **Examples**:
  - Schema model validation and serialization
  - Spatial constraint calculations
  - Enum value validation
  - Data structure integrity

### Integration Tests (`integration/`)
- **Purpose**: Test component integration with real databases
- **Real Dependencies**: Uses actual DuckDB and LanceDB instances
- **Focus**: Database operations, spatial queries, memory management
- **Examples**:
  - DuckDB state persistence and retrieval
  - LanceDB semantic memory operations
  - Engine async operations and cycle management
  - Spatial query functionality

### Functional Tests (`functional/`)
- **Purpose**: End-to-end workflow testing
- **Complete Workflows**: Tests entire user journeys
- **Focus**: Seeding pipeline, simulation initialization, multi-cycle runs
- **Examples**:
  - Complete world building and seeding
  - Schema validation workflows
  - Multi-agent simulation scenarios
  - Performance testing with large datasets

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install pytest pytest-asyncio pytest-mock httpx
```

Ensure you have the required database dependencies:
```bash
pip install duckdb lancedb pyarrow
```

### Running All Tests

```bash
# Run all tests
pytest pyscrai/tests/

# Run with verbose output
pytest pyscrai/tests/ -v

# Run with coverage
pytest pyscrai/tests/ --cov=pyscrai --cov-report=html
```

### Running Specific Test Categories

```bash
# Unit tests only
pytest pyscrai/tests/unit/ -v

# Integration tests only
pytest pyscrai/tests/integration/ -v

# Functional tests only
pytest pyscrai/tests/functional/ -v
```

### Running Specific Test Files

```bash
# Run specific test file
pytest pyscrai/tests/unit/test_schemas.py -v

# Run specific test class
pytest pyscrai/tests/integration/test_duckdb.py::TestDuckDBStateManager -v

# Run specific test method
pytest pyscrai/tests/functional/test_seeding_pipeline.py::TestSeedingPipeline::test_complete_seeding_workflow -v
```

### Running Tests with Markers

```bash
# Run only unit tests (using pytest markers)
pytest pyscrai/tests/ -m "unit"

# Run only integration tests
pytest pyscrai/tests/ -m "integration"

# Run only functional tests
pytest pyscrai/tests/ -m "functional"
```

## Test Configuration

### Shared Fixtures (`conftest.py`)

The `conftest.py` file provides shared fixtures used across all test categories:

- **`test_config`**: Creates temporary test configuration with isolated directories
- **`clean_config`**: Provides clean config for each test
- **`duckdb_manager`**: Disposable DuckDB state manager for testing
- **`lancedb_memory`**: Disposable LanceDB memory bank for testing
- **`sample_world_state`**: Pre-built world state for testing
- **`sample_terrain`**: Sample terrain data for spatial tests
- **`sample_memory_data`**: Sample memory entries for memory tests

### Test Utilities (`test_config.py`)

The `test_config.py` file provides comprehensive test utilities:

- **`TestDataFactory`**: Creates test data (world states, actors, assets, terrain)
- **`TestConfigHelper`**: Provides test configuration helpers
- **`TestDatabaseHelper`**: Manages temporary database paths and cleanup
- **`TestMemoryHelper`**: Creates test memory data
- **`TestSpatialHelper`**: Spatial calculation and polygon creation utilities
- **`TestEngineHelper`**: Mock Archon creation for engine testing
- **`TestValidationHelper`**: World state and spatial data validation
- **`TestPerformanceHelper`**: Performance measurement and timeout utilities

## Test Data

### Sample World States

The test suite includes several sample world states for different testing scenarios:

- **`sample_world_state`**: Basic world state with 3 actors and 4 assets
- **`create_large_world_state`**: Large dataset for performance testing (50 actors, 100 assets)
- **Custom terrain examples**: Mountain, water, and urban terrain samples

### Test Coordinates

Common test coordinates are defined for consistent spatial testing:
- Los Angeles: 34.05, -118.25
- New York: 40.71, -74.01
- Chicago: 41.88, -87.63
- Houston: 29.76, -95.37

## Test Best Practices

### Unit Tests
- ✅ Test individual functions and methods in isolation
- ✅ Use mock objects to avoid external dependencies
- ✅ Focus on business logic and data validation
- ✅ Keep tests fast (under 100ms each)
- ❌ Don't use real databases or external services

### Integration Tests
- ✅ Use real database instances (DuckDB, LanceDB)
- ✅ Test component interactions
- ✅ Verify database schema and queries
- ✅ Test spatial operations with real coordinates
- ✅ Clean up resources after each test

### Functional Tests
- ✅ Test complete user workflows
- ✅ Use realistic test data and scenarios
- ✅ Verify end-to-end functionality
- ✅ Test error handling and edge cases
- ✅ Include performance benchmarks

### General Guidelines
- ✅ Use descriptive test names that explain the scenario
- ✅ Follow AAA pattern: Arrange, Act, Assert
- ✅ Use parametrized tests for multiple scenarios
- ✅ Clean up test data and resources
- ✅ Document complex test scenarios

## Mocking Strategy

### LLM Providers
- **Never make real API calls** during testing
- Use `MockLLMProvider` for consistent, fast responses
- Mock responses based on prompt content patterns
- Test prompt construction and response parsing separately

### Database Operations
- Use in-memory or temporary file databases
- Create disposable database instances for each test
- Clean up database files after tests complete
- Test both success and failure scenarios

### External Services
- Mock all external API calls
- Use `pytest-mock` for easy mocking
- Test error handling for service failures

## Performance Testing

The test suite includes performance benchmarks for:

- **Large dataset seeding**: 100+ actors and 200+ assets
- **Spatial query performance**: Complex geographic queries
- **Memory operations**: Large-scale semantic memory operations
- **Engine cycle performance**: Multi-cycle simulation runs

Performance thresholds:
- Seeding 300 entities: < 15 seconds
- Spatial queries: < 1 second
- Memory operations: < 5 seconds for 1000 memories
- Engine cycles: < 2 seconds per cycle

## Continuous Integration

### Test Execution Order
1. **Unit tests** (fastest, run first)
2. **Integration tests** (medium speed)
3. **Functional tests** (slowest, run last)

### Parallel Execution
Tests are designed to run in parallel using pytest-xdist:
```bash
pytest pyscrai/tests/ -n auto
```

### Coverage Requirements
- **Minimum coverage**: 80% overall
- **Unit tests**: 90%+ coverage
- **Integration tests**: 70%+ coverage
- **Functional tests**: 50%+ coverage

## Troubleshooting

### Common Issues

**Database Lock Errors**:
- Ensure proper cleanup in test fixtures
- Use unique database paths for parallel tests
- Check for lingering database connections

**Memory Leaks**:
- Always close database connections
- Clean up temporary files and directories
- Use context managers where possible

**Flaky Tests**:
- Avoid timing-dependent assertions
- Use appropriate timeouts for async operations
- Ensure test isolation

### Debugging Tips

1. **Run single test**: `pytest -v -s tests/file.py::TestClass::test_method`
2. **Enable logging**: Add `--log-cli-level=DEBUG` to pytest command
3. **Capture output**: Use `-s` flag to see print statements
4. **Step through**: Use `pytest --pdb` for interactive debugging

## Contributing to Tests

### Adding New Tests

1. **Choose appropriate category**: unit, integration, or functional
2. **Use existing fixtures**: Leverage shared fixtures in `conftest.py`
3. **Follow naming conventions**: `test_` prefix, descriptive names
4. **Add to appropriate directory**: Match test category structure
5. **Update documentation**: Add to this README if needed

### Test Categories Decision Tree

```
Is it testing a single function/method? → unit/
Does it need a real database? → integration/
Is it testing a complete workflow? → functional/
```

### Code Review Checklist

- [ ] Tests follow the testing pyramid structure
- [ ] Appropriate use of fixtures and mocks
- [ ] Clear, descriptive test names
- [ ] Proper cleanup of resources
- [ ] Error cases are tested
- [ ] Performance implications considered
- [ ] Documentation updated if needed

## Test Metrics

### Success Criteria

- **Unit tests**: < 100ms execution time
- **Integration tests**: < 5 seconds execution time
- **Functional tests**: < 30 seconds execution time
- **Overall suite**: < 5 minutes execution time

### Quality Metrics

- **Test coverage**: > 80% overall
- **Test reliability**: > 95% pass rate
- **Test maintainability**: Clear, well-documented tests
- **Test performance**: Fast feedback for developers

## Support

For questions about the test suite:
1. Check this README for common issues
2. Review existing test examples
3. Consult the pytest documentation
4. Ask in the project discussions

Happy testing! 🧪
