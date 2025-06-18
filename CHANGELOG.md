# Changelog

## [0.4.0](https://github.com/gmc-norr/st2-seqdata/compare/v0.3.1...v0.4.0) (2025-06-18)


### Features

* properly detect moved analysis directories ([#71](https://github.com/gmc-norr/st2-seqdata/issues/71)) ([b6c7612](https://github.com/gmc-norr/st2-seqdata/commit/b6c7612c3dc8eebfa0bd4b3953dbbf6575bc95ec))

## [0.3.1](https://github.com/gmc-norr/st2-seqdata/compare/v0.3.0...v0.3.1) (2025-04-22)


### Bug Fixes

* update platform names to match cleve ([#65](https://github.com/gmc-norr/st2-seqdata/issues/65)) ([5e791f8](https://github.com/gmc-norr/st2-seqdata/commit/5e791f809489951a6ef1c9da07cb2cc25e81248a))

## [0.3.0](https://github.com/gmc-norr/st2-seqdata/compare/v0.2.0...v0.3.0) (2025-01-20)


### Features

* copy interop to shared drive ([#61](https://github.com/gmc-norr/st2-seqdata/issues/61)) ([99db947](https://github.com/gmc-norr/st2-seqdata/commit/99db9479f8f2cdbedb9c31b569e087093080181e))


### Bug Fixes

* copy_interop timeout increased ([#63](https://github.com/gmc-norr/st2-seqdata/issues/63)) ([002e0ee](https://github.com/gmc-norr/st2-seqdata/commit/002e0ee33c89a04dfb84d974a537dcc101836fc7))
* Make timeout argument longer. ([#64](https://github.com/gmc-norr/st2-seqdata/issues/64)) ([5e8298b](https://github.com/gmc-norr/st2-seqdata/commit/5e8298b4e1863e8f2c929c869c8d22ed2961d729))

## [0.2.0](https://github.com/gmc-norr/st2-seqdata/compare/v0.1.2...v0.2.0) (2024-10-01)

This release is an update in order to match the cleve API changes that were introduced in v0.3.0.
As a consequence, this release is not compatible with cleve < v0.3.0.

### Features

* adapt to cleve API changes ([#58](https://github.com/gmc-norr/st2-seqdata/issues/58)) ([f5e4aff](https://github.com/gmc-norr/st2-seqdata/commit/f5e4affcc496597d06d648a49b96a66c80ee3c70))

## [0.1.2](https://github.com/gmc-norr/st2-seqdata/compare/v0.1.1...v0.1.2) (2024-09-30)


### Bug Fixes

* don't try to update run path if it is missing ([#56](https://github.com/gmc-norr/st2-seqdata/issues/56)) ([55e2b31](https://github.com/gmc-norr/st2-seqdata/commit/55e2b314ed198668a849224179f8627084382ead))

## [0.1.1](https://github.com/gmc-norr/st2-seqdata/compare/v0.1.0...v0.1.1) (2024-09-27)


### Bug Fixes

* check that watch directory exists ([c797388](https://github.com/gmc-norr/st2-seqdata/commit/c797388c770236e8bd885b3772246f25f36ce369))
* correct brief query parameter ([9f2de22](https://github.com/gmc-norr/st2-seqdata/commit/9f2de22884d46fe7d9607ef445bc8ab8a24cfd1a))
* handle state change with a workflow ([#55](https://github.com/gmc-norr/st2-seqdata/issues/55)) ([c3f2bc3](https://github.com/gmc-norr/st2-seqdata/commit/c3f2bc3e68863703ba716991edd5a0c852f014e8))

## 0.1.0 (2024-09-05)


### Features

* activate the Illumina directory sensor ([#13](https://github.com/gmc-norr/st2-seqdata/issues/13)) ([588457a](https://github.com/gmc-norr/st2-seqdata/commit/588457ac7b310c2167a483c8697a4692b678197f))
* add analysis directory sensor ([#5](https://github.com/gmc-norr/st2-seqdata/issues/5)) ([62c6c94](https://github.com/gmc-norr/st2-seqdata/commit/62c6c94f2b30ae588eba749fef74644b38af7af9))
* add handling for samplesheets ([#35](https://github.com/gmc-norr/st2-seqdata/issues/35)) ([78df442](https://github.com/gmc-norr/st2-seqdata/commit/78df4420f64944746f577f47f49b3a231b3d8332))
* add rule and action for updating run path ([#32](https://github.com/gmc-norr/st2-seqdata/issues/32)) ([d4c171c](https://github.com/gmc-norr/st2-seqdata/commit/d4c171cd8a6076e18e47995e2b5ab8a2554fb55a))
* add rules and actions for handling sequencing runs ([#10](https://github.com/gmc-norr/st2-seqdata/issues/10)) ([9dd4659](https://github.com/gmc-norr/st2-seqdata/commit/9dd46590045439c02635fef19d085e9bf71cd652))
* add run directory sensor ([#1](https://github.com/gmc-norr/st2-seqdata/issues/1)) ([250474c](https://github.com/gmc-norr/st2-seqdata/commit/250474c53c9cd9a31e2f1a60f62cd52fa5cd993a))
* conform cleve service to API update ([#26](https://github.com/gmc-norr/st2-seqdata/issues/26)) ([bc41120](https://github.com/gmc-norr/st2-seqdata/commit/bc4112051b5e1610a7c700e6090c41916e64e0a0))
* detect duplicate runs ([#37](https://github.com/gmc-norr/st2-seqdata/issues/37)) ([aa6d28e](https://github.com/gmc-norr/st2-seqdata/commit/aa6d28ed61a880b0e5c0e6beb930b092b296faeb))
* rule and action for adding run qc ([#25](https://github.com/gmc-norr/st2-seqdata/issues/25)) ([79f3aef](https://github.com/gmc-norr/st2-seqdata/commit/79f3aef71f8b7bfe30ea1c9a01eafb8b6089d576))
* supply run info when adding a new run ([#22](https://github.com/gmc-norr/st2-seqdata/issues/22)) ([3e49c7c](https://github.com/gmc-norr/st2-seqdata/commit/3e49c7cab1cea14cf52b443050ae3e1c02aab8cf))
* use cleve for tracking run directory states ([#9](https://github.com/gmc-norr/st2-seqdata/issues/9)) ([b75eb31](https://github.com/gmc-norr/st2-seqdata/commit/b75eb315d736421868d2cddca63df1b89b85a3b3))


### Bug Fixes

* add brief flag when fetching runs ([#12](https://github.com/gmc-norr/st2-seqdata/issues/12)) ([04d4e37](https://github.com/gmc-norr/st2-seqdata/commit/04d4e370979b8f6ccf183c757243efeeb0326203))
* add run action issues ([#24](https://github.com/gmc-norr/st2-seqdata/issues/24)) ([c4a7668](https://github.com/gmc-norr/st2-seqdata/commit/c4a76688450230acbd4bfdea1b30ed972522f2bd))
* assume that protocol is included for host ([#42](https://github.com/gmc-norr/st2-seqdata/issues/42)) ([efb1811](https://github.com/gmc-norr/st2-seqdata/commit/efb181122b908c63dbaae629350ad1a229fbd6d4))
* catch ValueErrors when extracting run ID ([#15](https://github.com/gmc-norr/st2-seqdata/issues/15)) ([6e1640c](https://github.com/gmc-norr/st2-seqdata/commit/6e1640cfbcfa6df1ef05bd33d117a4adff44e246))
* conform add_run to API changes ([#28](https://github.com/gmc-norr/st2-seqdata/issues/28)) ([d3dae52](https://github.com/gmc-norr/st2-seqdata/commit/d3dae5268481509f2658279a32c139a6f63932b3))
* correct content type when updating run state ([04d4e37](https://github.com/gmc-norr/st2-seqdata/commit/04d4e370979b8f6ccf183c757243efeeb0326203))
* correct page size parameter ([#27](https://github.com/gmc-norr/st2-seqdata/issues/27)) ([775bee4](https://github.com/gmc-norr/st2-seqdata/commit/775bee4b928c39dd421b3dc7ffa1f74f344ba1c4))
* correct url parameters for get request ([#23](https://github.com/gmc-norr/st2-seqdata/issues/23)) ([488052f](https://github.com/gmc-norr/st2-seqdata/commit/488052fdbc54f5fe9c7b6e051fe596075f958e34))
* correct URLs in exceptions ([04d4e37](https://github.com/gmc-norr/st2-seqdata/commit/04d4e370979b8f6ccf183c757243efeeb0326203))
* detect both `"RunId"` and `"RunID"` ([6e1640c](https://github.com/gmc-norr/st2-seqdata/commit/6e1640cfbcfa6df1ef05bd33d117a4adff44e246))
* directory state check ([#6](https://github.com/gmc-norr/st2-seqdata/issues/6)) ([0e972fc](https://github.com/gmc-norr/st2-seqdata/commit/0e972fc727c3b309d75f2facf3eb7310dd4a7835))
* don't emit duplicate run triggers too frequently ([#38](https://github.com/gmc-norr/st2-seqdata/issues/38)) ([27b0dbb](https://github.com/gmc-norr/st2-seqdata/commit/27b0dbbf57d0fb2e458094090616b8bba00836f5))
* don't emit multiple state changes when moved ([22c0a00](https://github.com/gmc-norr/st2-seqdata/commit/22c0a00ac02e3d78d5ac4a7a7f352cb6fac6484b))
* don't make path required for state change ([#20](https://github.com/gmc-norr/st2-seqdata/issues/20)) ([2d8ef5d](https://github.com/gmc-norr/st2-seqdata/commit/2d8ef5d695e0d821fd48a9653cdcf4e4d45b84ce))
* get run status from RunCompletionStatus.xml ([#41](https://github.com/gmc-norr/st2-seqdata/issues/41)) ([a9be505](https://github.com/gmc-norr/st2-seqdata/commit/a9be5051788bcc3d46682c122abb97c798d5d049))
* incorrect arguments for analysis update ([b794c89](https://github.com/gmc-norr/st2-seqdata/commit/b794c89903ddc03e144e2df7669ae3d26e7e5ffe))
* incorrect call to update_analysis action ([#44](https://github.com/gmc-norr/st2-seqdata/issues/44)) ([b15ff76](https://github.com/gmc-norr/st2-seqdata/commit/b15ff7631a6c71fab55aed66bc38a9f0ae38523e))
* incorrect parameters passed to requests.patch ([#45](https://github.com/gmc-norr/st2-seqdata/issues/45)) ([15b8950](https://github.com/gmc-norr/st2-seqdata/commit/15b8950f5e8d0bd0872a2847d26a6239119d9376))
* mismatched parameters ([#43](https://github.com/gmc-norr/st2-seqdata/issues/43)) ([01b4fdd](https://github.com/gmc-norr/st2-seqdata/commit/01b4fdd52e8bd0711753b256f067342572865788))
* pass analysis id from trigger to action ([#33](https://github.com/gmc-norr/st2-seqdata/issues/33)) ([33c9007](https://github.com/gmc-norr/st2-seqdata/commit/33c90072d22a9d943a4a3b935fca7410db95af92)), closes [#29](https://github.com/gmc-norr/st2-seqdata/issues/29)
* run IDs not extracted properly ([#17](https://github.com/gmc-norr/st2-seqdata/issues/17)) ([90affd7](https://github.com/gmc-norr/st2-seqdata/commit/90affd764a4fdee3dd70c7a5f189da3a5f3aa006))
* samplesheet modification timestamp in UTC ([#40](https://github.com/gmc-norr/st2-seqdata/issues/40)) ([57b31db](https://github.com/gmc-norr/st2-seqdata/commit/57b31db2190e8569220e261c1842d6bd95ba6816))
* time zone issue with sample sheet update ([#48](https://github.com/gmc-norr/st2-seqdata/issues/48)) ([3fd7d26](https://github.com/gmc-norr/st2-seqdata/commit/3fd7d261f64931d2ca0661b149b7eec60bc66fe7))
* typo in `update_samplesheet` metadata ([#39](https://github.com/gmc-norr/st2-seqdata/issues/39)) ([ddfc9ab](https://github.com/gmc-norr/st2-seqdata/commit/ddfc9ab46dccbe4e9406c200a181ca3334eeab4d))
* typo in NextSeq serial tag ([6e1640c](https://github.com/gmc-norr/st2-seqdata/commit/6e1640cfbcfa6df1ef05bd33d117a4adff44e246))
* update sample sheet if the registered file is missing ([#49](https://github.com/gmc-norr/st2-seqdata/issues/49)) ([d06f019](https://github.com/gmc-norr/st2-seqdata/commit/d06f01926195c36866dd74db668739a5e1133f57))
* update state even if history is empty ([7b44649](https://github.com/gmc-norr/st2-seqdata/commit/7b446499bf41f74626ed975c80e5d38f95168880))
