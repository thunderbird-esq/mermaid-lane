Run the full test suite and code quality checks for the IPTV project.

Steps:
1. Change to the iptv directory
2. Run `npm test` to execute the full Jest test suite (runs in --runInBand mode)
3. Run `npm run lint` to check code quality with ESLint
4. Analyze and report test results:
   - Number of test suites passed/failed
   - Number of individual tests passed/failed
   - Test coverage information if available
   - Any linting errors or warnings
5. If there are failures, provide details about:
   - Which tests failed and why
   - Stack traces for errors
   - Suggestions for fixing issues
6. Summarize overall test health

This command ensures code quality and that all functionality works as expected before committing changes.
