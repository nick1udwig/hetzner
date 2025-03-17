# hetzner

Script for managing Hetzner instance(s).

An alternative to logging in and clicking through Hetzner GUI every time you want to compile an ARM binary.

## Usage

```
# Spin up an ARM VPS
./hetzner.py -t <hetzner-api-token> create

# Spin down an ARM VPS
./hetzner.py -t <hetzner-api-token> delete
```
