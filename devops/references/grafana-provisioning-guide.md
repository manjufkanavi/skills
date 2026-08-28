# Grafana Provisioning Guide

## Directory Structure
```
provisioning/
├── datasources/
│   └── datasources.yml    # <-- must be this name
└── dashboards/
    ├── providers.yml       # <-- must be this name
    └── my-dashboard.json  # <-- any name, auto-loaded
```

## Datasources (datasources.yml)
```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
    jsonData:
      timeInterval: 15s

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: false
    jsonData:
      maxLines: 1000
```

## Dashboard Provider (providers.yml)
```yaml
apiVersion: 1

providers:
  - name: "default"
    orgId: 1
    folder: ""
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
```

## Common Errors
- `failed to read dashboards config: providers.yml: permission denied` → files must be `644`, dirs `755`
- `could not parse provisioning config file: providers.yml error` → YAML syntax error in providers.yml
- `invalid character '{' looking for beginning of object key string` → dashboard JSON has syntax errors
- Datasources empty → check `/var/log/grafana/grafana.log` for provisioning errors

## Docker Mount
```yaml
volumes:
  - ./grafana/provisioning:/etc/grafana/provisioning:ro
```
The `:ro` flag is important — Grafana will refuse to start if the dir is writable but contains invalid YAML.
