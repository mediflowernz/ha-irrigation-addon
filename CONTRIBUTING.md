# Contributing to Home Assistant Irrigation Addon

Thank you for your interest in contributing to the Home Assistant Irrigation Addon! This project aims to provide professional-grade irrigation control for cannabis cultivation and other hydroponic systems.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Home Assistant 2023.1.0 or higher
- Basic understanding of Home Assistant custom integrations
- Knowledge of irrigation systems and automation

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/mediflowernz/ha-irrigation-addon.git
   cd ha-irrigation-addon
   ```

2. **Install development dependencies**
   ```bash
   pip install -r tests/requirements.txt
   ```

3. **Run tests to verify setup**
   ```bash
   python run_all_tests.py
   ```

## Development Guidelines

### Code Style

- Follow PEP 8 Python style guidelines
- Use type hints for all function parameters and return values
- Write descriptive docstrings for all classes and methods
- Keep functions focused and single-purpose

### Testing

- Write tests for all new functionality
- Ensure all existing tests pass before submitting
- Include both unit tests and integration tests
- Test fail-safe mechanisms thoroughly

### Documentation

- Update documentation for any new features
- Include configuration examples
- Document any breaking changes
- Keep README.md up to date

## Types of Contributions

### Bug Reports

When reporting bugs, please include:

- Home Assistant version
- Integration version
- Detailed steps to reproduce
- Expected vs actual behavior
- Relevant log entries
- Hardware configuration details

### Feature Requests

For new features, please provide:

- Clear description of the feature
- Use case and benefits
- Proposed implementation approach
- Compatibility considerations

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow coding standards
   - Add appropriate tests
   - Update documentation

4. **Test your changes**
   ```bash
   python run_all_tests.py
   python validate_tests.py
   ```

5. **Commit your changes**
   ```bash
   git commit -m "Add feature: your feature description"
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request**

## Pull Request Guidelines

### Before Submitting

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No merge conflicts

### Pull Request Description

Include:

- Summary of changes
- Related issue numbers
- Testing performed
- Breaking changes (if any)
- Screenshots (for UI changes)

## Code Review Process

1. **Automated Checks**: All PRs run automated tests
2. **Code Review**: Maintainers review code quality and design
3. **Testing**: Changes are tested in real environments
4. **Approval**: At least one maintainer approval required
5. **Merge**: Squash and merge to main branch

## Development Areas

### Core Components

- **Models**: Data structures and validation
- **Coordinator**: Main orchestration logic
- **Storage**: Data persistence and history
- **Config Flow**: Home Assistant integration setup
- **Services**: Home Assistant service definitions

### Frontend Components

- **Web Panel**: React-based irrigation dashboard
- **Real-time Updates**: WebSocket integration
- **Mobile Responsive**: Touch-friendly interface
- **Accessibility**: Screen reader and keyboard support

### Safety Systems

- **Fail-safes**: Over-watering prevention
- **Entity Validation**: Hardware availability checks
- **Emergency Stop**: Immediate system shutdown
- **Error Recovery**: Graceful error handling

## Testing Strategy

### Unit Tests
- Individual component testing
- Data model validation
- Business logic verification

### Integration Tests
- End-to-end workflows
- Home Assistant integration
- Hardware control sequences

### Frontend Tests
- UI component rendering
- User interaction flows
- Responsive design validation

## Release Process

1. **Version Bump**: Update version in manifest.json
2. **Changelog**: Update CHANGELOG.md
3. **Testing**: Full test suite execution
4. **Documentation**: Update installation guides
5. **Release**: Create GitHub release with notes

## Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help newcomers learn and contribute
- Maintain professional communication

### Communication Channels

- **Issues**: Bug reports and feature requests
- **Discussions**: General questions and ideas
- **Pull Requests**: Code contributions and reviews

## Security

### Reporting Security Issues

Please report security vulnerabilities privately to:
- Email: [security contact]
- Do not create public issues for security problems

### Security Considerations

- Input validation and sanitization
- Safe handling of entity states
- Secure storage of configuration data
- Protection against injection attacks

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Recognition

Contributors are recognized in:
- CHANGELOG.md for significant contributions
- README.md contributors section
- GitHub contributors page

## Questions?

If you have questions about contributing:

1. Check existing issues and discussions
2. Review documentation thoroughly
3. Create a discussion for general questions
4. Create an issue for specific problems

Thank you for helping make irrigation automation better for everyone!