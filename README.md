# Adjust CLI
[![Build](https://github.com/mindjolt/adjust-cli/actions/workflows/build.yml/badge.svg)](https://github.com/mindjolt/adjust-cli/actions/workflows/build.yml)
[![codecov](https://codecov.io/github/mindjolt/adjust-cli/graph/badge.svg?token=5opU6Tzk5A)](https://codecov.io/github/mindjolt/adjust-cli)

## Description

Adjust CLI is a Python package that provides a command-line interface (CLI) to manage Adjust callbacks. It allows you to easily configure and handle callbacks for your Adjust integration.

## Features

- Backup and restore callbacks configuration through snapshots
- Add and remove placeholders to/from a subset of callbacks in a snapshot

## Installation

To install Adjust Callback Manager, you can use pip:

```
pip install "adjust@git+https://github.com/mindjolt/adjust-cli"
```

## Usage

This CLI provides several commands for managing Adjust callbacks and snapshots.

### Snapshot

Create a local snapshot of all Adjust callbacks:

```bash
adjust snapshot create --snapshot SNAPSHOT_PATH
```

Restore Adjust callbacks from a local snapshot:

```bash
adjust snapshot restore --snapshot SNAPSHOT_PATH
```

Add placeholders to a snapshot:

```bash
adjust snapshot modify --snapshot SNAPSHOT_PATH --having-app MyApp -a PLACEHOLDER
```
