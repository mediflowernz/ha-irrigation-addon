# Irrigation Addon Tests

This directory contains comprehensive tests for the Home Assistant Irrigation Addon integration.

## Test Structure

### Unit Tests (`test_models.py`)
Tests for core data models and validation:
- **Shot** class validation and functionality
- **IrrigationEvent** class validation and functionality  
- **Room** class validation and functionality
- Data serialization/deserialization
- Input validation and error handling

### Coordinator Tests (`test_coordinator.py`)
Tests for the main coordination logic:
- Coordinator initialization and setup
- Room management (add, update, delete)
- Settings management
- Fail-safe mechanisms
- Hardware control (pump/zone activation)
- System health monitoring
- Emergency stop functionality

### Configuration Flow Tests (`test_config_flow.py`)
Tests for Home Assistant configuration flow:
- Initial setup flow
- Settings configuration
- Room management through UI
- Entity validation
- Options flow functionality

### Storage Tests (`test_storage.py`)
Tests for data persistence and storage:
- Data loading and saving
- Room data management
- Settings persistence
- History tracking
- Performance metrics
- Backup and restore functionality
- Data migration

### Integration Tests (`test_integration.py`)
End-to-end integration tests:
- Complete irrigation cycles
- Home Assistant entity integration
- Fail-safe scenario testing
- System health monitoring
- Real-world workflow testing

### Frontend Tests (`test_frontend.py`)
Tests for web panel functionality:
- HTML structure validation
- CSS responsive design
- JavaScript component testing
- UI component rendering
- Real-time update functionality
- User workflow validation
- Accessibility compliance

## Running Tests

### Prerequisites
```bash
pip install -r tests/requirements.txt
```

### Using pytest (Recommended)
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_models.py -v

# Run with coverage
pytest tests/ --cov=custom_components.irrigation_addon

# Run integration tests only
pytest tests/test_integration.py -v
```

### Using the validation script
```bash
python validate_tests.py
```

## Test Coverage

The tests cover the following requirements from the specification:

### Core Functionality (Requirements 1-8)
- ✅ Room management and configuration
- ✅ Pump and zone control with proper sequencing
- ✅ P1/P2 event creation and execution
- ✅ Real-time sensor data monitoring
- ✅ Manual run capabilities with timer control
- ✅ Irrigation history and event tracking
- ✅ Settings configuration and persistence
- ✅ Light schedule integration and fail-safes

### User Interface (Requirement 9)
- ✅ Professional web interface structure
- ✅ Real-time status indicators
- ✅ Drag-and-drop shot reordering (structure validation)
- ✅ Progress indicators during irrigation
- ✅ Responsive design across devices

### Installation and Integration (Requirement 10)
- ✅ Home Assistant custom integration structure
- ✅ HACS compatibility
- ✅ Proper manifest configuration
- ✅ Integration setup and teardown

## Test Categories

### 1. Unit Tests
Focus on individual components in isolation:
- Data model validation
- Business logic correctness
- Input/output validation
- Error handling

### 2. Integration Tests  
Test component interactions:
- Complete irrigation workflows
- Entity state management
- Service call integration
- Data persistence flows

### 3. Frontend Tests
Validate user interface:
- Component structure
- Responsive design
- User interaction flows
- Real-time updates

### 4. Fail-Safe Tests
Ensure safety mechanisms:
- Light schedule conflicts
- Entity availability checks
- Over-watering prevention
- Emergency stop procedures

## Mock Strategy

Tests use comprehensive mocking to isolate components:

- **Home Assistant Core**: Mocked `hass` object with states and services
- **Entity Registry**: Mocked entity validation and lookup
- **Storage**: Mocked file system operations
- **Time/Scheduling**: Mocked datetime and async scheduling
- **Hardware Control**: Mocked switch/sensor entity interactions

## Continuous Integration

Tests are designed to run in CI environments:
- No external dependencies required
- Deterministic test execution
- Comprehensive error reporting
- Performance benchmarking capabilities

## Adding New Tests

When adding new functionality:

1. **Unit Tests**: Add to appropriate `test_*.py` file
2. **Integration Tests**: Add end-to-end scenarios to `test_integration.py`
3. **Frontend Tests**: Add UI validation to `test_frontend.py`
4. **Update Documentation**: Update this README with new test coverage

### Test Naming Convention
- Test classes: `TestComponentName`
- Test methods: `test_specific_functionality`
- Fixtures: `mock_component_name` or `sample_data_name`

### Assertion Guidelines
- Use descriptive assertion messages
- Test both positive and negative cases
- Validate error conditions and edge cases
- Ensure proper cleanup in async tests

## Performance Testing

Some tests include performance validation:
- Coordinator setup time
- Data loading/saving performance
- Memory usage during irrigation cycles
- Response time for UI operations

## Security Testing

Tests validate security aspects:
- Input sanitization
- Entity access control
- Configuration validation
- Error message safety (no sensitive data exposure)

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `custom_components` is in Python path
2. **Async Test Failures**: Use `pytest-asyncio` plugin
3. **Mock Issues**: Verify mock objects match expected interfaces
4. **File Not Found**: Some frontend tests skip if files don't exist

### Debug Mode
Run tests with verbose output:
```bash
pytest tests/ -v -s --tb=long
```

### Test Isolation
Each test is designed to be independent:
- No shared state between tests
- Proper setup and teardown
- Isolated mock environments