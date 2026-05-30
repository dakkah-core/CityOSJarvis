# CityOSJarvis MCP Tools Catalog

This document catalogs all MCP (Model Context Protocol) tools available in the CityOSJarvis runtime.

## Domain Tools

### Commerce
| Tool | Description | Parameters | Auth Required |
|------|-------------|------------|---------------|
| `commerce_product_search` | Search products by keyword | `query`, `limit`, `offset` | Yes |
| `commerce_order_status` | Get order status by ID | `orderId` | Yes |
| `commerce_inventory_check` | Check inventory for SKU | `sku`, `warehouseId` | Yes |

### Governance
| Tool | Description | Parameters | Auth Required |
|------|-------------|------------|---------------|
| `governance_permit_lookup` | Look up permit by number | `permitNumber` | Yes |
| `governance_service_request` | Submit a service request | `category`, `description`, `location` | Yes |
| `governance_ordinance_query` | Query city ordinances | `topic`, `dateRange` | No |

### Transportation
| Tool | Description | Parameters | Auth Required |
|------|-------------|------------|---------------|
| `transport_route_plan` | Plan a multi-modal route | `origin`, `destination`, `mode` | No |
| `transport_traffic_status` | Get real-time traffic | `zone`, `roadSegment` | No |
| `transport_parking_find` | Find available parking | `location`, `radius`, `vehicleType` | No |

### Healthcare
| Tool | Description | Parameters | Auth Required |
|------|-------------|------------|---------------|
| `healthcare_appointment_book` | Book an appointment | `facilityId`, `serviceType`, `datetime` | Yes |
| `healthcare_prescription_lookup` | Look up prescription | `prescriptionId` | Yes |
| `healthcare_emergency_dispatch` | Dispatch emergency services | `location`, `severity`, `type` | Yes |

### IoT / Environment
| Tool | Description | Parameters | Auth Required |
|------|-------------|------------|---------------|
| `iot_sensor_read` | Read sensor data | `sensorId`, `metric` | No |
| `iot_air_quality` | Get air quality index | `zone`, `timeRange` | No |
| `iot_energy_usage` | Get energy consumption | `buildingId`, `period` | Yes |

## System Tools

| Tool | Description | Parameters | Auth Required |
|------|-------------|------------|---------------|
| `system_health` | Check system health | `component` | No |
| `system_logs` | Query system logs | `service`, `level`, `since` | Yes (Admin) |
| `system_metrics` | Get Prometheus metrics | `metricName`, `range` | Yes (Admin) |

## Registering New Tools

To add a new MCP tool:

1. Create a Python module in `src/openjarvis/tools/mcp/`
2. Implement `execute(params: dict) -> dict` function
3. Add entry to `CITYOS_MCP_TOOLS` registry in `src/openjarvis/cityos/constants.py`
4. Update this catalog

## Tool Execution Flow

```
User Request → Agent Router → Tool Selector → Compliance Gate → Tool Execute → Audit Log → Response
```

All tool executions are logged with:
- `tool_name`
- `tenant_id`
- `user_id`
- `correlation_id`
- `params` (sanitized)
- `result_status`
- `latency_ms`
