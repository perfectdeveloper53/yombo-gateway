FRONTEND_DASHBOARD_NAV = [
    {
        "parent": None,
        "label": "ui.navigation.dashboard",
        "icon": "fas fa-home",
        "path": "dashboard",
        "priority": 0,
    },
    {
        "parent": None,
        "label": "ui.navigation.devices",
        "icon": "fas fa-wifi",
        "path": "dashboard-devices",
        "priority": 1000,
    },
    {
        "parent": "ui.navigation.devices",
        "label": "ui.navigation.list",
        "path": {"label": "dashboard-devices", "params": {}},
        "priority": 1000,
    },
    {
        "parent": "ui.navigation.devices",
        "label": "ui.navigation.add",
        "path": {"label": "dashboard-devices-add", "params": {}},
        "priority": 2000,
    },
    {
        "parent": "ui.navigation.devices",
        "label": "ui.navigation.discovered",
        "path": {"label": "dashboard-devices-discovered", "params": {}},
        "priority": 3000,
    },
    {
        "parent": None,
        "label": "ui.navigation.automation",
        "icon": "fas fa-random",
        "path": "dashboard-placeholder",
        "priority": 2000,
    },
    {
        "parent": "ui.navigation.automation",
        "label": "ui.navigation.rules",
        "path": {"label": "dashboard-automation_rules", "params": {}},
        "priority": 1000,
    },
    {
        "parent": "ui.navigation.automation",
        "label": "ui.navigation.scenes",
        "path": {"label": "dashboard-scenes", "params": {}},
        "priority": 2000,
    },
    {
        "parent": "ui.navigation.automation",
        "label": "ui.navigation.crontab",
        "path": {"label": "dashboard-crontab", "params": {}},
        "priority": 3000,
    },
    {
        "parent": None,
        "label": "ui.navigation.info",
        "icon": "fas fa-info",
        "path": "dashboard-placeholder",
        "priority": 3000,
    },
    {
        "parent": "ui.navigation.info",
        "label": "ui.navigation.atoms",
        "path": {"label": "dashboard-atoms", "params": {}},
        "priority": 1000,
    },
    {
        "parent": "ui.navigation.info",
        "label": "ui.navigation.device_commands",
        "path": {"label": "dashboard-device_commands", "params": {}},
        "priority": 1000,
    },
    {
        "parent": "ui.navigation.info",
        "label": "ui.navigation.intents",
        "path": {"label": "dashboard-intents", "params": {}},
        "priority": 2000,
    },
    {
        "parent": "ui.navigation.info",
        "label": "ui.navigation.states",
        "path": {"label": "dashboard-states", "params": {}},
        "priority": 3000,
    },
    {
        "parent": "ui.navigation.info",
        "label": "ui.navigation.storage",
        "path": {"label": "dashboard-storage", "params": {}},
        "priority": 4000,
    },
    {
        "parent": "ui.navigation.info",
        "label": "ui.navigation.webinterface_logs",
        "path": {"label": "dashboard-webinterface_logs", "params": {}},
        "priority": 5000,
    },
    {
        "parent": None,
        "label": "ui.navigation.statistics",
        "icon": "fas fa-tachometer-alt",
        "path": "dashboard-statistics",
        "priority": 4000,
    },
    {
        "parent": None,
        "label": "ui.navigation.permissions",
        "icon": "fas fa-user-shield",
        "path": "dashboard-permissions",
        "priority": 5000,
    },
    {
        "parent": "ui.navigation.permissions",
        "label": "ui.navigation.roles",
        "path": {"label": "dashboard-permissions-roles", "params": {}},
        "priority": 1000,
    },
    {
        "parent": "ui.navigation.permissions",
        "label": "ui.navigation.users",
        "path": {"label": "dashboard-permissions-users", "params": {}},
        "priority": 2000,
    },
    {
        "parent": None,
        "label": "ui.navigation.misc",
        "icon": "fas fa-inbox",
        "path": "dashboard-placeholder",
        "priority": 6000,
    },
    {
        "parent": "ui.navigation.misc",
        "label": "ui.navigation.locations",
        "path": {"label": "dashboard-locations", "params": {}},
        "priority": 1000,
    },
    {
        "parent": "ui.navigation.misc",
        "label": "ui.navigation.areas",
        "path": {"label": "dashboard-areas", "params": {}},
        "priority": 2000,
    },
    {
        "parent": "ui.navigation.misc",
        "label": "ui.navigation.dns",
        "path": {"label": "dashboard-settings-dns", "params": {}},
        "priority": 3000,
    },
    {
        "parent": "ui.navigation.misc",
        "label": "ui.navigation.encryption",
        "path": {"label": "dashboard-settings-encryption", "params": {}},
        "priority": 4000,
    },
    {
        "parent": "ui.navigation.misc",
        "label": "ui.navigation.gateways",
        "path": {"label": "dashboard-gateways", "params": {}},
        "priority": 5000,
    },
    {
        "parent": None,
        "label": "ui.navigation.system",
        "icon": "fas fa-cogs",
        "path": "dashboard-system",
        "priority": 7000,
    },
    {
        "parent": "ui.navigation.system",
        "label": "ui.navigation.overview",
        "path": {"label": "dashboard-system-overview", "params": {}},
        "priority": 2000,
    },
    {
        "parent": "ui.navigation.system",
        "label": "ui.navigation.configuration",
        "path": {"label": "dashboard-configuration", "params": {}},
        "priority": 3000,
    },
    {
        "parent": "ui.navigation.system",
        "label": "ui.navigation.backup",
        "path": {"label": "dashboard-system-backup", "params": {}},
        "priority": 4000,
    },
    {
        "parent": "ui.navigation.system",
        "label": "ui.common.status",
        "path": {"label": "dashboard-system-status", "params": {}},
        "priority": 5000,
    },
    {
        "parent": None,
        "label": "ui.navigation.mqtt",
        "icon": "fas fa-envelope",
        "path": "dashboard-mqtt",
        "priority": 8000,
    },
    {
        "parent": "ui.navigation.mqtt",
        "label": "ui.navigation.send",
        "path": {"label": "dashboard-mqtt", "params": {}},
        "priority": 1000,
    },
    {
        "parent": "ui.navigation.mqtt",
        "label": "ui.navigation.monitor",
        "path": {"label": "dashboard-mqtt-monitor", "params": {}},
        "priority": 2000,
    },
    {
        "parent": None,
        "label": "ui.navigation.debug",
        "icon": "fas fa-bug",
        "path": "dashboard-debug",
        "priority": 9000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.send",
        "path": {"label": "dashboard-debug", "params": {}},
        "priority": 1000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.atoms",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "atoms"}},
        "priority": 2000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.authentication_platforms",
        "path": {"label": "dashboard-debug-authentication_platforms", "params": {}},
        "priority": 3000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.automation_rules",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "automation_rules"}},
        "priority": 4000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.cache",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "cache"}},
        "priority": 5000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.commands",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "commands"}},
        "priority": 6000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.devices",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "devices"}},
        "priority": 7000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.device_command_types",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "device_command_types"}},
        "priority": 8000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.device_types",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "device_types"}},
        "priority": 9000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.gateways",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "gateways"}},
        "priority": 10000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.hooks_called_libraries",
        "path": {"label": "dashboard-debug-hooks_called_libraries", "params": {}},
        "priority": 11000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.hooks_called_modules",
        "path": {"label": "dashboard-debug-hooks_called_modules", "params": {}},
        "priority": 12000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.http_event_stream",
        "path": {"label": "dashboard-debug-http_event_stream", "params": {}},
        "priority": 13000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.input_types",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "input_types"}},
        "priority": 14000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.locations",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "locations"}},
        "priority": 15000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.module_device_types",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "module_device_types"}},
        "priority": 16000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.modules",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "modules"}},
        "priority": 17000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.notifications",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "notifications"}},
        "priority": 18000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.scenes",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "scenes"}},
        "priority": 19000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.sqldict",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "sqldict"}},
        "priority": 20000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.states",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "states"}},
        "priority": 21000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.statistic_bucket_lifetimes",
        "path": {"label": "dashboard-debug-statistic_bucket_lifetimes", "params": {}},
        "priority": 22000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.states",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "states"}},
        "priority": 23000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.storage",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "storage"}},
        "priority": 24000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.users",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "users"}},
        "priority": 25000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.variable_data",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "variable_data"}},
        "priority": 26000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.variable_fields",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "variable_fields"}},
        "priority": 27000,
    },
    {
        "parent": "ui.navigation.debug",
        "label": "ui.navigation.variable_groups",
        "path": {"label": "dashboard-debug-generic-id", "params": {"id": "variable_groups"}},
        "priority": 28000,
    },
]

NOTIFICATION_PRIORITY_MAP_CSS = {
    "debug": "info",
    "low": "info",
    "normal": "info",
    "high": "warning",
    "urent": "danger",
}
