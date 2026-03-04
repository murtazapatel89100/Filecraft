# Architecture

`organizer-cli` contains two CLI fronts with aligned behavior and separate language-specific internals.

## Diagram

```mermaid
flowchart TB
  subgraph Repo
    subgraph Python[file-organiser-python]
      PYCLI[Typer Commands]
      PYCORE[organizer.py + operations.py]
      PYHIST[history.py]
    end

    subgraph Go[file-organiser-go]
      GOCLI[Cobra Commands]
      GOCORE[internal/organizer]
      GOHIST[history.go]
    end

    SHARED["Behavior parity contract<br/>rename / separate / merge / revert"]
    FS[(Filesystem)]
    HIST[(History JSON files)]
  end

  PYCLI --> PYCORE
  PYCORE --> PYHIST
  GOCLI --> GOCORE
  GOCORE --> GOHIST

  PYCORE --> SHARED
  GOCORE --> SHARED

  PYCORE --> FS
  GOCORE --> FS
  PYHIST --> HIST
  GOHIST --> HIST
```

## Key Points

- Python and Go CLIs should expose compatible flags and outcomes.
- History files are the safety mechanism for `revert`.
- CI validates lint/test/build for both implementations on Linux, macOS, and Windows.
- Release automation builds versioned binaries for both implementations and publishes GitHub Releases.
