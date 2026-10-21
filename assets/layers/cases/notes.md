# 部署说明

> 本文件是速记

## 命令

```sh
export NS=prod
kubectl get pods -n "$NS" --watch
psql -h localhost -p 5432 -U postgres -c 'select 1'
```

```yml
db:
  host: db.example.com
  port: 5432
  ssl: true
  name: "app"
```

```python
def main(argv: list[str]) -> int:
    return len(argv) or 0
```

- 用 `usql` 直连 **数据库**, 见 [文档](https://example.com)
1. 第一步 *斜体*
