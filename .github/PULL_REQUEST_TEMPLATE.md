## Summary

- What does this PR change?
- Why is this change needed?

## Scope

- [ ] Filecraft-python implementation (`filecraft-python`)
- [ ] Filecraft-go implementation (`filecraft-go`)
- [ ] Docs/CI only

## Compatibility Parity

- [ ] Behavior is compatible across Python and Go implementations
- [ ] If parity is not included, rationale is documented below

Parity notes:

## Validation

### Python

- [ ] `poetry run black --check src tests`
- [ ] `poetry run python -m unittest discover -s tests -p "test_*.py"`

### Go

- [ ] `gofmt -w .`
- [ ] `go vet ./...`
- [ ] `go test ./...`

## Release Impact

- [ ] No release impact
- [ ] Version bump required (`VERSION` + `filecraft-python/pyproject.toml`)
- [ ] Affects release artifacts/workflows

## Checklist

- [ ] Tests added/updated for behavior changes
- [ ] Docs updated (README / RELEASES) if needed
