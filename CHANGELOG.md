# Changelog

## [1.0.0](https://github.com/christianhbye/mockserial/compare/v0.0.1...v1.0.0) (2026-03-25)


### ⚠ BREAKING CHANGES

* write() now raises SerialException instead of RuntimeError. Code catching RuntimeError specifically will need updating. The `peer` parameter is now keyword-only.
* in_waiting is now a property. Callers using `obj.in_waiting()` with parentheses will get TypeError (calling an int). Change to `obj.in_waiting` (no parens) to match pySerial's API.

### Features

* add optional baud-rate timing simulation on flush/write ([82ca4e7](https://github.com/christianhbye/mockserial/commit/82ca4e7ef6dabfae9d5d9b1c84d842619bee78cf))
* expose __version__ from package metadata ([edda3a7](https://github.com/christianhbye/mockserial/commit/edda3a7ed1b23c4b8258673383c3d5e070a40509))
* match pySerial Serial API (constructor, exceptions, context manager, thread-safe close) ([fdd0f0d](https://github.com/christianhbye/mockserial/commit/fdd0f0de522422e559484450640b829cdbf26574))
* modernize Python packaging infrastructure ([0800145](https://github.com/christianhbye/mockserial/commit/08001457df9e8c5ac9f3a818fa780b211cf24e82))


### Bug Fixes

* make in_waiting a property, fix read/readline thread-safety and timeout ([a90b1e5](https://github.com/christianhbye/mockserial/commit/a90b1e55d55b01c5ba5daa2b63f7133f5e0618bc))
* skip codecov uploads for dependabot PRs ([d5b2114](https://github.com/christianhbye/mockserial/commit/d5b21144bc279a932e77f871850ff18b10536677))
