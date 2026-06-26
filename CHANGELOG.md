# Changelog

## v0.2.0

**Release Date:** 2026-06-26

### 🔍 Code Review & Quality Assurance

- **Comprehensive codebase audit** completed covering security, performance, and maturity
- **Security Review:** 5 findings identified (2 critical, 3 high/medium) — fixes planned for v0.3.0
- **Performance Analysis:** Identified optimization opportunities (parallelization, caching)
- **Maturity Assessment:** Code score 5.2/10 → Roadmap for Production-Ready status by Q3 2026

### 🚀 Improvements

- **GitLab CI/CD Pipeline:** Added automatic changelog generation on SemVer tag releases
- **Error Handling:** Improved error output and debugging visibility in changelog pipeline
- **Logging:** Added progress indicators in CI/CD jobs for better observability

### 📚 Documentation

- Comprehensive `.reviews/` structure created with detailed findings and recommendations
- Security review documented with actionable fixes
- Performance optimization roadmap documented

### ⚠️ Known Issues

- **2 Critical Security Findings** pending implementation (v0.3.0):
  - Path traversal in convert.py
  - Text DoS vulnerability in render.py
- See `.reviews/` for full audit details and fix recommendations

### 🔧 Technical Notes

- Minimum Python 3.9+ required
- CUDA 12.8 for GPU, CPU-only fallback supported (future release)
- All code follows MIT license terms

---

## v0.1

Initial release with core TTS rendering pipeline.
