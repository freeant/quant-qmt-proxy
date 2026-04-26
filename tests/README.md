# Tests

The maintained test surface is `tests/unit`.

Default runs are local-only and use the in-process `mock` environment. Real xtquant tests are opt-in and split into:

- `mock`: local fake data and fake order flow
- `dev`: real xtquant + explicitly registered simulated account
- `prod`: real xtquant + explicitly registered real account, but automated tests remain readonly

## Default local run

```powershell
.venv\Scripts\python.exe -m pytest -q
```

or

```powershell
.venv\Scripts\python.exe -m pytest tests/unit -q
```

## Real-environment prerequisites

Create an untracked local file named `config.test.local.yml` based on `config.test.local.example.yml`.

`config.local.yml` is for normal runtime startup. `config.test.local.yml` is test-only and is read explicitly by the pytest fixture layer.

The file is used for:

- `testing.default_account_profile`
- `testing.enable_prod_readonly_tests`
- `testing.prod_unlock_token`
- `testing.qmt_userdata_path`
- `xtquant.trading.accounts`

Account profiles must be registered explicitly:

- `dev` tests require `account_kind: simulated`
- `prod` tests require `account_kind: real`
- both must be `enabled: true`

## Pytest options

```powershell
pytest -q `
  --xt-mode=dev `
  --xt-account-profile=sim-dev `
  --xt-enable-live-streams
```

Available options:

- `--xt-mode=mock|dev|prod`
- `--xt-account-profile=...`
- `--xt-qmt-userdata-path=...`
- `--xt-api-key=...`
- `--xt-enable-live-streams`
- `--xt-enable-prod-tests`

## Environment variables

Equivalent environment variables are supported:

- `QMT_TEST_MODE`
- `QMT_TEST_ACCOUNT_PROFILE`
- `QMT_TEST_QMT_USERDATA_PATH`
- `QMT_TEST_API_KEY`
- `QMT_TEST_ENABLE_LIVE_STREAMS`
- `QMT_TEST_ENABLE_PROD_TESTS`
- `QMT_TEST_PROD_UNLOCK_TOKEN`

## Safety defaults

- Default mode is `mock`
- `dev` and `prod` tests are skipped unless a valid local config and matching account profile exist
- Live streaming tests are skipped in real mode unless `--xt-enable-live-streams` is enabled
- `prod` readonly tests require all three:
  - `testing.enable_prod_readonly_tests: true` in `config.test.local.yml`
  - `--xt-enable-prod-tests`
  - `QMT_TEST_PROD_UNLOCK_TOKEN` matching `testing.prod_unlock_token`
- Automated `prod` tests never place real orders
- `SubmitStockOrder` and `CancelStockOrder` in `prod` are asserted as rejected by the safety gate
- This readonly rule only applies to pytest. Real deployed `prod` traffic can still place orders when `xtquant.trading.enable_prod_orders=true`

## Covered interfaces

`tests/unit` covers the maintained interface set:

- REST data endpoints
- REST trading endpoints
- REST health endpoints and root endpoint
- REST auth failure paths
- WebSocket quote and whole-quote subscription consumption
- WebSocket token and unknown-subscription rejection paths
- gRPC data RPCs
- gRPC trading RPCs
- gRPC health check
- gRPC auth failure paths for unary and streaming RPCs
- gRPC trading event stream
- configuration/runtime bootstrap paths
- interface inventory checks for FastAPI and gRPC method coverage

## Notes

- Real xtquant validation still depends on your local QMT machine state.
- Mock mode is the only mode guaranteed in CI/local default runs.
- Legacy `tests/rest` and `tests/grpc` suites were removed; the default collection target is only `tests/unit`.
